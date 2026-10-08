#!/usr/bin/env python3
"""
Generate golden command/response files from the Python reference simulator.

Runs a corpus of protocol commands (all 4 brands) through the *unmodified*
Python simulator and dumps every response to testdata/golden/commands_<brand>.jsonl.

The Go port must reproduce these responses byte-for-byte (timestamps aside).

Usage:
    python tools/golden/gen_commands.py
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from fiscalsim.simulator import create_simulator  # noqa: E402

OUT_DIR = os.path.join(ROOT, "testdata", "golden")

# S1 embeds datetime.now() as "YYYY-MM-DD HH:MM:SS" inside the response.
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------

# TFHKA ASCII protocol scenarios
TFHKA_CORPUS = [
    ("invoice_full", [
        "iR*J-12345678-9",
        "iS*EMPRESA DE PRUEBA C.A.",
        "i01Av. Principal, Caracas",
        "i020414-1234567",
        "!   1.000     15.00 CAFE",
        '"   2.000      8.00 PAN',
        "#   1.000   1000.00 LICORES",
        "3",
        "1002031.00",
        "101",
        "S1",
        "U0X",
        "U0Z",
    ]),
    ("credit_note", [
        "iR*J-12345678-9",
        "iS*EMPRESA C.A.",
        "!   1.000     15.00 CAFE",
        "10015.00",
        "101",
        "d1",
        "iR*J-12345678-9",
        "iS*EMPRESA C.A.",
        "iF*001",
        "iD*2024-01-15",
        "iI*MLTFHKA001",
        "d1   1.000     15.00 CAFE",
        "101",
        "S2",
    ]),
    ("debit_note", [
        "d2",
        "iR*J-12345678-9",
        "iF*002",
        "`1   1.000     15.00 CAFE",
        "101",
        "S2",
    ]),
    ("non_fiscal", [
        "80$",
        "80!PRESUPUESTO",
        "80*Linea de texto libre",
        "81",
    ]),
    ("status_suite", [
        "S1",
        "S2",
        "S3",
        "S4",
        "S5",
        "S6",
        "S7",
        "S8E",
        "S8P",
    ]),
    ("payments_discounts", [
        "!   1.000    100.00 SERVICIO",
        "70010.00",
        "7015.00",
        "103Pago parcial",
        "10050.00",
        "S4",
        "S2",
        "101",
    ]),
    ("drawer_comment", [
        "0",
        "@COMENTARIO una nota",
        "4",
    ]),
    ("reports_x2_z2", [
        "!   1.000     20.00 TE",
        "10020.00",
        "101",
        "U1X",
        "U1Z",
    ]),
    ("exempt_quirk", [
        "    1.000     10.00 EXENTO",
    ]),
    ("runes_desc", [
        "iS*NIÑO & ASOC.",
        "!   1.000     15.00 CAFÉ ÑUÑOÁ",
        "101",
    ]),
    ("errors_edge", [
        "",
        "   ",
        "FOO",
        "!",
        "!   x.000     15.00 BAD",
        "d1",
        "d1short",
        "`x",
        "100abc",
        "100",
        "700",
        "701",
        "iR*",
        "iS*",
        "i01",
        "iF*",
        "iD*",
        "iI*",
        "@Foo|bar",
        "81",
        "3",
        "101",
        "0",
    ]),
]

# Hasar / Bixolon / Epson IxBatch protocol scenarios (cross-protocol too)
IXBATCH_CORPUS = [
    ("full_flow", [
        "@CustomerData|J-12345678-9|EMPRESA C.A.|Av Principal",
        "@OpenFiscalReceipt",
        "@PrintLine|Cafe|2|15.00|general",
        "@PrintLine|Pan|3|8.00|reduced",
        "@Subtotal",
        "@AddPayment|100.00|cash",
        "@Close",
        "@Status",
        "@PrintZReport",
    ]),
    ("cross_status", [
        "@OpenFiscalReceipt",
        "@PrintLine|Item1|1|100.00|general",
        "@AddPayment|116.00|cash",
        "@Close",
        "S1",
        "S2",
        "S3",
        "S5",
        "S8E",
        "U0X",
        "@PrintZReport",
    ]),
    ("credit_debit_notes", [
        "@OpenCreditNote",
        "@CustomerData|J-12345678-9|EMPRESA C.A.|Av Principal",
        "@PrintLine|Devolucion|1|15.00|general",
        "@Close",
        "@OpenDebitNote",
        "@PrintLine|Recargo|1|10.00|general",
        "@Close",
        "S2",
    ]),
    ("non_fiscal", [
        "@OpenNonFiscalDoc",
        "@PrintNonFiscalText|Hola",
        "@PrintFiscalText|Texto fiscal",
        "@CloseNonFiscalDoc",
    ]),
    ("customer_variants", [
        "@CustomerData|J-1|NOMBRE|DIRECCION",
        "@CustomerData|J-2|SOLO NOMBRE",
        "@CustomerData|J-3",
        "@SetCustomerData|J-4|CLASICO",
        "@SetCustomerTIN|J-555",
        "@SetCustomerInfo1|NOMBRE 1",
        "@SetCustomerInfo2|NOMBRE 2",
        "@SetCustomerExtraData|extra=1",
        "@CustomerData|||",
    ]),
    ("tax_specs", [
        "@OpenFiscalReceipt",
        "@PrintLine|A|1|10|0",
        "@PrintLine|B|1|10|1",
        "@PrintLine|C|1|10|2",
        "@PrintLine|D|1|10|3",
        "@PrintLine|E|1|10|16",
        "@PrintLine|F|1|10|8",
        "@PrintLine|G|1|10|30",
        "@PrintLine|H|1|10|99",
        "@PrintLine|I|1|10|exento",
        "@PrintLine|J|1|10|reducida",
        "@PrintLine|K|1|10|",
        "@PrintLine|L|1|10",
        "@PrintLine|M|1|10|general|Q",
        "@PrintLineItem|N|1|10|general|M",
        "@RefundItem|R|1|10|general",
        "@Close",
    ]),
    ("payments_flow", [
        "@OpenFiscalReceipt",
        "@PrintLine|Cafe|1|30.00|general",
        "@Subtotal",
        "@AddPayment|30.00|tarjeta",
        "@AddPayment|5.50|efectivo",
        "@TotalTender|Efectivo|0|T|0",
        "@LastItemCancel",
        "@LastItemDiscount|5.00|X",
        "@Status",
        "@Close",
        "@PrintXReport",
        "@PrintZReport",
        "@DailyClose|Z",
        "@DailyCloseByDate",
        "@DailyCloseByNumber",
        "@RefundClose|10.00|1",
    ]),
    ("misc_ack", [
        "@OpenDrawer",
        "@OpenDrawer|2",
        "@BarCode|12345",
        "@Login|cajero",
        "@Logoff",
        "@PrintTest",
        "@Reprint",
        "@ReprintByDate|2024-01-01",
        "@ReprintByNumber|1",
        "@SetDate|2024-01-01",
        "@SetTime|10:00:00",
        "@StatusExtra",
        "@ConfigureControllerByOne",
        "@PrintConfigurationData",
        "@ProgramClerk|1",
        "@ProgramPaymentMedia|cash",
        "@ProgramSymbol|Bs.",
        "@ProgramTaxes|16|8|30",
        "@SaveTaxes",
        "@SendRawCommand|raw",
        "@SetHeaderTrailer|H|T",
        "@DisplayCommercial|COMERCIAL",
        "@DisplayDateTime",
        "@DisplayMessage|MSG",
        "@ProgramCommercial|COM",
        "@ProgramMessage|MSG",
        "@FormatCheck|1",
        "@FormatEndorse|1",
        "@ModeSlip",
        "@ModeValidation",
        "@PrintEndorse",
        "@PrintValidation",
        "@ReadMICR",
        "@PrintCashItem",
        "@PrintAuditStatusReport",
        "@TrainingMode",
        "@ResetPrinterBuffer",
        "@CloseFiscalReceipt",
        "@CloseCashReceipt",
        "@DailyClose",
        "@Cancel",
        "@AddPayment|10|cash",
        "@Subtotal",
        "@Status",
    ]),
    ("errors_edge", [
        "@PrintLine|d|x|y",
        "@PrintLine|d|1",
        "@PrintLine",
        "@AddPayment|abc|cash",
        "@AddPayment",
        "@Foo|bar",
        "@",
        "@RefundItem|d|1|10|general",
        "@TotalTender|solo",
        "@DirectPayment",
        "@DirectPayment|x",
        "@RefundClose|10",
        "@DailyCloseX",
        "@Status|extra",
        "S1",
        "U0Z",
        "101",
        "3",
        "",
    ]),
]

BRAND_CORPUS = {
    "tfhka": TFHKA_CORPUS,
    "hasar": IXBATCH_CORPUS,
    "bixolon": IXBATCH_CORPUS,
    "epson": IXBATCH_CORPUS,
}


def normalize(text: str) -> str:
    return TS_RE.sub("<TS>", text)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for brand, corpus in BRAND_CORPUS.items():
        out_path = os.path.join(OUT_DIR, f"commands_{brand}.jsonl")
        count = 0
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            for scenario, commands in corpus:
                sim = create_simulator(brand)  # fresh, no state_path
                for i, cmd in enumerate(commands):
                    response = sim.process_command(cmd)
                    record = {
                        "scenario": scenario,
                        "i": i,
                        "command": cmd,
                        "response": normalize(response),
                    }
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                    count += 1
        print(f"{brand}: {count} responses -> {os.path.relpath(out_path, ROOT)}")


if __name__ == "__main__":
    main()
