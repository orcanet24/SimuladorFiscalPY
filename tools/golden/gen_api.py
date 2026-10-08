#!/usr/bin/env python3
"""
Generate a golden snapshot of the web panel API from the Python reference.

Starts `python panel.py` against a throwaway data dir, exercises every REST
endpoint for every brand, scrubs timestamps and writes
testdata/golden/api.json.

The Go port must serve semantically identical JSON (same keys/values;
timestamps replaced by "<TS>" on both sides before comparison).

Usage:
    python tools/golden/gen_api.py
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_PATH = os.path.join(ROOT, "testdata", "golden", "api.json")

ISO_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?")
PAPER_TS_RE = re.compile(r"\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}")

BRANDS = ["tfhka", "hasar", "bixolon", "epson"]


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def scrub(value):
    if isinstance(value, str):
        value = ISO_TS_RE.sub("<TS>", value)
        return PAPER_TS_RE.sub("<TS>", value)
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def req(base, method, path, body=None):
    url = base + path
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers,
                                     method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            status = resp.status
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except ValueError:
        payload = {"_raw_bytes": len(raw)}
    return {"status": status, "body": scrub(payload)}


def wait_ready(base, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req(base, "GET", "/api/state")
            return True
        except OSError:
            time.sleep(0.15)
    return False


def sale_flow(brand, close=True):
    """Structured quick-sale steps (fixed values) for one brand."""
    steps = []
    steps.append(("POST", "/api/sale", {
        "brand": brand, "action": "open",
        "params": {"doc": "invoice", "rif": "J-12345678-9",
                   "name": "EMPRESA DE PRUEBA C.A.",
                   "address": "Av. Principal, Caracas"},
    }))
    steps.append(("POST", "/api/sale", {
        "brand": brand, "action": "customer",
        "params": {"rif": "J-12345678-9", "name": "EMPRESA DE PRUEBA C.A.",
                   "address": "Av. Principal, Caracas"},
    }))
    steps.append(("POST", "/api/sale", {
        "brand": brand, "action": "item",
        "params": {"description": "CAFE", "qty": 2, "price": 15.0,
                   "tax": "general"},
    }))
    steps.append(("POST", "/api/sale", {
        "brand": brand, "action": "item",
        "params": {"description": "PAN", "qty": 3, "price": 8.0,
                   "tax": "reduced"},
    }))
    steps.append(("POST", "/api/sale",
                  {"brand": brand, "action": "subtotal", "params": {}}))
    if close:
        steps.append(("POST", "/api/sale", {
            "brand": brand, "action": "payment",
            "params": {"amount": 54.0, "method": "cash"},
        }))
        steps.append(("POST", "/api/sale",
                      {"brand": brand, "action": "close", "params": {}}))
    return steps


def run_flow(results, base, tag, steps):
    for i, (method, path, body) in enumerate(steps):
        results[f"{tag}|{i:02d}|{method} {path}"] = req(base, method, path, body)


def main():
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    data_dir = tempfile.mkdtemp(prefix="fiscalsim_golden_")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "panel.py"),
         "--host", "127.0.0.1", "--port", str(port),
         "--data-dir", data_dir, "--no-browser", "--quiet"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = {}
    try:
        if not wait_ready(base):
            raise RuntimeError("panel.py did not become ready")
        with open(os.path.join(ROOT, "panel.py"), "rb") as fh:
            import hashlib
            results["GET / (index)"] = {
                "status": 200,
                "sha256": hashlib.sha256(fh.read()).hexdigest(),
            }
        for brand in BRANDS:
            # raw command
            run_flow(results, base, f"{brand} raw", [
                ("POST", "/api/command",
                 {"brand": brand, "command": "S1" if brand == "tfhka"
                  else "@Status"}),
            ])
            # quick sale with live preview before closing
            run_flow(results, base, f"{brand} sale", sale_flow(brand))
            # report X and Z
            run_flow(results, base, f"{brand} report", [
                ("POST", "/api/report", {"brand": brand, "type": "x"}),
                ("POST", "/api/report", {"brand": brand, "type": "z"}),
            ])
            # fiscal memory
            company = {
                "rif": "J-12345678-9",
                "razon_social": "COMERCIAL LOS SIMULADORES C.A.",
                "direccion": "Av. Principal, Edificio Fiscal, Piso 4",
                "municipio": "CHACAO", "ciudad": "CARACAS", "estado": "MIRANDA",
                "telefono": "0212-9555123",
                "representante_legal": "JUAN PEREZ RODRIGUEZ",
                "cedula_representante": "V-12345678",
                "actividad_economica": "VENTA DE EQUIPOS DE OFICINA",
                "condiciones_pago": "CONTADO 30 DIAS",
                "contribuyente_especial": True,
                "agente_retencion": True,
            }
            run_flow(results, base, f"{brand} company", [
                ("POST", "/api/company", {"brand": brand, "company": company}),
            ])
            # GETs (jobs must exist by now: sale close created job #1)
            run_flow(results, base, f"{brand} get", [
                ("GET", f"/api/state?brand={brand}", None),
                ("GET", f"/api/history?brand={brand}&since=0", None),
                ("GET", f"/api/preview?brand={brand}", None),
                ("GET", f"/api/jobs?brand={brand}", None),
                ("GET", f"/api/job/1?brand={brand}", None),
                ("GET", f"/api/company?brand={brand}", None),
            ])
            # history pagination
            run_flow(results, base, f"{brand} hist2", [
                ("GET", f"/api/history?brand={brand}&since=1", None),
                ("GET", f"/api/history?brand={brand}&since=99999", None),
            ])
        # extra open-doc preview (document left open, then cancelled)
        run_flow(results, base, "tfhka preview-open", [
            ("POST", "/api/sale", {"brand": "tfhka", "action": "open",
                                   "params": {"doc": "invoice",
                                              "rif": "V-11111111",
                                              "name": "PREVIA ABIERTA",
                                              "address": "Calle Luna"}}),
            ("POST", "/api/sale", {"brand": "tfhka", "action": "item",
                                   "params": {"description": "ITEM PREVIA",
                                              "qty": 1, "price": 5.0,
                                              "tax": "exempt"}}),
            ("GET", "/api/preview?brand=tfhka", None),
            ("POST", "/api/sale", {"brand": "tfhka", "action": "cancel",
                                   "params": {}}),
            ("GET", "/api/preview?brand=tfhka", None),
        ])
        # error paths
        run_flow(results, base, "errors", [
            ("POST", "/api/command", {"brand": "tfhka", "command": ""}),
            ("POST", "/api/command", {"brand": "desconocida",
                                      "command": "S1"}),
            ("POST", "/api/sale", {"brand": "tfhka", "action": "",
                                   "params": {}}),
            ("POST", "/api/sale", {"brand": "tfhka", "action": "nope",
                                   "params": {}}),
            ("POST", "/api/company", {"brand": "tfhka", "company": {}}),
            ("POST", "/api/report", {"brand": "tfhka", "type": "x"}),
            ("GET", "/api/state", None),
            ("GET", "/api/nope", None),
            ("GET", "/api/job/99999?brand=tfhka", None),
            ("GET", "/api/job/abc?brand=tfhka", None),
            ("POST", "/api/nope", {"x": 1}),
        ])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(data_dir, ignore_errors=True)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1, sort_keys=False)
        fh.write("\n")
    print(f"api.json: {len(results)} endpoint results")


if __name__ == "__main__":
    main()
