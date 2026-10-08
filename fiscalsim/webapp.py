"""
Fiscal Printer Web Panel - HTTP API + static UI

Stdlib-only web server (no Flask/FastAPI needed) that exposes the
simulator over HTTP so a browser panel can show:

  * the live command log (everything the printer processes)
  * the virtual paper roll (receipt / X / Z report as printed)
  * the fiscal memory (company data required by law)
  * quick-sale controls that speak the real protocol of each brand

API
---
GET  /                     -> panel UI (static/index.html)
GET  /api/state            -> full simulator state as JSON
GET  /api/history?since=N  -> command history entries after seq N
GET  /api/preview          -> live preview lines of the open document
GET  /api/jobs             -> list of print jobs (metadata)
GET  /api/job/<id>         -> one print job with its paper lines
GET  /api/company          -> fiscal memory (company data)
POST /api/command          -> {"command": "..."} raw protocol command
POST /api/company          -> program fiscal memory
POST /api/sale             -> structured quick-sale step
POST /api/report           -> {"type": "x"|"z"} print X or Z report
"""

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import urlparse, parse_qs

from .simulator import create_simulator, FiscalPrinterSimulator
from . import render as paper

logger = logging.getLogger("fiscalsim.webapp")

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
BRANDS = ["tfhka", "hasar", "bixolon", "epson"]

# Host actions that build real protocol commands per brand
_TFHKA_PREFIX = {"exempt": " ", "general": "!", "reduced": '"', "additional": "#"}


def _json_default(obj: Any):
    from datetime import datetime, date
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


class PanelState:
    """Holds the simulator instances (one per brand) for the panel."""

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.sims: Dict[str, FiscalPrinterSimulator] = {}
        self.lock = threading.Lock()
        for brand in BRANDS:
            path = os.path.join(self.data_dir, f"state_{brand}.json")
            self.sims[brand] = create_simulator(brand, state_path=path)

    def get(self, brand: str) -> FiscalPrinterSimulator:
        brand = (brand or "tfhka").lower()
        if brand not in self.sims:
            brand = "tfhka"
        return self.sims[brand]


def build_state_payload(sim: FiscalPrinterSimulator) -> Dict[str, Any]:
    st = sim.state
    status = st.get_status_code()
    error = st.get_error_code()
    from .protocol import STATUS_CODES, ERROR_CODES
    return {
        "brand": sim.brand,
        "model": sim.model,
        "command_count": sim.command_count,
        "status": {"code": status, "hex": f"0x{status:02X}",
                   "name": STATUS_CODES.get(status, "Desconocido")},
        "error": {"code": error, "hex": f"0x{error:02X}",
                  "name": ERROR_CODES.get(error, "Desconocido")},
        "mode": st.mode,
        "memory_status": st.memory_status,
        "document": {
            "open": st.document_open,
            "type": st.document_type,
            "items": len(st.current_items),
            "subtotal": round(st.subtotal_bases + st.subtotal_tax, 2),
            "payable": round(st.amount_payable, 2),
            "paid": round(st.payments_made, 2),
            "customer": {"rif": st.customer_rif, "name": st.customer_name,
                         "address": st.customer_address},
        },
        "counters": {
            "invoices": st.invoice_counter,
            "credit_notes": st.credit_note_counter,
            "debit_notes": st.debit_note_counter,
            "non_fiscal": st.non_fiscal_counter,
            "x_reports": st.x_report_counter,
            "z_reports": st.z_report_counter,
            "daily_closure": st.daily_closure_counter,
            "fiscal_docs": st.fiscal_counter,
        },
        "daily": {
            "invoices": st.daily_invoices,
            "credit_notes": st.daily_credit_notes,
            "debit_notes": st.daily_debit_notes,
            "non_fiscal": st.daily_non_fiscal,
            "sales": round(st.daily_sales, 2),
            "tax": round(st.daily_tax, 2),
        },
        "totals": {
            "lifetime_sales": round(st.total_sales, 2),
            "lifetime_tax": round(st.total_tax, 2),
        },
        "payments": {k: round(v, 2) for k, v in st.payment_totals.items()},
        "tax_rates": st.tax_rates,
        "serial_number": st.serial_number,
        "rif": st.rif,
        "memory": {
            "total_mb": st.audit_memory_total,
            "free_mb": round(st.audit_memory_free, 2),
            "used_mb": round(st.audit_memory_used, 2),
            "used_pct": round(100 * st.audit_memory_used /
                              max(st.audit_memory_total, 0.001), 1),
        },
        "print_job_seq": st.print_job_seq,
        "headers": st.headers,
        "is_tfhka": sim.brand == "TFHKA",
    }


def host_action(sim: FiscalPrinterSimulator, action: str,
                params: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a structured panel action into real protocol commands."""
    is_tfhka = sim.brand == "TFHKA"
    commands = []

    if action == "open":
        doc = params.get("doc", "invoice")
        if is_tfhka:
            rif = params.get("rif", "")
            name = params.get("name", "")
            address = params.get("address", "")
            if rif:
                commands.append(f"iR*{rif}")
            if name:
                commands.append(f"iS*{name}")
            if address:
                commands.append(f"i01{address}")
            if doc == "credit_note":
                commands.append("d1")
            elif doc == "debit_note":
                commands.append("d2")
        else:
            if doc == "credit_note":
                commands.append("@OpenCreditNote")
            elif doc == "debit_note":
                commands.append("@OpenDebitNote")
            else:
                commands.append("@OpenFiscalReceipt")
            rif = params.get("rif", "")
            name = params.get("name", "")
            address = params.get("address", "")
            if rif or name or address:
                commands.append(
                    f"@CustomerData|{rif}|{name}|{address}")

    elif action == "item":
        desc = params.get("description", "ITEM")
        qty = float(params.get("qty", 1))
        price = float(params.get("price", 0))
        tax = params.get("tax", "general")
        if is_tfhka:
            prefix = _TFHKA_PREFIX.get(tax, "!")
            commands.append(
                f"{prefix}{qty:8.3f}{price:10.2f}{desc}")
        else:
            commands.append(f"@PrintLine|{desc}|{qty}|{price}|{tax}")

    elif action == "subtotal":
        commands.append("3" if is_tfhka else "@Subtotal")

    elif action == "payment":
        amount = float(params.get("amount", 0))
        method = params.get("method", "cash")
        if is_tfhka:
            # TFHKA declares the tender type with 103 before the 100 amount
            if method and method != "cash":
                commands.append(f"103{method}")
            commands.append(f"100{amount:.2f}")
        else:
            commands.append(f"@AddPayment|{amount:.2f}|{method}")

    elif action == "close":
        commands.append("101" if is_tfhka else "@Close")

    elif action == "status":
        commands.append("S1" if is_tfhka else "@Status")

    elif action == "cancel":
        if is_tfhka:
            # TFHKA has no direct cancel: close empties the doc
            if sim.state.document_open:
                with sim.state.lock:
                    sim.state.document_open = False
                    sim.state.document_type = None
                    sim.state.current_state = "waiting"
                    sim.state.current_items = []
                    sim.state.subtotal_bases = 0.0
                    sim.state.subtotal_tax = 0.0
                    sim.state.amount_payable = 0.0
                return {"commands": [], "responses": [],
                        "note": "Documento cancelado localmente"}
            return {"commands": [], "responses": [], "note": "Sin documento"}
        commands.append("@Cancel")

    elif action == "report":
        kind = str(params.get("type", "x")).lower()
        if is_tfhka:
            commands.append("U0X" if kind == "x" else "U0Z")
        else:
            commands.append("@PrintXReport" if kind == "x"
                            else "@PrintZReport")

    elif action == "drawer":
        commands.append("0" if is_tfhka else "@OpenDrawer")

    elif action == "customer":
        rif = params.get("rif", "")
        name = params.get("name", "")
        address = params.get("address", "")
        if is_tfhka:
            if rif:
                commands.append(f"iR*{rif}")
            if name:
                commands.append(f"iS*{name}")
            if address:
                commands.append(f"i01{address}")
        else:
            commands.append(f"@CustomerData|{rif}|{name}|{address}")

    else:
        return {"error": f"Acción desconocida: {action}"}

    responses = []
    for cmd in commands:
        resp = sim.process_command(cmd)
        responses.append({"command": cmd, "response": resp})

    last_job = sim.state.print_jobs[-1] if sim.state.print_jobs else None
    return {
        "commands": commands,
        "responses": responses,
        "last_job_id": last_job["id"] if last_job else None,
    }


class PanelHandler(BaseHTTPRequestHandler):
    panel: PanelState = None  # injected by make_server

    # -------------------------------------------------------------- helpers
    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False,
                          default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: str, content_type: str) -> None:
        try:
            with open(path, "rb") as fh:
                body = fh.read()
        except OSError:
            self._send_json({"error": "not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def log_message(self, fmt, *args):  # quiet default access log
        logger.debug(fmt, *args)

    # --------------------------------------------------------------- routes
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            self._send_file(os.path.join(STATIC_DIR, "index.html"),
                            "text/html; charset=utf-8")
        elif path.endswith(".css"):
            self._send_file(os.path.join(STATIC_DIR, path.lstrip("/")),
                            "text/css; charset=utf-8")
        elif path.endswith(".js"):
            self._send_file(os.path.join(STATIC_DIR, path.lstrip("/")),
                            "application/javascript; charset=utf-8")
        elif path == "/api/state":
            sim = self.panel.get(query.get("brand", ["tfhka"])[0])
            self._send_json(build_state_payload(sim))
        elif path == "/api/history":
            sim = self.panel.get(query.get("brand", ["tfhka"])[0])
            since = int(query.get("since", ["0"])[0])
            with sim.state.lock:
                entries = [e for e in sim.history if e["seq"] > since]
            self._send_json({"entries": entries,
                             "count": sim.command_count})
        elif path == "/api/preview":
            sim = self.panel.get(query.get("brand", ["tfhka"])[0])
            with sim.state.lock:
                lines = paper.render_open_document(sim.state)
            self._send_json({"open": sim.state.document_open, "lines": lines})
        elif path == "/api/jobs":
            sim = self.panel.get(query.get("brand", ["tfhka"])[0])
            with sim.state.lock:
                jobs = [
                    {"id": j["id"], "kind": j["kind"], "title": j["title"],
                     "ts": j["ts"], "meta": j.get("meta", {})}
                    for j in reversed(sim.state.print_jobs)
                ]
            self._send_json({"jobs": jobs})
        elif path.startswith("/api/job/"):
            sim = self.panel.get(query.get("brand", ["tfhka"])[0])
            try:
                job_id = int(path.rsplit("/", 1)[1])
            except ValueError:
                self._send_json({"error": "bad id"}, 400)
                return
            with sim.state.lock:
                job = next((j for j in sim.state.print_jobs
                            if j["id"] == job_id), None)
            if job is None:
                self._send_json({"error": "job not found"}, 404)
            else:
                self._send_json(job)
        elif path == "/api/company":
            sim = self.panel.get(query.get("brand", ["tfhka"])[0])
            self._send_json({"company": sim.state.company,
                             "headers": sim.state.headers})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()
        brand = body.get("brand", "tfhka")

        if path == "/api/command":
            sim = self.panel.get(brand)
            command = str(body.get("command", "")).strip()
            if not command:
                self._send_json({"error": "command required"}, 400)
                return
            response = sim.process_command(command)
            self._send_json({
                "command": command,
                "response": response,
                "seq": sim.command_count,
            })
        elif path == "/api/company":
            sim = self.panel.get(brand)
            data = body.get("company") or body.get("data") or {}
            if not isinstance(data, dict) or not data:
                self._send_json({"error": "company data required"}, 400)
                return
            result = sim.program_company(data)
            self._send_json({"company": result,
                             "headers": sim.state.headers})
        elif path == "/api/sale":
            sim = self.panel.get(brand)
            action = str(body.get("action", "")).strip()
            params = body.get("params") or {}
            if not action:
                self._send_json({"error": "action required"}, 400)
                return
            result = host_action(sim, action, params)
            self._send_json(result)
        elif path == "/api/report":
            sim = self.panel.get(brand)
            kind = str(body.get("type", "x")).lower()
            result = host_action(sim, "report", {"type": kind})
            self._send_json(result)
        else:
            self._send_json({"error": "not found"}, 404)


def make_server(host: str = "127.0.0.1", port: int = 8080,
                data_dir: str = None) -> ThreadingHTTPServer:
    handler = type("BoundPanelHandler", (PanelHandler,), {
        "panel": PanelState(data_dir),
    })
    server = ThreadingHTTPServer((host, port), handler)
    return server


def run_server(host: str = "127.0.0.1", port: int = 8080,
               data_dir: str = None) -> None:
    server = make_server(host, port, data_dir)
    print(f"Panel fiscal corriendo en http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo panel...")
    finally:
        server.server_close()
