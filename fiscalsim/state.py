"""
Fiscal Printer Internal State
Maintains realistic state for all printer brands
"""

from datetime import datetime, date
from typing import List, Dict, Optional
import threading


class FiscalPrinterState:
    """Represents the internal state of a fiscal printer"""
    
    def __init__(self, brand: str = "TFHKA", model: str = "TFHKA"):
        # Identity
        self.brand = brand.upper()
        self.model = model.upper()
        self.serial_number = f"ML{brand[:2].upper()}{model[:3].upper()}{10000:05d}"
        self.fiscal_registration = "J-12345678-9"
        self.rif = "J-12345678-9"
        
        # Mode and status
        self.mode = "fiscal"  # test or fiscal
        self.memory_status = "ok"  # ok, almost_full, full
        self.current_state = "waiting"  # waiting, fiscal, non_fiscal
        
        # Counters
        self.fiscal_counter = 0  # Fiscal document counter
        self.invoice_counter = 0
        self.credit_note_counter = 0
        self.debit_note_counter = 0
        self.non_fiscal_counter = 0
        self.z_report_counter = 0
        self.x_report_counter = 0
        self.daily_closure_counter = 0
        
        # Lifetime totals (never reset - accumulated since machine programming)
        self.total_sales = 0.0
        self.total_tax = 0.0
        self.total_discounts = 0.0
        self.total_surcharges = 0.0

        # Daily totals (reset on Z report only)
        self.daily_sales = 0.0
        self.daily_tax = 0.0
        self.daily_discounts = 0.0
        self.daily_surcharges = 0.0
        self.daily_invoices = 0
        self.daily_credit_notes = 0
        self.daily_debit_notes = 0
        self.daily_non_fiscal = 0
        
        # Tax totals by rate
        self.tax_totals = {
            "general": {"base": 0.0, "tax": 0.0},
            "reduced": {"base": 0.0, "tax": 0.0},
            "additional": {"base": 0.0, "tax": 0.0},
            "exempt": {"base": 0.0, "tax": 0.0},
        }
        
        # Credit note totals
        self.credit_note_totals = {
            "general": {"base": 0.0, "tax": 0.0},
            "reduced": {"base": 0.0, "tax": 0.0},
            "additional": {"base": 0.0, "tax": 0.0},
            "exempt": {"base": 0.0, "tax": 0.0},
        }
        
        # Debit note totals
        self.debit_note_totals = {
            "general": {"base": 0.0, "tax": 0.0},
            "reduced": {"base": 0.0, "tax": 0.0},
            "additional": {"base": 0.0, "tax": 0.0},
            "exempt": {"base": 0.0, "tax": 0.0},
        }
        
        # Payment totals by method
        self.payment_totals: Dict[str, float] = {}
        
        # Tax rates (Venezuela defaults)
        self.tax_rates = {
            "general": 16.0,      # Tasa General
            "reduced": 8.0,       # Tasa Reducida
            "additional": 30.0,   # Tasa Adicional (formerly 25% but 30% common now)
        }
        self.tax_type = 1  # 1=included, 2=excluded
        
        # Current document
        self.current_document = None
        self.document_open = False
        self.document_type = None  # invoice, credit_note, debit_note, non_fiscal
        self.current_items: List[Dict] = []
        self.current_customer = None
        self.subtotal_bases = 0.0
        self.subtotal_tax = 0.0
        self.amount_payable = 0.0
        self.payments_made = 0.0
        self.payment_count = 0
        self.subtotal_printed = False        # Customer info
        self.customer_rif = ""
        self.customer_name = ""
        self.customer_address = ""
        self.customer_phone = ""
        self.reference_invoice = ""
        self.reference_date = ""
        self.reference_serial = ""
        # Payments of the current document only
        self.doc_payments: Dict[str, float] = {}
    
        # Reports storage
        self.z_reports: List[Dict] = []
        self.x_reports: List[Dict] = []
        self.print_jobs: List[Dict] = []
        self.print_job_seq = 0

        # Company data programmed into the fiscal memory
        # (data required by law on every fiscal receipt)
        self.company = {
            "rif": "",
            "razon_social": "",
            "direccion": "",        # domicilio fiscal (calle/avenida/urbo)
            "municipio": "",
            "ciudad": "",
            "estado": "",
            "telefono": "",
            "email": "",
            "representante_legal": "",
            "cedula_representante": "",
            "actividad_economica": "",
            "nif": "",
            "moneda": "Bs.",
            "logo_text": "",
            "condiciones_pago": "CONTADO",
            "contribuyente_especial": False,
            "agente_retencion": False,
        }
        
        # Date tracking
        self.last_invoice_date = None
        self.last_z_report_date = None
        self.current_date = date.today()
        
        # Paper status
        self.has_paper = True
        self.paper_jam = False
        self.cover_open = False
        
        # Audit memory (MB)
        self.audit_memory_number = 1
        self.audit_memory_total = 4.0  # 4MB
        self.audit_memory_free = 3.5   # 3.5MB free
        self.audit_memory_used = 0.5   # Used
        
        # Flags
        self.flags = {
            "print_logo": False,
            "reduce_z_report": False,
            "print_z_report_items": False,
            "print_customer_data": False,
            "dont_open_drawer": False,
            "paper_sensor_enabled": True,
        }
        
        # Header and footer lines
        self.headers = [
            "RIF: J-12345678-9",
            "FACTURA FISCAL",
            "AVENIDA PRINCIPAL",
            "CARACAS - VENEZUELA",
            "",
            "",
            "",
            "",
        ]
        self.footers = {
            "footer1": "GRACIAS POR SU COMPRA",
            "footer2": "",
            "footer3": "",
            "footer4": "",
            "footer5": "",
            "footer6": "",
            "footer7": "",
            "footer8": "",
        }
        
        # Lock
        self.lock = threading.Lock()
    
    def program_company(self, data: Dict) -> Dict:
        """Program the company data into the fiscal memory.
        
        This is the data that law requires on every fiscal receipt:
        RIF, razón social, domicilio fiscal, representante legal, etc.
        """
        for key, value in data.items():
            if key in self.company:
                self.company[key] = value
        
        # Keep machine RIF in sync with the programmed company RIF
        if self.company.get("rif"):
            self.rif = self.company["rif"]
            self.fiscal_registration = self.company["rif"]
        
        # Regenerate the 8 fiscal header lines (S8E)
        c = self.company
        logo = c.get("logo_text") or c.get("razon_social") or ""
        addr = c.get("direccion") or ""
        locality = " - ".join(
            p for p in [c.get("municipio"), c.get("estado")] if p
        )
        self.headers = [
            logo[:40],
            f"RIF: {c.get('rif', '')}"[:40],
            addr[:40],
            locality[:40],
            f"TEL: {c.get('telefono', '')}"[:40] if c.get("telefono") else "",
            f"REP. LEGAL: {c.get('representante_legal', '')}"[:40] if c.get("representante_legal") else "",
            "",
            "",
        ]
        return dict(self.company)
    
    def get_status_code(self) -> int:
        """Get current status byte"""
        mode_val = 0 if self.mode == "test" else 4
        if self.mode == "fiscal":
            if self.current_state == "waiting":
                if self.memory_status == "ok":
                    return 0x04
                elif self.memory_status == "almost_full":
                    return 0x07
                else:
                    return 0x0A
            elif self.current_state == "fiscal":
                if self.memory_status == "ok":
                    return 0x05
                elif self.memory_status == "almost_full":
                    return 0x08
                else:
                    return 0x0B
            elif self.current_state == "non_fiscal":
                if self.memory_status == "ok":
                    return 0x06
                elif self.memory_status == "almost_full":
                    return 0x09
                else:
                    return 0x0C
        return 0x04
    
    def get_error_code(self) -> int:
        """Get error code"""
        if not self.has_paper:
            return 0x01
        if self.paper_jam:
            return 0x02
        if self.audit_memory_free <= 0.01:
            return 0x6C
        return 0x00
    
    def calculate_item_tax(self, price: float, tax_rate: float) -> tuple:
        """Calculate base and tax amount for an item"""
        if self.tax_type == 1:  # Tax included in price
            base = price / (1 + tax_rate / 100)
            tax = price - base
        else:  # Tax excluded
            base = price
            tax = price * tax_rate / 100
        return base, tax
    
    def add_item(self, description: str, quantity: float, price: float, 
                 tax_type: str = "general"):
        """Add an item to the current document"""
        tax_rate = self.tax_rates.get(tax_type, 16.0)
        if tax_type == "exempt":
            tax_rate = 0.0
        
        base, tax = self.calculate_item_tax(price, tax_rate)
        
        item = {
            "description": description,
            "quantity": quantity,
            "price": price,
            "tax_type": tax_type,
            "tax_rate": tax_rate,
            "base": base * quantity,
            "tax": tax * quantity,
            "total": (base + tax) * quantity,
        }
        
        self.current_items.append(item)
        self.subtotal_bases += item["base"]
        self.subtotal_tax += item["tax"]
        self.amount_payable += item["total"]
        
        # Update tax totals
        self.tax_totals[tax_type]["base"] += item["base"]
        self.tax_totals[tax_type]["tax"] += item["tax"]
        
        # Update daily totals
        self.total_sales += item["total"]
        self.total_tax += item["tax"]
        self.daily_sales += item["total"]
        self.daily_tax += item["tax"]
        
        return item
    
    def add_payment(self, amount: float, method: str = "cash"):
        """Add a payment"""
        self.payments_made += amount
        self.payment_count += 1
        self.amount_payable -= amount
        
        self.payment_totals[method] = self.payment_totals.get(method, 0.0) + amount
        self.doc_payments[method] = self.doc_payments.get(method, 0.0) + amount
    
    def open_document(self, doc_type: str):
        """Open a new document"""
        self.document_open = True
        self.document_type = doc_type
        self.current_items = []
        self.subtotal_bases = 0.0
        self.subtotal_tax = 0.0
        self.amount_payable = 0.0
        self.payments_made = 0.0
        self.payment_count = 0
        self.doc_payments = {}
        self.subtotal_printed = False
        self.current_state = "fiscal" if doc_type != "non_fiscal" else "non_fiscal"
    
    def close_document(self):
        """Close the current document"""
        if not self.document_open:
            return None
        
        doc = {
            "type": self.document_type,
            "number": 0,
            "items": list(self.current_items),
            "subtotal_bases": self.subtotal_bases,
            "subtotal_tax": self.subtotal_tax,
            "total": self.subtotal_bases + self.subtotal_tax,
            "customer": {
                "rif": self.customer_rif,
                "name": self.customer_name,
                "address": self.customer_address,
            },
            "payments": {},
            "timestamp": datetime.now(),
        }
        
        if self.document_type == "invoice":
            self.invoice_counter += 1
            self.fiscal_counter += 1
            self.daily_invoices += 1
            doc["number"] = self.invoice_counter
            self.last_invoice_date = datetime.now()
        elif self.document_type == "credit_note":
            self.credit_note_counter += 1
            self.fiscal_counter += 1
            self.daily_credit_notes += 1
            doc["number"] = self.credit_note_counter
            doc["reference_invoice"] = self.reference_invoice
        elif self.document_type == "debit_note":
            self.debit_note_counter += 1
            self.fiscal_counter += 1
            self.daily_debit_notes += 1
            doc["number"] = self.debit_note_counter
            doc["reference_invoice"] = self.reference_invoice
        elif self.document_type == "non_fiscal":
            self.non_fiscal_counter += 1
            self.daily_non_fiscal += 1
            doc["number"] = self.non_fiscal_counter
        
        doc["payments"] = dict(self.doc_payments)
        doc["paid"] = self.payments_made
        doc["change"] = max(0.0, self.payments_made - (self.subtotal_bases + self.subtotal_tax))
        doc["serial_number"] = self.serial_number
        doc["rif"] = self.rif
        doc["company"] = dict(self.company)
        doc["reference_date"] = self.reference_date
        doc["reference_serial"] = self.reference_serial
        
        self.document_open = False
        self.document_type = None
        self.current_state = "waiting"
        self.current_items = []
        # Reset document-scoped accumulators (totals were snapshotted above)
        self.subtotal_bases = 0.0
        self.subtotal_tax = 0.0
        self.amount_payable = 0.0
        self.payments_made = 0.0
        self.payment_count = 0
        self.doc_payments = {}
        self.subtotal_printed = False
        # Customer/reference data does not carry over to the next document
        self.customer_rif = ""
        self.customer_name = ""
        self.customer_address = ""
        self.customer_phone = ""
        self.reference_invoice = ""
        self.reference_date = ""
        self.reference_serial = ""
        
        # Update audit memory
        doc_size_kb = len(str(doc)) / 1024
        self.audit_memory_used += doc_size_kb / 1024  # MB
        self.audit_memory_free = self.audit_memory_total - self.audit_memory_used
        
        return doc
    
    def generate_z_report(self) -> Dict:
        """Generate a Z report (daily closure)"""
        z = {
            "type": "Z",
            "number": self.z_report_counter + 1,
            "timestamp": datetime.now(),
            "last_invoice": self.invoice_counter,
            "last_credit_note": self.credit_note_counter,
            "last_debit_note": self.debit_note_counter,
            "total_sales": self.daily_sales,
            "total_tax": self.daily_tax,
            "total_discounts": self.daily_discounts,
            "total_surcharges": self.daily_surcharges,
            "daily_invoices": self.daily_invoices,
            "daily_credit_notes": self.daily_credit_notes,
            "daily_debit_notes": self.daily_debit_notes,
            "daily_non_fiscal": self.daily_non_fiscal,
            "lifetime_sales": self.total_sales,
            "lifetime_tax": self.total_tax,
            "tax_totals": {
                "general": dict(self.tax_totals["general"]),
                "reduced": dict(self.tax_totals["reduced"]),
                "additional": dict(self.tax_totals["additional"]),
                "exempt": dict(self.tax_totals["exempt"]),
            },
            "credit_note_totals": {
                "general": dict(self.credit_note_totals["general"]),
                "reduced": dict(self.credit_note_totals["reduced"]),
                "additional": dict(self.credit_note_totals["additional"]),
                "exempt": dict(self.credit_note_totals["exempt"]),
            },
            "debit_note_totals": {
                "general": dict(self.debit_note_totals["general"]),
                "reduced": dict(self.debit_note_totals["reduced"]),
                "additional": dict(self.debit_note_totals["additional"]),
                "exempt": dict(self.debit_note_totals["exempt"]),
            },
            "payments": dict(self.payment_totals),
        }
        
        self.z_report_counter += 1
        self.daily_closure_counter += 1
        self.last_z_report_date = datetime.now()
        self.z_reports.append(z)
        
        # Reset only daily totals - lifetime counters/totals are never reset
        self.daily_sales = 0.0
        self.daily_tax = 0.0
        self.daily_discounts = 0.0
        self.daily_surcharges = 0.0
        self.daily_invoices = 0
        self.daily_credit_notes = 0
        self.daily_debit_notes = 0
        self.daily_non_fiscal = 0
        self.tax_totals = {k: {"base": 0.0, "tax": 0.0} for k in self.tax_totals}
        self.credit_note_totals = {k: {"base": 0.0, "tax": 0.0} for k in self.credit_note_totals}
        self.debit_note_totals = {k: {"base": 0.0, "tax": 0.0} for k in self.debit_note_totals}
        self.payment_totals = {}
        
        return z
    
    def generate_x_report(self) -> Dict:
        """Generate an X report (current totals without reset)"""
        x = {
            "type": "X",
            "number": self.x_report_counter + 1,
            "timestamp": datetime.now(),
            "last_invoice": self.invoice_counter,
            "last_credit_note": self.credit_note_counter,
            "last_debit_note": self.debit_note_counter,
            "total_sales": self.daily_sales,
            "total_tax": self.daily_tax,
            "daily_invoices": self.daily_invoices,
            "daily_credit_notes": self.daily_credit_notes,
            "daily_debit_notes": self.daily_debit_notes,
            "daily_non_fiscal": self.daily_non_fiscal,
            "tax_totals": {
                "general": dict(self.tax_totals["general"]),
                "reduced": dict(self.tax_totals["reduced"]),
                "additional": dict(self.tax_totals["additional"]),
                "exempt": dict(self.tax_totals["exempt"]),
            },
            "payments": dict(self.payment_totals),
        }
        
        self.x_report_counter += 1
        self.x_reports.append(x)
        return x
    
    def get_s1_data(self) -> Dict:
        """Get S1 printer data (general parameters)"""
        return {
            "machine_number": self.serial_number,
            "rif": self.rif,
            "audit_counter": self.fiscal_counter,
            "daily_closure": self.daily_closure_counter,
            "last_invoice": self.invoice_counter,
            "last_credit_note": self.credit_note_counter,
            "last_debit_note": self.debit_note_counter,
            "last_non_fiscal": self.non_fiscal_counter,
            "invoices_today": self.daily_invoices,
            "credit_notes_today": self.daily_credit_notes,
            "debit_notes_today": self.daily_debit_notes,
            "non_fiscal_today": self.daily_non_fiscal,
            "total_sales": self.daily_sales,
            "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cashier_number": 1,
        }
    
    def get_s2_data(self) -> Dict:
        """Get S2 document data (current document totals)"""
        return {
            "condition": 0 if self.document_open else 1,
            "type_document": {
                "invoice": 0,
                "credit_note": 1,
                "debit_note": 2,
            }.get(self.document_type, 0) if self.document_type else 0,
            "quantity_articles": len(self.current_items),
            "subtotal_bases": round(self.subtotal_bases, 2),
            "subtotal_tax": round(self.subtotal_tax, 2),
            "amount_payable": round(self.amount_payable, 2),
            "payments_made": self.payment_count,
        }
    
    def get_s3_data(self) -> Dict:
        """Get S3 tax configuration"""
        return {
            "tax1": self.tax_rates["general"],
            "tax2": self.tax_rates["reduced"],
            "tax3": self.tax_rates["additional"],
            "type_tax1": self.tax_type,
            "type_tax2": self.tax_type,
            "type_tax3": self.tax_type,
        }
    
    def get_s5_data(self) -> Dict:
        """Get S5 audit memory data"""
        return {
            "machine_number": self.serial_number,
            "rif": self.rif,
            "audit_memory_number": self.audit_memory_number,
            "audit_memory_total": self.audit_memory_total,
            "audit_memory_free": round(self.audit_memory_free, 2),
            "registered_documents": self.fiscal_counter,
        }
