#!/usr/bin/env python3
"""
Generate golden paper-roll outputs from the Python reference simulator.

Two kinds of golden files:

1. paper_jobs_<brand>.jsonl  - the printed lines of every print job produced
   by scripted flows (receipts, credit/debit notes, non-fiscal, X/Z reports),
   taken from the simulator's own print_jobs queue. Timestamps normalized.

2. paper_fixed_<name>.txt    - render() outputs for documents built with a
   FIXED timestamp (fully deterministic, no normalization needed), covering
   the company block, multi-rate breakdowns, amount-in-words, etc.

3. words.txt                 - number_to_words() golden table.

Usage:
    python tools/golden/gen_paper.py
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from datetime import datetime  # noqa: E402

from fiscalsim import render as paper  # noqa: E402
from fiscalsim.simulator import create_simulator  # noqa: E402

OUT_DIR = os.path.join(ROOT, "testdata", "golden")

# "15/01/2026  10:30:00" as rendered by strftime("%d/%m/%Y  %H:%M:%S")
PAPER_TS_RE = re.compile(r"\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}")

FIXED_TS = datetime(2026, 1, 15, 10, 30, 0)

COMPANY = {
    "rif": "J-12345678-9",
    "razon_social": "COMERCIAL LOS SIMULADORES C.A.",
    "direccion": "Avenida Principal de Los Chaguaramos, Edificio Fiscal, Piso 4, Oficina B",
    "municipio": "CHACAO",
    "ciudad": "CARACAS",
    "estado": "MIRANDA",
    "telefono": "0212-9555123",
    "email": "facturacion@simuladores.com.ve",
    "representante_legal": "JUAN PEREZ RODRIGUEZ",
    "cedula_representante": "V-12345678",
    "actividad_economica": "VENTA DE EQUIPOS DE OFICINA Y SUMINISTROS",
    "nif": "",
    "moneda": "Bs.",
    "logo_text": "LOS SIMULADORES",
    "condiciones_pago": "CONTADO 30 DIAS",
    "contribuyente_especial": True,
    "agente_retencion": True,
}


def normalize(text: str) -> str:
    return PAPER_TS_RE.sub("<TS>", text)


def dump_lines(fh, scenario, lines):
    for line in lines:
        fh.write("%s\t%s\n" % (scenario, normalize(line)))


# ---------------------------------------------------------------------------
# 1. Jobs from scripted flows (per brand)
# ---------------------------------------------------------------------------

def job_flows():
    """Yield (brand, scenario, list_of_commands) flows that produce print jobs."""
    yield "tfhka", "invoice_x_z", [
        "iR*J-12345678-9",
        "iS*EMPRESA C.A.",
        "i01Av. Principal, Caracas",
        "!   1.000     15.00 CAFE",
        '"   2.000      8.00 PAN',
        "3",
        "10031.00",
        "101",
        "U0X",
        "U0Z",
    ]
    yield "tfhka", "credit_note", [
        "d1",
        "iR*J-12345678-9",
        "iF*001",
        "iD*2024-01-15",
        "iI*MLTFHKA001",
        "d1   1.000     15.00 CAFE",
        "101",
    ]
    yield "tfhka", "debit_note", [
        "d2",
        "`1   1.000     15.00 CAFE",
        "101",
    ]
    yield "tfhka", "non_fiscal", [
        "80$",
        "80!PRESUPUESTO",
        "81",
    ]
    yield "hasar", "invoice_x_z", [
        "@CustomerData|J-12345678-9|EMPRESA C.A.|Av Principal",
        "@OpenFiscalReceipt",
        "@PrintLine|Cafe|2|15.00|general",
        "@PrintLine|Pan|3|8.00|reduced",
        "@Subtotal",
        "@AddPayment|100.00|cash",
        "@Close",
        "@PrintXReport",
        "@PrintZReport",
    ]
    yield "bixolon", "invoice", [
        "@OpenFiscalReceipt",
        "@PrintLine|Item1|1|100.00|general",
        "@AddPayment|116.00|cash",
        "@Close",
    ]
    yield "epson", "invoice", [
        "@OpenFiscalReceipt",
        "@PrintLine|Item1|1|500.00|general",
        "@AddPayment|580.00|cash",
        "@Close",
        "@PrintZReport",
    ]


def gen_jobs():
    for brand, scenario, commands in job_flows():
        path = os.path.join(OUT_DIR, f"paper_jobs_{brand}.jsonl")
        sim = create_simulator(brand)
        for cmd in commands:
            sim.process_command(cmd)
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            for job in sim.state.print_jobs:
                tag = "%s/%s/%d" % (scenario, job["kind"], job["id"])
                for line in job["lines"]:
                    fh.write("%s\t%s\n" % (tag, normalize(line)))
        print(f"jobs {brand}/{scenario}: {len(sim.state.print_jobs)} jobs")


# ---------------------------------------------------------------------------
# 2. Fixed-timestamp renders (deterministic)
# ---------------------------------------------------------------------------

def base_doc(**kw):
    doc = {
        "type": "invoice",
        "number": 42,
        "items": [],
        "subtotal_bases": 0.0,
        "subtotal_tax": 0.0,
        "total": 0.0,
        "customer": {"rif": "", "name": "", "address": ""},
        "payments": {},
        "paid": 0.0,
        "change": 0.0,
        "timestamp": FIXED_TS,
        "serial_number": "MLTFHKA001",
        "rif": "J-12345678-9",
        "company": dict(COMPANY),
        "reference_invoice": "",
        "reference_date": "",
        "reference_serial": "",
    }
    doc.update(kw)
    return doc


def gen_fixed():
    files = {}

    # Multi-rate receipt with customer, payments and change
    items = [
        {"description": "CAFE EXCLUSIVO DE VENEZUELA", "quantity": 2,
         "price": 15.5, "tax_type": "general", "tax_rate": 16.0,
         "base": 26.724137931034484, "tax": 3.2758620689655172, "total": 31.0},
        {"description": "PAN", "quantity": 3, "price": 8.0,
         "tax_type": "reduced", "tax_rate": 8.0,
         "base": 22.22222222222222, "tax": 1.7777777777777777, "total": 24.0},
        {"description": "LICORES FINOS", "quantity": 1, "price": 100.0,
         "tax_type": "additional", "tax_rate": 30.0,
         "base": 76.92307692307692, "tax": 23.076923076923077, "total": 100.0},
        {"description": "PAN EXENTO", "quantity": 1, "price": 5.0,
         "tax_type": "exempt", "tax_rate": 0.0,
         "base": 5.0, "tax": 0.0, "total": 5.0},
    ]
    receipt = base_doc(
        items=items,
        subtotal_bases=130.86943707633362,
        subtotal_tax=28.13056292366648,
        total=159.0,
        customer={"rif": "V-12345678", "name": "MARIA GARCIA DE LOPEZ",
                  "address": "Calle El Sol, Qta La Esperanza, Urb Las Flores"},
        payments={"cash": 200.0, "card": 0.0},
        paid=200.0,
        change=41.0,
    )
    files["paper_fixed_receipt.txt"] = paper.render_receipt(receipt, COMPANY)

    # Credit note with reference data
    cn_items = [{"description": "CAFE", "quantity": 1, "price": 15.0,
                 "tax_type": "general", "tax_rate": 16.0,
                 "base": 12.931034482758621, "tax": 2.0689655172413794,
                 "total": 15.0}]
    credit = base_doc(
        type="credit_note", number=7, items=cn_items,
        subtotal_bases=12.931034482758621, subtotal_tax=2.0689655172413794,
        total=15.0,
        payments={"cash": 15.0}, paid=15.0,
        reference_invoice="00000041", reference_date="2026-01-10",
        reference_serial="MLTFHKA001",
    )
    files["paper_fixed_credit.txt"] = paper.render_receipt(credit, COMPANY)

    # Debit note
    debit = base_doc(
        type="debit_note", number=3, items=cn_items,
        subtotal_bases=12.931034482758621, subtotal_tax=2.0689655172413794,
        total=15.0,
        payments={"transfer": 15.0}, paid=15.0,
        reference_invoice="00000040",
    )
    files["paper_fixed_debit.txt"] = paper.render_receipt(debit, COMPANY)

    # Bare consumer (no customer data)
    final_consumer = base_doc(
        items=[{"description": "ITEM", "quantity": 1, "price": 10.0,
                "tax_type": "general", "tax_rate": 16.0,
                "base": 8.620689655172413, "tax": 1.3793103448275863,
                "total": 10.0}],
        subtotal_bases=8.620689655172413, subtotal_tax=1.3793103448275863,
        total=10.0, payments={"cash": 10.0}, paid=10.0,
    )
    files["paper_fixed_consumer.txt"] = paper.render_receipt(final_consumer, COMPANY)

    # Non-fiscal document
    nf = base_doc(
        type="non_fiscal", number=9,
        items=[{"description": "PRESUPUESTO DE OBRA NRO 9"},
               {"description": "Linea muy larga de texto no fiscal que debe envolverse en varias lineas de papel"},
               {"description": "Total estimado: Bs. 1.500,00"}],
    )
    files["paper_fixed_nonfiscal.txt"] = paper.render_non_fiscal(nf, COMPANY)

    # X report
    x_report = {
        "type": "X", "number": 12, "timestamp": FIXED_TS,
        "last_invoice": 42, "last_credit_note": 7, "last_debit_note": 3,
        "total_sales": 159.0, "total_tax": 28.13,
        "daily_invoices": 5, "daily_credit_notes": 1, "daily_debit_notes": 1,
        "daily_non_fiscal": 2,
        "tax_totals": {
            "general": {"base": 60.0, "tax": 9.6},
            "reduced": {"base": 40.0, "tax": 3.2},
            "additional": {"base": 50.0, "tax": 15.0},
            "exempt": {"base": 0.0, "tax": 0.0},
        },
        "payments": {"cash": 100.0, "card": 59.0, "transfer": 0.0},
    }
    files["paper_fixed_xreport.txt"] = paper.render_x_report(x_report, COMPANY)

    # Z report (with discounts/surcharges lines)
    z_report = dict(x_report)
    z_report = {**x_report, "type": "Z", "number": 13,
                "total_discounts": 5.0, "total_surcharges": 2.5}
    files["paper_fixed_zreport.txt"] = paper.render_z_report(z_report, COMPANY)

    # Empty X report (no sales, no payments)
    empty_x = {
        "type": "X", "number": 1, "timestamp": FIXED_TS,
        "last_invoice": 0, "last_credit_note": 0, "last_debit_note": 0,
        "total_sales": 0.0, "total_tax": 0.0,
        "daily_invoices": 0, "daily_credit_notes": 0, "daily_debit_notes": 0,
        "daily_non_fiscal": 0,
        "tax_totals": {"general": {"base": 0.0, "tax": 0.0},
                       "reduced": {"base": 0.0, "tax": 0.0},
                       "additional": {"base": 0.0, "tax": 0.0},
                       "exempt": {"base": 0.0, "tax": 0.0}},
        "payments": {},
    }
    files["paper_fixed_empty_x.txt"] = paper.render_x_report(empty_x, COMPANY)

    # Live preview: build an open document through the real simulator
    sim = create_simulator("tfhka")
    sim.process_command("iR*J-99999999-9")
    sim.process_command("iS*CLIENTE EN CURSO")
    sim.process_command("!   1.000     15.00 CAFE")
    sim.process_command("10015.00")
    files["paper_fixed_preview.txt"] = (
        [normalize(l) for l in paper.render_open_document(sim.state)])
    # Closed-document preview must be empty
    sim.process_command("101")
    files["paper_fixed_preview_closed.txt"] = paper.render_open_document(sim.state)

    # Empty company (all optional fields blank)
    empty_company = {k: (False if isinstance(v, bool) else "")
                     for k, v in COMPANY.items()}
    empty_company["contribuyente_especial"] = False
    empty_company["agente_retencion"] = False
    bare = base_doc(
        items=[{"description": "X", "quantity": 1, "price": 1.0,
                "tax_type": "general", "tax_rate": 16.0,
                "base": 0.8620689655172413, "tax": 0.13793103448275863,
                "total": 1.0}],
        subtotal_bases=0.8620689655172413, subtotal_tax=0.13793103448275863,
        total=1.0, company=empty_company,
    )
    files["paper_fixed_bare_company.txt"] = paper.render_receipt(bare, empty_company)

    for name, lines in files.items():
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            for line in lines:
                fh.write(line + "\n")
        print(f"{name}: {len(lines)} lines")


# ---------------------------------------------------------------------------
# 3. number_to_words golden table
# ---------------------------------------------------------------------------

WORD_AMOUNTS = [
    0, 0.05, 0.1, 1, 1.99, 10, 15, 21, 29, 30, 99, 100, 101, 115, 999,
    1000, 1001, 1999, 9999, 10000, 21000, 100000, 999999, 1000000,
    1000001, 1500000, 3000000, 999999999, 123456789.10, 2500000.5,
    0.005, 1.005, 10.015, 1234.567,
]


def gen_words():
    path = os.path.join(OUT_DIR, "words.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for amount in WORD_AMOUNTS:
            fh.write("%s\t%s\n" % (repr(amount) if not isinstance(amount, int)
                                   else str(amount),
                                   paper.number_to_words(amount)))
    print(f"words.txt: {len(WORD_AMOUNTS)} entries")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # jobs files are appended per scenario -> start clean
    for brand in BRANDS:
        path = os.path.join(OUT_DIR, f"paper_jobs_{brand}.jsonl")
        if os.path.exists(path):
            os.remove(path)
    gen_jobs()
    gen_fixed()
    gen_words()


BRANDS = ["tfhka", "hasar", "bixolon", "epson"]

if __name__ == "__main__":
    main()
