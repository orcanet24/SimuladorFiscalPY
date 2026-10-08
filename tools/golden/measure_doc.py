import json
import sys

sys.path.insert(0, ".")
from datetime import datetime

import fiscalsim.state as S
from fiscalsim.simulator import create_simulator

lens = []
orig = S.FiscalPrinterState.close_document


def patched(self):
    d = orig(self)
    if d is not None:
        lens.append((len(str(d)), len(json.dumps(d, default=str))))
    return d


FLOWS = {
    "tfhka": ["iR*J-12345678-9", "iS*EMPRESA DE PRUEBA C.A.",
              "i01Av. Principal, Caracas",
              "iR*J-12345678-9", "iS*EMPRESA DE PRUEBA C.A.",
              "i01Av. Principal, Caracas",
              "!   2.000     15.00 CAFE", '"   3.000      8.00 PAN',
              "3", "10054.00", "101"],
    "hasar": ["@CustomerData|J-12345678-9|EMPRESA DE PRUEBA C.A.|Av. Principal, Caracas",
              "@OpenFiscalReceipt", "@PrintLine|CAFE|2|15.00|general",
              "@PrintLine|PAN|3|8.00|reduced", "@Subtotal",
              "@AddPayment|54.00|cash", "@Close"],
    "bixolon": ["@CustomerData|J-12345678-9|EMPRESA DE PRUEBA C.A.|Av. Principal, Caracas",
                "@OpenFiscalReceipt", "@PrintLine|CAFE|2|15.00|general",
                "@PrintLine|PAN|3|8.00|reduced", "@Subtotal",
                "@AddPayment|54.00|cash", "@Close"],
    "epson": ["@CustomerData|J-12345678-9|EMPRESA DE PRUEBA C.A.|Av. Principal, Caracas",
              "@OpenFiscalReceipt", "@PrintLine|CAFE|2|15.00|general",
              "@PrintLine|PAN|3|8.00|reduced", "@Subtotal",
              "@AddPayment|54.00|cash", "@Close"],
}

S.FiscalPrinterState.close_document = patched
for brand, cmds in FLOWS.items():
    lens.clear()
    sim = create_simulator(brand)
    for c in cmds:
        sim.process_command(c)
    st = sim.state
    print(f"{brand}: str(doc)={lens[0][0] if lens else '-'} "
          f"json(doc)={lens[0][1] if lens else '-'} "
          f"used={st.audit_memory_used!r} free={st.audit_memory_free!r} "
          f"pct={round(100 * st.audit_memory_used / max(st.audit_memory_total, 0.001), 1)}")
