"""
Fiscal Paper Renderer
Builds the virtual thermal-paper lines for fiscal receipts, credit/debit
notes, non-fiscal documents and X/Z reports.

All lines are plain strings of at most PAPER_WIDTH characters, so the web
panel can render them in a monospace "paper roll" exactly like a real
40-column thermal printer would.
"""

from datetime import datetime
from typing import Dict, List

PAPER_WIDTH = 42

# ---------------------------------------------------------------------------
# Number to words (Spanish) - required by law on every receipt ("SON: ...")
# ---------------------------------------------------------------------------

_UNITS = [
    "", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE",
    "OCHO", "NUEVE", "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE",
    "QUINCE", "DIECISÉIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE",
    "VEINTE", "VEINTIUNO", "VEINTIDÓS", "VEINTITRÉS", "VEINTICUATRO",
    "VEINTICINCO", "VEINTISÉIS", "VEINTISIETE", "VEINTIOCHO",
    "VEINTINUEVE",
]
_TENS = ["", "", "", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA",
         "SETENTA", "OCHENTA", "NOVENTA"]
_HUNDREDS = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS",
             "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS",
             "NOVECIENTOS"]


def _num_to_words_up_to_999(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "CIEN"
    h, rest = divmod(n, 100)
    parts: List[str] = []
    if h:
        parts.append(_HUNDREDS[h])
    if rest:
        if rest < 30:
            parts.append(_UNITS[rest])
        else:
            t, u = divmod(rest, 10)
            word = _TENS[t]
            if u:
                word += " Y " + _UNITS[u]
            parts.append(word)
    return " ".join(parts)


def number_to_words(amount: float) -> str:
    """Convert an amount to Spanish words, e.g. 1234.50 ->
    'MIL DOSCIENTOS TREINTA Y CUATRO CON 50/100'."""
    whole = int(abs(amount))
    cents = int(round((abs(amount) - whole) * 100))

    if whole == 0:
        words = "CERO"
    else:
        chunks: List[str] = []
        millions, rest = divmod(whole, 1_000_000)
        thousands, units = divmod(rest, 1_000)
        if millions:
            chunks.append(
                ("UN MILLÓN" if millions == 1
                 else f"{_num_to_words_up_to_999(millions)} MILLONES")
            )
        if thousands:
            if thousands == 1:
                chunks.append("MIL")
            else:
                chunks.append(_num_to_words_up_to_999(thousands) + " MIL")
        if units:
            chunks.append(_num_to_words_up_to_999(units))
        words = " ".join(chunks)

    return f"{words} CON {cents:02d}/100"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _center(text: str) -> str:
    return text.center(PAPER_WIDTH)


def _rule(char: str = "-") -> str:
    return char * PAPER_WIDTH


def _kv(key: str, value: str, sep: str = ":") -> str:
    """Key left, value right, filling the width."""
    left = f"{key}{sep} "
    right = str(value)
    pad = PAPER_WIDTH - len(left) - len(right)
    if pad < 1:
        return (left + right)[:PAPER_WIDTH]
    return left + " " * pad + right


def _money(value: float) -> str:
    return f"{value:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _wrap(text: str, width: int = PAPER_WIDTH) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = ""
    for w in words:
        if not current:
            current = w
        elif len(current) + 1 + len(w) <= width:
            current += " " + w
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines or [""]


def _company_block(company: Dict) -> List[str]:
    lines: List[str] = []
    name = company.get("razon_social") or "EMPRESA SIN NOMBRE"
    lines.append(_center(name.upper()))
    if company.get("rif"):
        lines.append(_center(f"RIF: {company['rif']}"))
    if company.get("logo_text") and company.get("logo_text") != name:
        lines.append(_center(company["logo_text"].upper()))
    if company.get("direccion"):
        lines.extend(_center(l) for l in _wrap(company["direccion"], 40))
    locality = " - ".join(
        p for p in [company.get("municipio"), company.get("ciudad"),
                    company.get("estado")] if p
    )
    if locality:
        lines.extend(_center(l) for l in _wrap(locality, 40))
    if company.get("telefono"):
        lines.append(_center(f"Telf: {company['telefono']}"))
    if company.get("representante_legal"):
        rep = f"Rep. Legal: {company['representante_legal']}"
        if company.get("cedula_representante"):
            rep += f" - C.I. {company['cedula_representante']}"
        lines.extend(_center(l) for l in _wrap(rep, 40))
    if company.get("actividad_economica"):
        lines.extend(_center(l) for l in _wrap(
            f"Actividad: {company['actividad_economica']}", 40))
    if company.get("contribuyente_especial"):
        lines.append(_center("CONTRIBUYENTE ESPECIAL"))
    if company.get("agente_retencion"):
        lines.append(_center("AGENTE DE RETENCION IVA"))
    return lines


# ---------------------------------------------------------------------------
# Receipt rendering
# ---------------------------------------------------------------------------

_DOC_TITLES = {
    "invoice": "FACTURA FISCAL",
    "credit_note": "NOTA DE CREDITO",
    "debit_note": "NOTA DE DEBITO",
    "non_fiscal": "DOCUMENTO NO FISCAL",
}

_TAX_LABELS = {
    "general": "G16",
    "reduced": "R8",
    "additional": "A30",
    "exempt": "EX",
}


def render_receipt(doc: Dict, company: Dict = None) -> List[str]:
    """Render a closed fiscal document as paper lines."""
    if company is None:
        company = doc.get("company") or {}
    lines: List[str] = []

    # --- Header -----------------------------------------------------------
    lines.extend(_company_block(company))
    lines.append(_rule("="))
    doc_type = doc.get("type", "invoice")
    lines.append(_center(_DOC_TITLES.get(doc_type, "DOCUMENTO FISCAL")))
    lines.append(_center(f"N° {doc.get('number', 0):08d}"))
    ts = doc.get("timestamp")
    if isinstance(ts, datetime):
        lines.append(_center(ts.strftime("%d/%m/%Y  %H:%M:%S")))
    lines.append(_rule("="))

    # --- Customer ---------------------------------------------------------
    cust = doc.get("customer") or {}
    lines.append("CLIENTE:")
    if cust.get("rif"):
        lines.append(f"  RIF/C.I: {cust['rif']}")
    if cust.get("name"):
        for l in _wrap(f"  {cust['name']}", 42):
            lines.append(l)
    if cust.get("address"):
        for l in _wrap(f"  {cust['address']}", 42):
            lines.append(l)
    if not any([cust.get("rif"), cust.get("name"), cust.get("address")]):
        lines.append("  CONSUMIDOR FINAL")
    lines.append(_rule())

    # --- Reference (credit/debit notes) -----------------------------------
    if doc_type in ("credit_note", "debit_note"):
        if doc.get("reference_invoice"):
            lines.append(_kv("FACT. REFERIDA", doc["reference_invoice"]))
        if doc.get("reference_date"):
            lines.append(_kv("FECHA ORIG.", doc["reference_date"]))
        if doc.get("reference_serial"):
            lines.append(_kv("SERIE ORIG.", doc["reference_serial"]))
        lines.append(_rule())

    # --- Items table ------------------------------------------------------
    lines.append(
        f"{'CANT':>7} {'DESCRIPCION':<17} {'PREC':>7} {'IVA':>4} {'IMPORTE':>9}"
    )
    lines.append(_rule())
    for item in doc.get("items", []):
        qty = item.get("quantity", 0)
        desc = str(item.get("description", ""))[:17]
        price = item.get("price", 0.0)
        tax_label = _TAX_LABELS.get(item.get("tax_type", "general"), "G16")
        total = item.get("total", 0.0)
        lines.append(f"{qty:>7.3f} {desc:<17} {price:>7.2f} {tax_label:>4} {total:>9.2f}")
        # Extra description lines beyond 17 chars are folded to a new line
        full_desc = str(item.get("description", ""))
        if len(full_desc) > 17:
            for l in _wrap(f"   {full_desc}", 42)[1:]:
                lines.append(l)
    lines.append(_rule())

    # --- Totals -----------------------------------------------------------
    lines.append(_kv("SUBTOTAL", _money(doc.get("subtotal_bases", 0) +
                                        doc.get("subtotal_tax", 0))))
    # Per-rate breakdown
    by_rate: Dict[str, Dict[str, float]] = {}
    for item in doc.get("items", []):
        rate = item.get("tax_type", "general")
        by_rate.setdefault(rate, {"base": 0.0, "tax": 0.0})
        by_rate[rate]["base"] += item.get("base", 0.0)
        by_rate[rate]["tax"] += item.get("tax", 0.0)
    for rate in ("general", "reduced", "additional", "exempt"):
        if rate in by_rate:
            pct = {"general": "16%", "reduced": "8%",
                   "additional": "30%", "exempt": "EXENTO"}[rate]
            lines.append(_kv(f"  BASE IVA {pct}" if rate != "exempt"
                             else "  BASE EXENTA",
                             _money(by_rate[rate]["base"])))
            if rate != "exempt":
                lines.append(_kv(f"  IVA {pct}", _money(by_rate[rate]["tax"])))
    lines.append(_rule("="))
    lines.append(_kv("TOTAL Bs.", _money(doc.get("total", 0))))
    lines.append(_rule("="))

    # --- Payments ---------------------------------------------------------
    payment_labels = {
        "cash": "EFECTIVO", "card": "TARJETA", "transfer": "TRANSFERENCIA",
        "mobile": "PAGO MOVIL", "credit": "CREDITO", "check": "CHEQUE",
        "pay_0": "EFECTIVO", "pay_1": "TARJETA", "pay_2": "TRANSFERENCIA",
    }
    for method, amount in (doc.get("payments") or {}).items():
        label = payment_labels.get(method, str(method).upper())
        lines.append(_kv(label, _money(amount)))
    if doc.get("change"):
        lines.append(_kv("CAMBIO", _money(doc["change"])))

    # --- Amount in words (legal requirement) ------------------------------
    lines.append(_rule())
    words = number_to_words(doc.get("total", 0))
    wrapped = _wrap(f"SON: {words}", 42)
    lines.extend(f"  {w}" if i == 0 else f"  {w}"
                 for i, w in enumerate(wrapped))

    # --- Legal footnotes ---------------------------------------------------
    lines.append(_rule())
    if doc.get("serial_number"):
        lines.append(_kv("MAQUINA", doc["serial_number"]))
    if doc.get("rif"):
        lines.append(_kv("RIF MAQ.", doc["rif"]))
    if company.get("condiciones_pago"):
        lines.append(_kv("COND. PAGO", company["condiciones_pago"]))
    lines.append(_center("ART. 63 Ley IVA - Ley Org."))
    lines.append(_center("Simplificacion y Racionalizacion"))
    lines.append(_center("del Proceso Tributario"))
    lines.append(_rule())
    footer = (company.get("footers") or {}).get("footer1") or \
        "GRACIAS POR SU COMPRA"
    lines.append(_center(footer))
    lines.append(_center("* * * * * * * * * * * * * * * *"))
    lines.append(_center("DOCUMENTO FISCAL DIGITAL"))
    lines.append(_center("SIMULADOR - NO VALOR FISCAL"))
    return lines


# ---------------------------------------------------------------------------
# X / Z reports
# ---------------------------------------------------------------------------

def _report_common_lines(rep: Dict, company: Dict, title: str) -> List[str]:
    lines: List[str] = []
    lines.extend(_company_block(company))
    lines.append(_rule("="))
    lines.append(_center(title))
    lines.append(_center(f"REPORTE N° {rep.get('number', 0):04d}"))
    ts = rep.get("timestamp")
    if isinstance(ts, datetime):
        lines.append(_center(ts.strftime("%d/%m/%Y  %H:%M:%S")))
    lines.append(_rule("="))
    return lines


_PAYMENT_LABELS = {
    "cash": "EFECTIVO", "card": "TARJETA", "transfer": "TRANSFERENCIA",
    "mobile": "PAGO MOVIL", "credit": "CREDITO", "check": "CHEQUE",
    "pay_0": "EFECTIVO", "pay_1": "TARJETA", "pay_2": "TRANSFERENCIA",
}


def _report_body_lines(rep: Dict) -> List[str]:
    lines: List[str] = []
    lines.append("DOCUMENTOS DEL DIA:")
    lines.append(_kv("  Facturas", str(rep.get("daily_invoices",
                 rep.get("last_invoice", 0)))))
    lines.append(_kv("  Notas de credito", str(rep.get("daily_credit_notes",
                 rep.get("last_credit_note", 0)))))
    lines.append(_kv("  Notas de debito", str(rep.get("daily_debit_notes",
                 rep.get("last_debit_note", 0)))))
    lines.append(_kv("  No fiscales", str(rep.get("daily_non_fiscal", 0))))
    lines.append(_rule())

    lines.append("VENTAS POR ALICUOTA:")
    labels = {"general": "GENERAL 16%", "reduced": "REDUCIDA 8%",
              "additional": "ADICIONAL 30%", "exempt": "EXENTO"}
    for rate in ("general", "reduced", "additional", "exempt"):
        block = (rep.get("tax_totals") or {}).get(rate) or {}
        if block.get("base") or block.get("tax"):
            lines.append(_kv(f"  {labels[rate]}", _money(block.get("base", 0))))
            if rate != "exempt":
                lines.append(_kv(f"    IVA", _money(block.get("tax", 0))))
    lines.append(_rule())

    lines.append("FORMAS DE PAGO:")
    payments = rep.get("payments") or {}
    if payments:
        for method, amount in payments.items():
            label = _PAYMENT_LABELS.get(str(method).lower(),
                                        str(method).upper())
            lines.append(_kv(f"  {label}", _money(amount)))
    else:
        lines.append("  (sin pagos registrados)")
    lines.append(_rule("="))

    lines.append(_kv("TOTAL VENTAS", _money(rep.get("total_sales", 0))))
    lines.append(_kv("TOTAL IVA", _money(rep.get("total_tax", 0))))
    if rep.get("total_discounts"):
        lines.append(_kv("DESCUENTOS", _money(rep["total_discounts"])))
    if rep.get("total_surcharges"):
        lines.append(_kv("RECARGOS", _money(rep["total_surcharges"])))
    lines.append(_rule("="))
    return lines


def render_x_report(rep: Dict, company: Dict = None) -> List[str]:
    """X report: read-only snapshot of the day, totals are NOT reset."""
    company = company or {}
    lines = _report_common_lines(rep, company,
                                 "REPORTE X - CORTE DE CAJA")
    lines.extend(_report_body_lines(rep))
    lines.append(_center("ESTE REPORTE NO REINICIA"))
    lines.append(_center("LOS TOTALES DEL DIA"))
    lines.append(_rule())
    if rep.get("last_invoice"):
        lines.append(_kv("ULTIMA FACTURA",
                         f"{rep['last_invoice']:08d}"))
    lines.append(_center("* * * * * * * * * * * * * * * *"))
    lines.append(_center("SIMULADOR - NO VALOR FISCAL"))
    return lines


def render_z_report(rep: Dict, company: Dict = None) -> List[str]:
    """Z report: daily closure - totals ARE reset after this."""
    company = company or {}
    lines = _report_common_lines(rep, company,
                                 "REPORTE Z - CIERRE DIARIO")
    lines.extend(_report_body_lines(rep))
    lines.append(_center("CIERRE DEL DIA"))
    lines.append(_center("TOTALES REINICIADOS TRAS"))
    lines.append(_center("ESTE REPORTE"))
    lines.append(_rule())
    if rep.get("last_invoice"):
        lines.append(_kv("ULTIMA FACTURA",
                         f"{rep['last_invoice']:08d}"))
    lines.append(_kv("CIERRES DIARIOS", str(rep.get("number", 0))))
    lines.append(_center("* * * * * * * * * * * * * * * *"))
    lines.append(_center("SIMULADOR - NO VALOR FISCAL"))
    return lines


def render_open_document(state) -> List[str]:
    """Render a live preview of the currently open document.

    `state` is a FiscalPrinterState whose document is still open - the
    panel polls this to show the ticket being built line by line.
    """
    if not getattr(state, "document_open", False):
        return []
    doc = {
        "type": state.document_type or "invoice",
        "number": {
            "invoice": state.invoice_counter + 1,
            "credit_note": state.credit_note_counter + 1,
            "debit_note": state.debit_note_counter + 1,
            "non_fiscal": state.non_fiscal_counter + 1,
        }.get(state.document_type or "invoice", state.invoice_counter + 1),
        "items": list(state.current_items),
        "subtotal_bases": state.subtotal_bases,
        "subtotal_tax": state.subtotal_tax,
        "total": state.subtotal_bases + state.subtotal_tax,
        "customer": {
            "rif": state.customer_rif,
            "name": state.customer_name,
            "address": state.customer_address,
        },
        "payments": dict(state.doc_payments),
        "paid": state.payments_made,
        "change": max(0.0, state.payments_made -
                      (state.subtotal_bases + state.subtotal_tax)),
        "timestamp": datetime.now(),
        "serial_number": state.serial_number,
        "rif": state.rif,
        "company": dict(state.company),
    }
    lines = render_receipt(doc, state.company)
    return ["".ljust(PAPER_WIDTH)] + [
        "* DOCUMENTO EN CURSO - VISTA PREVIA *".center(PAPER_WIDTH)
    ] + lines


def render_non_fiscal(doc: Dict, company: Dict = None) -> List[str]:
    company = company or doc.get("company") or {}
    lines: List[str] = []
    lines.extend(_company_block(company))
    lines.append(_rule("="))
    lines.append(_center("DOCUMENTO NO FISCAL"))
    lines.append(_center(f"N° {doc.get('number', 0):08d}"))
    ts = doc.get("timestamp")
    if isinstance(ts, datetime):
        lines.append(_center(ts.strftime("%d/%m/%Y  %H:%M:%S")))
    lines.append(_rule("="))
    for item in doc.get("items", []):
        lines.extend(_wrap(str(item.get("description", "")), 42))
    lines.append(_rule())
    lines.append(_center("DOCUMENTO SIN VALOR FISCAL"))
    return lines
