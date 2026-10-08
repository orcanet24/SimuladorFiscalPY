"""
Fiscal Printer Simulator - Base Printer Class
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .state import FiscalPrinterState
from .protocol import (
    TFHKACommands, HasarCommands, STATUS_CODES, ERROR_CODES,
    parse_tfhka_command, parse_ixbatch_command
)
from . import render as paper
from .persistence import save_state, load_state


# "103 <texto>" (PAYMENT_DESC) can declare the method used by the next "100"
_PAYMENT_METHOD_MAP = {
    "cash": "cash", "efectivo": "cash", "money": "cash",
    "card": "card", "tarjeta": "card",
    "transfer": "transfer", "transferencia": "transfer",
    "credit": "credit", "credito": "credit", "crédito": "credit",
    "check": "check", "cheque": "check",
    "mobile": "mobile", "pago movil": "mobile",
}


class FiscalPrinterSimulator:
    """Base fiscal printer simulator"""
    
    def __init__(self, brand: str = "TFHKA", model: str = "TFHKA",
                 state_path: Optional[str] = None):
        self.brand = brand.upper()
        self.model = model.upper()
        self.state = FiscalPrinterState(brand, model)
        self.logger = logging.getLogger(f"fiscalsim.{brand}")
        self.command_count = 0
        self.error_log = []
        self.history = []  # command log shown on the web panel
        self.state_path = state_path
        
        # Brand-specific configuration
        self._configure_brand()
        
        # Restore persisted state if a path was provided
        if state_path:
            load_state(self)
    
    def _configure_brand(self):
        """Configure brand-specific settings"""
        configs = {
            "TFHKA": {
                "serial": "MLTFHKA001",
                "fiscal_reg": "J-12345678-9",
                "memory_total": 4.0,
                "tax_rates": {"general": 16.0, "reduced": 8.0, "additional": 30.0},
            },
            "HASAR": {
                "serial": "MLHSR615F001",
                "fiscal_reg": "J-98765432-1",
                "memory_total": 4.0,
                "tax_rates": {"general": 16.0, "reduced": 8.0, "additional": 30.0},
            },
            "BIXOLON": {
                "serial": "MLBLN270001",
                "fiscal_reg": "J-55556666-3",
                "memory_total": 2.0,
                "tax_rates": {"general": 16.0, "reduced": 8.0, "additional": 30.0},
            },
            "EPSON": {
                "serial": "MLSTM200001",
                "fiscal_reg": "J-44443333-5",
                "memory_total": 8.0,
                "tax_rates": {"general": 16.0, "reduced": 8.0, "additional": 30.0},
            },
        }
        
        config = configs.get(self.brand, configs["TFHKA"])
        self.state.serial_number = config["serial"]
        self.state.fiscal_registration = config["fiscal_reg"]
        self.state.rif = config["fiscal_reg"]
        self.state.audit_memory_total = config["memory_total"]
        self.state.audit_memory_free = config["memory_total"] * 0.9
        self.state.tax_rates = config["tax_rates"]
    
    def process_command(self, command: str) -> str:
        """Process a command and return response"""
        self.command_count += 1
        self.logger.info(f"CMD #{self.command_count}: {command}")
        
        with self.state.lock:
            try:
                response = self._execute_command(command)
                response = self._format_response(response)
                self.logger.info(f"RSP #{self.command_count}: {response}")
            except Exception as e:
                error_msg = f"Error processing command '{command}': {e}"
                self.logger.error(error_msg)
                self.error_log.append({
                    "command": command,
                    "error": str(e),
                    "timestamp": datetime.now(),
                })
                response = self._format_response(
                    f"ERROR|0x50|{str(e)}")
            
            self._log_history(command, response)
            self._save_state()
            return response
    
    def _format_response(self, response: str) -> str:
        """Brand-specific response envelope (Epson overrides this)"""
        return response
    
    def _log_history(self, command: str, response: str) -> None:
        """Append an entry to the command history shown on the panel"""
        entry = {
            "seq": self.command_count,
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "command": command,
            "response": response,
            "ok": ("Error" not in response and "ERROR" not in response),
        }
        self.history.append(entry)
        if len(self.history) > 1000:
            del self.history[:len(self.history) - 1000]
    
    def _save_state(self) -> None:
        if self.state_path:
            save_state(self)
    
    def _execute_command(self, command: str) -> str:
        """Route a command to the right protocol handler"""
        # IxBatch @Commands (except TFHKA's @COMENTARIO)
        if command.startswith("@") and not command.startswith("@COMENTARIO"):
            ixcmd, ixparams = parse_ixbatch_command(command)
            if ixcmd:
                return self._handle_ixbatch(ixcmd, ixparams)
            return "@Response|Error|0x50|Comando desconocido"
        
        # TFHKA ASCII protocol
        cmd_type, params = parse_tfhka_command(command)
        if cmd_type and cmd_type != "UNKNOWN":
            return self._handle_tfhka(cmd_type, params, command)
        
        # Unknown command
        return "ERROR|0x50|Comando desconocido"
    
    # ------------------------------------------------------------------
    # Paper output (virtual print jobs for the web panel)
    # ------------------------------------------------------------------
    
    def _record_paper(self, kind: str, title: str, lines: list,
                      meta: Dict[str, Any] = None) -> Dict:
        """Append a finished print job (receipt/report) to the paper queue"""
        job = {
            "id": self.state.print_job_seq + 1,
            "kind": kind,  # receipt | credit_note | debit_note | non_fiscal | x_report | z_report
            "title": title,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "brand": self.brand,
            "lines": lines,
            "meta": meta or {},
        }
        self.state.print_job_seq += 1
        self.state.print_jobs.append(job)
        # Keep memory bounded: last 200 print jobs
        if len(self.state.print_jobs) > 200:
            del self.state.print_jobs[:len(self.state.print_jobs) - 200]
        return job
    
    def _record_receipt(self, doc: Dict) -> Dict:
        """Render and record a closed document as paper"""
        company = doc.get("company") or self.state.company
        doc_type = doc.get("type", "invoice")
        kind = doc_type if doc_type != "invoice" else "receipt"
        titles = {
            "invoice": f"FACTURA FISCAL N° {doc.get('number', 0):08d}",
            "credit_note": f"NOTA DE CREDITO N° {doc.get('number', 0):08d}",
            "debit_note": f"NOTA DE DEBITO N° {doc.get('number', 0):08d}",
            "non_fiscal": f"DOC NO FISCAL N° {doc.get('number', 0):08d}",
        }
        if doc_type == "non_fiscal":
            lines = paper.render_non_fiscal(doc, company)
        else:
            lines = paper.render_receipt(doc, company)
        meta = {
            "number": doc.get("number", 0),
            "total": round(doc.get("total", 0.0), 2),
            "doc_type": doc_type,
        }
        return self._record_paper(kind, titles.get(doc_type, "DOCUMENTO"),
                                  lines, meta)
    
    def _record_report(self, rep: Dict, kind: str) -> Dict:
        """Render and record an X or Z report as paper"""
        if kind == "X":
            lines = paper.render_x_report(rep, self.state.company)
            title = f"REPORTE X N° {rep.get('number', 0):04d}"
        else:
            lines = paper.render_z_report(rep, self.state.company)
            title = f"REPORTE Z N° {rep.get('number', 0):04d}"
        meta = {
            "number": rep.get("number", 0),
            "total_sales": round(rep.get("total_sales", 0.0), 2),
            "total_tax": round(rep.get("total_tax", 0.0), 2),
        }
        return self._record_paper(f"{kind.lower()}_report", title,
                                  lines, meta)
    
    def program_company(self, data: Dict) -> Dict:
        """Program company data into the fiscal memory (web API/panel)"""
        with self.state.lock:
            result = self.state.program_company(data)
            self._save_state()
            return result
    
    @staticmethod
    def _resolve_tax_name(spec: str) -> str:
        """Resolve a tax spec from an IxBatch host into a state tax name.

        Accepts: numeric TFHKA codes (0-3), names in EN/ES, or a percentage
        (16, 8, 30, 0) matched against the configured rates.
        """
        s = str(spec).strip().lower()
        name_map = {
            "0": "exempt", "exempt": "exempt", "exento": "exempt",
            "1": "general", "general": "general",
            "2": "reduced", "reduced": "reduced", "reducida": "reduced",
            "3": "additional", "additional": "additional",
            "adicional": "additional",
            "": "general",
        }
        if s in name_map:
            return name_map[s]
        try:
            value = float(s)
        except ValueError:
            return "general"
        # Percentage: match against configured rates
        if value == 0:
            return "exempt"
        if value == 16:
            return "general"
        if value == 8:
            return "reduced"
        if value == 30:
            return "additional"
        return "general"
    
    def _handle_tfhka(self, cmd_type: str, params: list, raw: str) -> str:
        """Handle TFHKA ASCII commands"""
        state = self.state
        
        if cmd_type == "ITEM" or cmd_type == "ITEM_CREDIT" or cmd_type == "ITEM_DEBIT":
            return self._handle_item(raw, cmd_type, params)
        
        elif cmd_type == "SUBTOTAL_PRINT":
            state.subtotal_printed = True
            return f"0|Subtotal: {state.subtotal_bases:.2f} + {state.subtotal_tax:.2f} = {state.subtotal_bases + state.subtotal_tax:.2f}"
        
        elif cmd_type == "SUBTOTAL_SILENT":
            return "0|OK"
        
        elif cmd_type == "CLOSE_TOTALIZE":
            if state.document_open:
                doc = state.close_document()
                if doc:
                    job = self._record_receipt(doc)
                    doc_type_names = {
                        "invoice": "Factura",
                        "credit_note": "Nota de Credito",
                        "debit_note": "Nota de Debito",
                        "non_fiscal": "Doc No Fiscal",
                    }
                    name = doc_type_names.get(doc['type'], "Documento")
                    return f"0|{name} {doc['number']}|Total: {doc['total']:.2f}|Impreso:{job['id']}"
            return "0|Cerrado"
        
        elif cmd_type == "OPEN_DRAWER":
            return "0|Gaveta abierta"
        
        elif cmd_type == "OPEN_NON_FISCAL":
            state.open_document("non_fiscal")
            return "0|DNF abierto"
        
        elif cmd_type == "PRINT_NON_FISCAL_TEXT":
            return "0|Texto impreso"
        
        elif cmd_type == "PRINT_NON_FISCAL_CONTENT":
            return "0|Contenido impreso"
        
        elif cmd_type == "CLOSE_NON_FISCAL":
            if state.document_open:
                doc = state.close_document()
                if doc:
                    self._record_receipt(doc)
            return "0|DNF cerrado"
        
        elif cmd_type == "COMMENT":
            return "0|Comentario"
        
        elif cmd_type == "PAYMENT":
            amount = float(params[0]) if params else 0
            # 103 <metodo> fija la forma de pago del siguiente 100
            method = state.pending_payment_method or "cash"
            state.pending_payment_method = ""
            state.add_payment(amount, method)
            return f"0|Pago: {amount:.2f}|Pendiente: {state.amount_payable:.2f}"
        
        elif cmd_type == "PAYMENT_DESC":
            desc = (params[0] if params else "").strip().lower()
            method = _PAYMENT_METHOD_MAP.get(desc)
            if method:
                state.pending_payment_method = method
            return "0|Descripcion pago"
        
        elif cmd_type == "DISCOUNT":
            amount = float(params[0]) if params else 0
            state.total_discounts += amount
            state.amount_payable -= amount
            return f"0|Descuento: {amount:.2f}"
        
        elif cmd_type == "SURCHARGE":
            amount = float(params[0]) if params else 0
            state.total_surcharges += amount
            state.amount_payable += amount
            return f"0|Recargo: {amount:.2f}"
        
        elif cmd_type == "CUSTOMER_RIF":
            state.customer_rif = params[0] if params else ""
            state.customer_rif = state.customer_rif.replace("*", "").strip()
            return "0|RIF registrado"
        
        elif cmd_type == "CUSTOMER_NAME":
            state.customer_name = params[0] if params else ""
            state.customer_name = state.customer_name.replace("*", "").strip()
            return "0|Nombre registrado"
        
        elif cmd_type == "CUSTOMER_ADDRESS":
            state.customer_address = params[0] if params else ""
            return "0|Direccion registrada"
        
        elif cmd_type == "CUSTOMER_PHONE":
            state.customer_phone = params[0] if params else ""
            return "0|Telefono registrado"
        
        elif cmd_type == "INVOICE_NUMBER":
            state.reference_invoice = params[0] if params else ""
            state.reference_invoice = state.reference_invoice.replace("*", "").strip()
            return "0|Nro factura referenciada"
        
        elif cmd_type == "INVOICE_DATE":
            state.reference_date = params[0] if params else ""
            state.reference_date = state.reference_date.replace("*", "").strip()
            return "0|Fecha factura referenciada"
        
        elif cmd_type == "FISCAL_SERIAL":
            state.reference_serial = params[0] if params else ""
            state.reference_serial = state.reference_serial.replace("*", "").strip()
            return "0|Serial fiscal registrado"
        
        elif cmd_type == "OPEN_CREDIT_NOTE":
            state.open_document("credit_note")
            return "0|Nota credito abierta"
        
        elif cmd_type == "OPEN_DEBIT_NOTE":
            state.open_document("debit_note")
            return "0|Nota debito abierta"
        
        # Status commands
        elif cmd_type == "S1":
            s1 = state.get_s1_data()
            return (
                f"0|{s1['machine_number']}|{s1['rif']}|"
                f"{s1['audit_counter']}|{s1['daily_closure']}|"
                f"{s1['last_invoice']}|{s1['last_credit_note']}|"
                f"{s1['last_debit_note']}|{s1['last_non_fiscal']}|"
                f"{s1['total_sales']:.2f}|{s1['current_datetime']}"
            )
        
        elif cmd_type == "S2":
            s2 = state.get_s2_data()
            return (
                f"{s2['condition']}|{s2['type_document']}|"
                f"{s2['quantity_articles']}|{s2['subtotal_bases']:.2f}|"
                f"{s2['subtotal_tax']:.2f}|{s2['amount_payable']:.2f}|"
                f"{s2['payments_made']}"
            )
        
        elif cmd_type == "S3":
            s3 = state.get_s3_data()
            return (
                f"{s3['tax1']:.2f}|{s3['tax2']:.2f}|{s3['tax3']:.2f}|"
                f"{s3['type_tax1']}|{s3['type_tax2']}|{s3['type_tax3']}"
            )
        
        elif cmd_type == "S4":
            payments = "|".join(f"{v:.2f}" for v in state.payment_totals.values())
            return f"0|{payments}|0.00"  # Last is donation
        
        elif cmd_type == "S5":
            s5 = state.get_s5_data()
            return (
                f"{s5['machine_number']}|{s5['rif']}|"
                f"{s5['audit_memory_number']}|{s5['audit_memory_total']:.2f}|"
                f"{s5['audit_memory_free']:.2f}|{s5['registered_documents']}"
            )
        
        elif cmd_type == "S8E":
            return "|".join(state.headers)
        
        elif cmd_type == "S8P":
            footers = [state.footers.get(f"footer{i}", "") for i in range(1, 9)]
            return "|".join(footers)
        
        # Report commands
        elif cmd_type in ("U0X", "REPORT_X"):
            x = state.generate_x_report()
            job = self._record_report(x, "X")
            return (
                f"0|Reporte X #{x['number']}|Ventas: {x['total_sales']:.2f}|"
                f"IVA: {x['total_tax']:.2f}|Impreso:{job['id']}"
            )
        
        elif cmd_type in ("U1X", "REPORT_X2"):
            x = state.generate_x_report()
            job = self._record_report(x, "X")
            return f"0|Reporte X2 #{x['number']}|Ventas: {x['total_sales']:.2f}|Impreso:{job['id']}"
        
        elif cmd_type in ("U0Z", "REPORT_Z"):
            z = state.generate_z_report()
            job = self._record_report(z, "Z")
            return (
                f"0|Reporte Z #{z['number']}|Ventas: {z['total_sales']:.2f}|"
                f"IVA: {z['total_tax']:.2f}|Impreso:{job['id']}"
            )
        
        elif cmd_type in ("U1Z", "REPORT_Z2"):
            z = state.generate_z_report()
            job = self._record_report(z, "Z")
            return f"0|Reporte Z2 #{z['number']}|Ventas: {z['total_sales']:.2f}|Impreso:{job['id']}"
        
        return "ERROR|0x50|Comando no implementado"
    
    def _handle_ixbatch(self, command: str, params: list) -> str:
        """Handle Hasar/Bixolon IxBatch @Command protocol"""
        state = self.state
        
        # Document opening commands
        if command == "@OpenFiscalReceipt":
            state.open_document("invoice")
            return "@Response|OK|0|Documento fiscal abierto"
        
        elif command == "@OpenCreditNote":
            state.open_document("credit_note")
            return "@Response|OK|0|Nota de credito abierta"
        
        elif command == "@OpenDebitNote":
            state.open_document("debit_note")
            return "@Response|OK|0|Nota de debito abierta"
        
        elif command == "@OpenNonFiscalDoc":
            state.open_document("non_fiscal")
            return "@Response|OK|0|Documento no fiscal abierto"
        
        elif command == "@CloseNonFiscalDoc":
            if state.document_open:
                state.close_document()
            return "@Response|OK|0|DNF cerrado"
        
        # PrintLineItem - the core command
        # @PrintLineItem|<desc>|<qty>|<price>|<tax_type>|<qualifier>
        # @PrintLine (alias used by test harnesses / other hosts):
        # @PrintLine|<desc>|<qty>|<price>|<tax_name>
        elif command in ("@PrintLineItem", "@PrintLine"):
            if not state.document_open:
                # Auto-open an invoice like the TFHKA side does
                state.open_document("invoice")
            if len(params) >= 3:
                desc = params[0]
                qty = float(params[1])
                price = float(params[2])
                tax_spec = params[3] if len(params) > 3 else "general"
                qualifier = params[4] if len(params) > 4 else "M"
                
                tax_name = self._resolve_tax_name(tax_spec)
                
                item = state.add_item(desc, qty, price, tax_name)
                return f"@Response|OK|0|{desc}|{qty:.3f}|{price:.2f}|{item['total']:.2f}"
            return "@Response|Error|2|Invalid params"
        
        elif command == "@RefundItem":
            if not state.document_open:
                return "@Response|Error|1|No document open"
            if len(params) >= 4:
                desc = params[0]
                qty = float(params[1])
                price = float(params[2])
                tax_name = self._resolve_tax_name(params[3])
                item = state.add_item(desc, qty, price, tax_name)
                return f"@Response|OK|0|NC {desc}|{qty:.3f}|{price:.2f}|{item['total']:.2f}"
            return "@Response|Error|2|Invalid params"
        
        # Customer data
        elif command in ("@CustomerData", "@SetCustomerData"):
            # @CustomerData|rif|nombre|direccion  (test harness format)
            # @SetCustomerData|rif|nombre         (classic IxBatch format)
            if len(params) >= 3:
                state.customer_rif = params[0]
                state.customer_name = params[1]
                state.customer_address = params[2]
            elif len(params) == 2:
                state.customer_rif = params[0]
                state.customer_name = params[1]
            elif len(params) == 1:
                state.customer_rif = params[0]
            return (f"@Response|OK|0|Cliente {state.customer_rif} "
                    f"{state.customer_name}".strip())
        
        elif command == "@SetCustomerInfo1":
            state.customer_name = params[0] if len(params) > 0 else ""
            return "@Response|OK|0|Nombre registrado"
        
        elif command == "@SetCustomerInfo2":
            state.customer_name_line2 = params[0] if len(params) > 0 else ""
            return "@Response|OK|0|Nombre linea 2 registrada"
        
        elif command == "@SetCustomerTIN":
            state.customer_rif = params[0] if len(params) > 0 else ""
            return "@Response|OK|0|RIF registrado"
        
        elif command == "@SetCustomerExtraData":
            return "@Response|OK|0|Datos extra registrados"
        
        # Payment commands
        elif command == "@Subtotal":
            return f"@Response|OK|0|Subtotal: {state.subtotal_bases:.2f}+IVA:{state.subtotal_tax:.2f}"
        
        elif command in ("@AddPayment", "@Cash"):
            # @AddPayment|<monto>|<metodo>  (test harness format)
            if len(params) >= 1:
                amount = float(params[0])
                method = (params[1] if len(params) > 1 else "cash").lower()
                method_map = {
                    "efectivo": "cash", "cash": "cash", "money": "cash",
                    "tarjeta": "card", "card": "card",
                    "transferencia": "transfer", "transfer": "transfer",
                    "credit": "credit", "credito": "credit",
                    "cheque": "check", "check": "check",
                }
                method = method_map.get(method, method)
                state.add_payment(amount, method)
                return f"@Response|OK|0|Pago: {amount:.2f}|Pendiente: {state.amount_payable:.2f}"
            return "@Response|Error|2|Invalid params"
        
        elif command == "@TotalTender":
            # @TotalTender|Texto|Monto|Calificador|MontoDescuento
            if len(params) >= 2:
                text = params[0]
                amount = float(params[1])
                qualifier = params[2] if len(params) > 2 else "T"
                discount = float(params[3]) if len(params) > 3 else 0.0
                if discount > 0:
                    state.total_discounts += discount
                    state.amount_payable -= discount
                state.add_payment(amount, "cash")
                change = max(0.0, state.amount_payable * -1)
                return f"@Response|OK|0|Pago: {amount:.2f}|Vuelto: {change:.2f}|{state.invoice_counter + 1:08d}"
            return "@Response|Error|2|Invalid params"
        
        elif command == "@DirectPayment":
            if len(params) >= 1:
                method = int(params[0])
                state.add_payment(state.amount_payable, f"pay_{method}")
                return "@Response|OK|0|Pago directo"
            return "@Response|Error|2|Invalid params"
        
        elif command == "@RefundClose":
            if len(params) >= 2:
                amount = float(params[0])
                method = int(params[1])
                state.close_document()
                return f"@Response|OK|0|Devolucion cerrada: {amount:.2f}"
            return "@Response|Error|2|Invalid params"
        
        # Document control
        elif command == "@Cancel":
            if state.document_open:
                state.close_document()
            return "@Response|OK|0|Cancelado"
        
        elif command == "@LastItemCancel":
            return "@Response|OK|0|Ultimo item cancelado"
        
        elif command == "@LastItemDiscount":
            if len(params) >= 2:
                amount = float(params[0])
                qualifier = params[1]
                return f"@Response|OK|0|Descuento: {amount:.2f}"
            return "@Response|Error|2|Invalid params"
        
        elif command in ("@Close", "@CloseFiscalReceipt"):
            if not state.document_open:
                return "@Response|OK|0|Cerrado"
            doc = state.close_document()
            if doc:
                job = self._record_receipt(doc)
                doc_name = {
                    "invoice": "Factura", "credit_note": "Nota de Credito",
                    "debit_note": "Nota de Debito",
                }.get(doc["type"], "Documento")
                return (f"@Response|OK|0|{doc_name} {doc['number']} "
                        f"cerrada|Total: {doc['total']:.2f}|Impreso:{job['id']}")
            return "@Response|OK|0|Cerrado"
        
        elif command == "@CloseCashReceipt":
            if state.document_open:
                doc = state.close_document()
                if doc:
                    self._record_receipt(doc)
            return "@Response|OK|0|DNF cerrado"
        
        # Reports
        elif command == "@PrintXReport":
            x = state.generate_x_report()
            job = self._record_report(x, "X")
            return f"@Response|OK|0|Reporte X #{x['number']}|Ventas: {x['total_sales']:.2f}|Impreso:{job['id']}"
        
        elif command == "@PrintZReport":
            z = state.generate_z_report()
            job = self._record_report(z, "Z")
            return f"@Response|OK|0|Reporte Z #{z['number']}|Ventas: {z['total_sales']:.2f}|Impreso:{job['id']}"
        
        elif command == "@DailyClose":
            if len(params) >= 1:
                close_type = params[0]
                z = state.generate_z_report()
                job = self._record_report(z, "Z")
                return f"@Response|OK|0|Cierre {close_type} #{z['number']}|Impreso:{job['id']}"
            return "@Response|Error|2|Invalid params"
        
        elif command == "@DailyCloseByDate":
            z = state.generate_z_report()
            job = self._record_report(z, "Z")
            return f"@Response|OK|0|Cierre por fecha #{z['number']}|Impreso:{job['id']}"
        
        elif command == "@DailyCloseByNumber":
            z = state.generate_z_report()
            job = self._record_report(z, "Z")
            return f"@Response|OK|0|Cierre por numero #{z['number']}|Impreso:{job['id']}"
        
        elif command == "@PrintAuditStatusReport":
            return "@Response|OK|0|Reporte de auditoria impreso"
        
        elif command == "@Reprint":
            return "@Response|OK|0|Reimpresion generada"
        
        elif command == "@ReprintByDate":
            return "@Response|OK|0|Reimpresion por fecha"
        
        elif command == "@ReprintByNumber":
            return "@Response|OK|0|Reimpresion por numero"
        
        # Text and comments
        elif command == "@PrintFiscalText":
            text = params[0] if params else ""
            return f"@Response|OK|0|Texto: {text}"
        
        elif command == "@PrintNonFiscalText":
            text = params[0] if params else ""
            return f"@Response|OK|0|No fiscal: {text}"
        
        elif command == "@PrintCashItem":
            return "@Response|OK|0|Movimiento caja"
        
        elif command == "@BarCode":
            return "@Response|OK|0|Codigo barras impreso"
        
        # Status
        elif command in ("@Status", "@StatusRequest"):
            status = state.get_status_code()
            error = state.get_error_code()
            doc_state = "ABIERTO" if state.document_open else "CERRADO"
            return (f"@Response|OK|0|Status: 0x{status:02X}|Error: 0x{error:02X}"
                    f"|Doc: {doc_state}|Ventas: {state.daily_sales:.2f}")
        
        elif command == "@StatusExtra":
            return "@Response|OK|0|Status extra OK"
        
        # Configuration
        elif command == "@ConfigureControllerByOne":
            return "@Response|OK|0|Configuracion OK"
        
        elif command == "@PrintConfigurationData":
            return "@Response|OK|0|Configuracion impresa"
        
        elif command == "@ProgramClerk":
            return "@Response|OK|0|Cajero programado"
        
        elif command == "@ProgramPaymentMedia":
            return "@Response|OK|0|Medio pago programado"
        
        elif command == "@ProgramSymbol":
            return "@Response|OK|0|Simbolo programado"
        
        elif command == "@ProgramTaxes":
            return "@Response|OK|0|Tasas programadas"
        
        elif command == "@SaveTaxes":
            return "@Response|OK|0|Tasas guardadas"
        
        elif command == "@SetDate":
            return "@Response|OK|0|Fecha establecida"
        
        elif command == "@SetTime":
            return "@Response|OK|0|Hora establecida"
        
        elif command == "@Login":
            return "@Response|OK|0|Logon OK"
        
        elif command == "@Logoff":
            return "@Response|OK|0|Logoff OK"
        
        elif command == "@TrainingMode":
            return "@Response|OK|0|Modo entrenamiento"
        
        elif command == "@OpenDrawer":
            drawer = params[0] if params else "1"
            return f"@Response|OK|0|Gaveta {drawer} abierta"
        
        elif command == "@PrintTest":
            return "@Response|OK|0|Test impreso"
        
        elif command == "@ResetPrinterBuffer":
            return "@Response|OK|0|Buffer reseteado"
        
        elif command == "@SendRawCommand":
            return "@Response|OK|0|Raw enviado"
        
        elif command == "@SetHeaderTrailer":
            return "@Response|OK|0|Header/trailer configurado"
        
        # Display
        elif command == "@DisplayCommercial":
            return "@Response|OK|0|Comercial mostrado"
        
        elif command == "@DisplayDateTime":
            return "@Response|OK|0|Fecha/hora mostrada"
        
        elif command == "@DisplayMessage":
            return "@Response|OK|0|Mensaje mostrado"
        
        elif command == "@ProgramCommercial":
            return "@Response|OK|0|Comercial programado"
        
        elif command == "@ProgramMessage":
            return "@Response|OK|0|Mensaje programado"
        
        # Check commands
        elif command == "@FormatCheck":
            return "@Response|OK|0|Cheque formateado"
        
        elif command == "@FormatEndorse":
            return "@Response|OK|0|Endoso formateado"
        
        elif command == "@ModeSlip":
            return "@Response|OK|0|Modo slip"
        
        elif command == "@ModeValidation":
            return "@Response|OK|0|Modo validacion"
        
        elif command == "@PrintEndorse":
            return "@Response|OK|0|Endoso impreso"
        
        elif command == "@PrintValidation":
            return "@Response|OK|0|Validacion impresa"
        
        elif command == "@ReadMICR":
            return "@Response|OK|0|MICR leido"
        
        return "@Response|Error|0x50|Comando desconocido"
    
    def _handle_item(self, raw: str, cmd_type: str, params: list) -> str:
        """Handle line item commands"""
        state = self.state
        
        if not state.document_open:
            # Auto-open invoice if not open
            state.open_document("invoice")
        
        if cmd_type == "ITEM":
            # Parse: prefix + qty(8.3) + price(10.2) + desc
            if len(raw) < 20:
                return "ERROR|0x50|Item format invalid"
            
            prefix = raw[0]
            tax_map = {' ': 'exempt', '!': 'general', '"': 'reduced', '#': 'additional'}
            tax_type = tax_map.get(prefix, 'general')
            
            try:
                qty_str = raw[1:9].strip()
                price_str = raw[9:19].strip()
                desc = raw[19:].strip()
                
                qty = float(qty_str)
                price = float(price_str)
                
                if not desc:
                    desc = "PRODUCTO"
                
                item = state.add_item(desc, qty, price, tax_type)
                return f"0|Item|{desc}|{qty:.3f}|{price:.2f}|{item['tax']:.2f}|{item['total']:.2f}"
            except ValueError:
                return "ERROR|0x50|Invalid qty/price"
        

        
        elif cmd_type == "ITEM_CREDIT":
            # Parse: d + tax_type + qty(8.3) + price(10.2) + desc
            if len(raw) < 21:
                return "ERROR|0x50|Credit note item format invalid"
            
            tax_type_idx = params[0] if params else 1
            tax_types = {0: 'exempt', 1: 'general', 2: 'reduced', 3: 'additional'}
            tax_type = tax_types.get(tax_type_idx, 'general')
            
            try:
                qty_str = raw[2:10].strip()
                price_str = raw[10:20].strip()
                desc = raw[20:].strip()
                
                qty = float(qty_str)
                price = float(price_str)
                
                if not desc:
                    desc = "PRODUCTO NC"
                
                item = state.add_item(desc, qty, price, tax_type)
                
                # Update credit note totals
                state.credit_note_totals[tax_type]["base"] += item["base"]
                state.credit_note_totals[tax_type]["tax"] += item["tax"]
                
                return f"0|NC Item|{desc}|{qty:.3f}|{price:.2f}|{item['tax']:.2f}|{item['total']:.2f}"
            except ValueError:
                return "ERROR|0x50|Invalid qty/price"
        
        elif cmd_type == "ITEM_DEBIT":
            # Parse: ` + tax_type + qty(8.3) + price(10.2) + desc
            if len(raw) < 21:
                return "ERROR|0x50|Debit note item format invalid"
            
            tax_type_idx = params[0] if params else 1
            tax_types = {0: 'exempt', 1: 'general', 2: 'reduced', 3: 'additional'}
            tax_type = tax_types.get(tax_type_idx, 'general')
            
            try:
                qty_str = raw[2:10].strip()
                price_str = raw[10:20].strip()
                desc = raw[20:].strip()
                
                qty = float(qty_str)
                price = float(price_str)
                
                if not desc:
                    desc = "PRODUCTO ND"
                
                item = state.add_item(desc, qty, price, tax_type)
                
                # Update debit note totals
                state.debit_note_totals[tax_type]["base"] += item["base"]
                state.debit_note_totals[tax_type]["tax"] += item["tax"]
                
                return f"0|ND Item|{desc}|{qty:.3f}|{price:.2f}|{item['tax']:.2f}|{item['total']:.2f}"
            except ValueError:
                return "ERROR|0x50|Invalid qty/price"
        
        return "ERROR|0x50|Unknown item type"


# Brand-specific subclasses

class TFHKASimulator(FiscalPrinterSimulator):
    """TFHKA (The Factory HKA) printer simulator"""
    
    def __init__(self, model: str = "TFHKA", state_path: str = None):
        super().__init__("TFHKA", model, state_path)
        self.state.serial_number = "MLTFHKA001"
        self.state.tax_rates = {"general": 16.0, "reduced": 8.0, "additional": 30.0}


class HasarSimulator(FiscalPrinterSimulator):
    """Hasar SMH/P-615F printer simulator"""
    
    def __init__(self, model: str = "SMH/P-615F", state_path: str = None):
        super().__init__("HASAR", model, state_path)
        self.state.serial_number = "MLHSR615F001"
        self.state.tax_rates = {"general": 16.0, "reduced": 8.0, "additional": 30.0}


class BixolonSimulator(FiscalPrinterSimulator):
    """Bixolon SRP-270 printer simulator"""
    
    def __init__(self, model: str = "SRP-270", state_path: str = None):
        super().__init__("BIXOLON", model, state_path)
        self.state.serial_number = "MLBLN270001"
        self.state.tax_rates = {"general": 16.0, "reduced": 8.0, "additional": 30.0}
        self.state.audit_memory_total = 2.0
        self.state.audit_memory_free = 1.8


class EpsonSimulator(FiscalPrinterSimulator):
    """Epson TM2000 printer simulator (STX/ETX binary protocol)"""
    
    def __init__(self, model: str = "TM2000", state_path: str = None):
        super().__init__("EPSON", model, state_path)
        self.state.serial_number = "MLSTM200001"
        self.state.tax_rates = {"general": 16.0, "reduced": 8.0, "additional": 30.0}
        self.state.audit_memory_total = 8.0
        self.state.audit_memory_free = 7.2
        self.sequence_number = 0x21
    
    def _format_response(self, response: str) -> str:
        """Epson wraps every response with status|error bytes"""
        status = self.state.get_status_code()
        error = self.state.get_error_code()
        return f"0x{status:02X}|0x{error:02X}|{response}"


# Factory
def create_simulator(brand: str, model: str = "",
                     state_path: str = None) -> FiscalPrinterSimulator:
    """Create a printer simulator by brand name"""
    brand_map = {
        "tfhka": TFHKASimulator,
        "hasar": HasarSimulator,
        "bixolon": BixolonSimulator,
        "epson": EpsonSimulator,
    }
    
    brand_lower = brand.lower()
    if brand_lower not in brand_map:
        raise ValueError(f"Unknown brand '{brand}'. Supported: {list(brand_map.keys())}")
    
    cls = brand_map[brand_lower]
    if model:
        return cls(model, state_path)
    return cls(state_path=state_path)
