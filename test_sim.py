"""
test_sim.py - Test the fiscal printer simulator
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiscalsim.simulator import create_simulator


def test_tfhka():
    """Test TFHKA simulator"""
    sim = create_simulator("tfhka")
    
    # Open invoice with customer data
    sim.process_command("iR*J-12345678-9")
    sim.process_command("iS*EMPRESA DE PRUEBA C.A.")
    sim.process_command("i01Av. Principal, Caracas")
    
    # Print items using TFHKA format: prefix + qty(8.3) + price(10.2) + desc
    # qty(8.3) = 8 chars with 3 decimals: "   1.000"
    # price(10.2) = 10 chars with 2 decimals: "     15.00"
    r1 = sim.process_command("!   1.000     15.00 CAFE")
    print(f"Item 1: {r1}")
    
    r2 = sim.process_command('"   2.000      8.00 PAN')
    print(f"Item 2: {r2}")
    
    # Subtotal
    r3 = sim.process_command("3")
    print(f"Subtotal: {r3}")
    
    # Payment
    r4 = sim.process_command("10023.00")
    print(f"Payment: {r4}")
    
    # Close
    r5 = sim.process_command("101")
    print(f"Close: {r5}")
    
    # Status
    r6 = sim.process_command("S1")
    print(f"S1: {r6}")
    
    # X Report
    r7 = sim.process_command("U0X")
    print(f"X Report: {r7}")
    
    # Z Report
    r8 = sim.process_command("U0Z")
    print(f"Z Report: {r8}")
    
    print(f"\nInvoices: {sim.state.invoice_counter}")
    print(f"Total sales: {sim.state.total_sales:.2f}")


def test_hasar():
    """Test Hasar IxBatch simulator"""
    sim = create_simulator("hasar")
    
    # Customer data
    r0 = sim.process_command("@CustomerData|J-12345678-9|EMPRESA C.A.|Av Principal")
    print(f"Customer: {r0}")
    
    # Open receipt
    r1 = sim.process_command("@OpenFiscalReceipt")
    print(f"Open: {r1}")
    
    # Print items
    r2 = sim.process_command("@PrintLine|Cafe|2|15.00|general")
    print(f"Item: {r2}")
    
    r3 = sim.process_command("@PrintLine|Pan|3|8.00|reduced")
    print(f"Item: {r3}")
    
    # Subtotal
    r4 = sim.process_command("@Subtotal")
    print(f"Subtotal: {r4}")
    
    # Payment
    r5 = sim.process_command("@AddPayment|100.00|cash")
    print(f"Payment: {r5}")
    
    # Close
    r6 = sim.process_command("@Close")
    print(f"Close: {r6}")
    
    # Status
    r7 = sim.process_command("@Status")
    print(f"Status: {r7}")
    
    # Z Report
    r8 = sim.process_command("@PrintZReport")
    print(f"Z Report: {r8}")
    
    print(f"\nInvoices: {sim.state.invoice_counter}")
    print(f"Total sales: {sim.state.total_sales:.2f}")


def test_bixolon():
    """Test Bixolon simulator"""
    sim = create_simulator("bixolon")
    
    r0 = sim.process_command("@OpenFiscalReceipt")
    print(f"Open: {r0}")
    
    r1 = sim.process_command("@PrintLine|Item1|1|100.00|general")
    print(f"Item: {r1}")
    
    r2 = sim.process_command("@AddPayment|116.00|cash")
    print(f"Payment: {r2}")
    
    r3 = sim.process_command("@Close")
    print(f"Close: {r3}")
    
    r4 = sim.process_command("S1")
    print(f"S1: {r4}")
    
    r5 = sim.process_command("@PrintZReport")
    print(f"Z Report: {r5}")
    
    print(f"\nInvoices: {sim.state.invoice_counter}")


def test_epson():
    """Test Epson simulator"""
    sim = create_simulator("epson")
    
    r1 = sim.process_command("@OpenFiscalReceipt")
    print(f"Open: {r1}")
    
    r2 = sim.process_command("@PrintLine|Item1|1|500.00|general")
    print(f"Item: {r2}")
    
    r3 = sim.process_command("@AddPayment|580.00|cash")
    print(f"Payment: {r3}")
    
    r4 = sim.process_command("@Close")
    print(f"Close: {r4}")
    
    r5 = sim.process_command("S2")
    print(f"S2: {r5}")
    
    r6 = sim.process_command("@PrintZReport")
    print(f"Z Report: {r6}")
    
    print(f"\nInvoices: {sim.state.invoice_counter}")


def test_credit_notes():
    """Test credit note workflow"""
    sim = create_simulator("tfhka")
    
    # First make an invoice
    sim.process_command("iR*J-12345678-9")
    sim.process_command("iS*EMPRESA C.A.")
    sim.process_command("!   1.000     15.00 CAFE")
    sim.process_command("10015.00")
    sim.process_command("101")
    
    # Open credit note (d1 opens credit note document)
    sim.process_command("d1")
    sim.process_command("iR*J-12345678-9")
    sim.process_command("iS*EMPRESA C.A.")
    sim.process_command("iF*001")  # Reference invoice
    sim.process_command("iD*2024-01-15")  # Original date
    sim.process_command("iI*MLTFHKA001")  # Fiscal serial
    
    # Credit note item: d + tax_type + qty(8.3) + price(10.2) + desc
    r = sim.process_command("d1   1.000     15.00 CAFE")
    print(f"Credit note item: {r}")
    
    r = sim.process_command("101")
    print(f"Close credit note: {r}")
    
    print(f"\nInvoices: {sim.state.invoice_counter}")
    print(f"Credit Notes: {sim.state.credit_note_counter}")


def test_non_fiscal():
    """Test non-fiscal document"""
    sim = create_simulator("tfhka")
    
    r1 = sim.process_command("80$")
    print(f"Open NF: {r1}")
    
    r2 = sim.process_command("80!PRESUPUESTO")
    print(f"Print NF: {r2}")
    
    r3 = sim.process_command("80*Linea de texto libre")
    print(f"Print NF content: {r3}")
    
    r4 = sim.process_command("81")
    print(f"Close NF: {r4}")
    
    print(f"\nNon-fiscal: {sim.state.non_fiscal_counter}")


def test_x_report():
    """Test X report without reset"""
    sim = create_simulator("tfhka")
    
    # Make some sales
    sim.process_command("!   1.000     15.00 CAFE")
    sim.process_command("10015.00")
    sim.process_command("101")
    
    sim.process_command("!   1.000     20.00 TE")
    sim.process_command("10020.00")
    sim.process_command("101")
    
    r1 = sim.process_command("U0X")
    print(f"X Report 1: {r1}")
    print(f"Total sales after X: {sim.state.total_sales:.2f}")
    
    r2 = sim.process_command("U0X")
    print(f"X Report 2: {r2}")
    print(f"Total sales after X2: {sim.state.total_sales:.2f}")


def test_z_report():
    """Test Z report with reset"""
    sim = create_simulator("tfhka")
    
    # Make some sales
    sim.process_command("!   1.000     15.00 CAFE")
    sim.process_command("10015.00")
    sim.process_command("101")
    
    print(f"Total before Z: {sim.state.total_sales:.2f}")
    
    r1 = sim.process_command("U0Z")
    print(f"Z Report: {r1}")
    print(f"Total after Z: {sim.state.total_sales:.2f}")
    print(f"Z counter: {sim.state.z_report_counter}")


if __name__ == "__main__":
    print("=" * 60)
    print("TFHKA TEST")
    print("=" * 60)
    test_tfhka()
    
    print("\n" + "=" * 60)
    print("HASAR TEST")
    print("=" * 60)
    test_hasar()
    
    print("\n" + "=" * 60)
    print("BIXOLON TEST")
    print("=" * 60)
    test_bixolon()
    
    print("\n" + "=" * 60)
    print("EPSON TEST")
    print("=" * 60)
    test_epson()
    
    print("\n" + "=" * 60)
    print("CREDIT NOTES TEST")
    print("=" * 60)
    test_credit_notes()
    
    print("\n" + "=" * 60)
    print("NON-FISCAL TEST")
    print("=" * 60)
    test_non_fiscal()
    
    print("\n" + "=" * 60)
    print("X REPORT TEST")
    print("=" * 60)
    test_x_report()
    
    print("\n" + "=" * 60)
    print("Z REPORT TEST")
    print("=" * 60)
    test_z_report()
