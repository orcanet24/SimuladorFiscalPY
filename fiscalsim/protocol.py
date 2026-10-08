"""
Fiscal Printer Simulator - Protocol Constants and Parsing
Based on TFHKA, Hasar, Bixolon, and Epson TM2000 documentation
"""

# TFHKA Command Constants
class TFHKACommands:
    # Document control
    OPEN_INVOICE = ""  # Just send items
    OPEN_CREDIT_NOTE = "d1"
    OPEN_DEBIT_NOTE = "d2"
    OPEN_NON_FISCAL = "80$"
    PRINT_NON_FISCAL_TEXT = "80!"
    PRINT_NON_FISCAL_CONTENT = "80*"
    CLOSE_NON_FISCAL = "81"
    
    # Line items use prefix: ' ' (exempt), '!' (general), '"' (reduced), '#' (additional)
    TAX_EXEMPT = " "
    TAX_GENERAL = "!"
    TAX_REDUCED = '"'
    TAX_ADDITIONAL = "#"
    
    # Document control
    SUBTOTAL_PRINT = "3"
    SUBTOTAL_SILENT = "4"
    CLOSE_TOTALIZE = "101"
    OPEN_DRAWER = "0"
    
    # Reports
    REPORT_X = "U0X"
    REPORT_X2 = "U1X"
    REPORT_Z = "U0Z"
    REPORT_Z2 = "U1Z"
    
    # Status requests
    STATUS_S1 = "S1"
    STATUS_S2 = "S2"
    STATUS_S3 = "S3"
    STATUS_S4 = "S4"
    STATUS_S5 = "S5"
    STATUS_S8E = "S8E"
    STATUS_S8P = "S8P"
    
    # Payment
    PAGO = "100"
    PAGO_DESCRIPTION = "103"
    DESCUENTO = "700"
    RECARGO = "701"
    
    # Credit/Debit notes
    CREDIT_NOTE_ITEM_PREFIX = "d"
    DEBIT_NOTE_ITEM_PREFIX = "`"  # chr(96)
    
    # Tax type for credit/debit note items
    TAX_TYPE_EXEMPT = 0
    TAX_TYPE_GENERAL = 1
    TAX_TYPE_REDUCED = 2
    TAX_TYPE_ADDITIONAL = 3
    
    # Comments
    COMMENT = "@COMENTARIO"


# Hasar IxBatch @Command protocol
class HasarCommands:
    # IxBatch command format: @Command|param1|param2|...
    COMMAND_PREFIX = "@"
    
    # Document commands
    OPEN_FISCAL_RECEIPT = "@OpenFiscalReceipt"
    OPEN_CREDIT_NOTE = "@OpenCreditNote"
    OPEN_DEBIT_NOTE = "@OpenDebitNote"
    OPEN_NON_FISCAL = "@OpenNonFiscalDoc"
    
    # Item commands
    PRINT_ITEM = "@PrintLine"
    PRINT_DESCRIPTION = "@PrintDescription"
    PRINT_SUBTOTAL = "@Subtotal"
    
    # Payment
    PAYMENT = "@AddPayment"
    CASH = "@Cash"
    
    # Close
    CLOSE = "@Close"
    CLOSE_NON_FISCAL = "@CloseNonFiscalDoc"
    
    # Reports
    REPORT_X = "@PrintXReport"
    REPORT_Z = "@PrintZReport"
    REPORT_MEMORY = "@UploadReportMemory"
    
    # Status
    STATUS = "@Status"
    
    # Customer data
    CUSTOMER_DATA = "@CustomerData"
    
    # Comments
    COMMENT = "@Comment"
    PRINT_TEXT = "@PrintText"


# Status codes (TFHKA Anexo 1)
STATUS_CODES = {
    0x00: "Estado desconocido",
    0x01: "Modo prueba - en espera",
    0x02: "Modo prueba - emision fiscal",
    0x03: "Modo prueba - emision no fiscal",
    0x04: "Modo fiscal - en espera",
    0x05: "Modo fiscal - emision fiscal",
    0x06: "Modo fiscal - emision no fiscal",
    0x07: "Fiscal casi llena - en espera",
    0x08: "Fiscal casi llena - emision fiscal",
    0x09: "Fiscal casi llena - emision no fiscal",
    0x0A: "Memoria fiscal llena - en espera",
    0x0B: "Memoria fiscal llena - emision fiscal",
    0x0C: "Memoria fiscal llena - emision no fiscal",
}

# Error codes (TFHKA Anexo 2)
ERROR_CODES = {
    0x00: "Sin error",
    0x01: "Fin papel",
    0x02: "Error mecanico papel",
    0x03: "Fin papel + error mecanico",
    0x50: "Comando invalido",
    0x54: "Tasa invalida",
    0x58: "Sin directivas",
    0x5C: "Comando invalido",
    0x60: "Error fiscal",
    0x64: "Error memoria fiscal",
    0x6C: "Memoria fiscal llena",
    0x70: "Buffer completo - reiniciar",
    0x80: "Error comunicacion",
    0x89: "Sin respuesta",
    0x90: "Error LRC",
    0x91: "Error interno API",
    0x99: "Error apertura archivo",
}


def parse_ixbatch_command(data: str):
    """Parse an IxBatch command: @Command|param1|param2|..."""
    if not data.startswith("@"):
        return None, []
    
    parts = data.split("|")
    command = parts[0].strip()
    params = [p.strip() for p in parts[1:]] if len(parts) > 1 else []
    
    return command, params


def parse_tfhka_command(data: str):
    """Parse a TFHKA ASCII command"""
    data = data.strip()
    
    if not data:
        return None, []
    
    # Check for status commands
    status_cmds = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8E", "S8P"]
    if data in status_cmds:
        return data, []
    
    # Check for report commands
    report_cmds = ["U0X", "U1X", "U0Z", "U1Z"]
    if data in report_cmds:
        return data, []
    
    # Check for document control
    if data == "3":
        return "SUBTOTAL_PRINT", []
    elif data == "4":
        return "SUBTOTAL_SILENT", []
    elif data == "101":
        return "CLOSE_TOTALIZE", []
    elif data == "0":
        return "OPEN_DRAWER", []
    
    # Check for credit/debit note open commands (d1, d2 - exactly 2 chars)
    if data in ("d1", "d2"):
        return "OPEN_CREDIT_NOTE" if data == "d1" else "OPEN_DEBIT_NOTE", []
    
    # Check for credit/debit note item prefix (d + tax_type + qty + price + desc)
    if data.startswith("d") and len(data) > 2:
        tax_type = int(data[1]) if data[1].isdigit() else 1
        return "ITEM_CREDIT", [tax_type]
    
    if data.startswith("`") and len(data) > 2:
        tax_type = int(data[1]) if data[1].isdigit() else 1
        return "ITEM_DEBIT", [tax_type]
    
    # Check for comment
    if data.startswith("@COMENTARIO"):
        return "COMMENT", [data[len("@COMENTARIO"):].strip()]
    
    # Check for line items (prefix + qty + price + desc)
    if data and data[0] in [' ', '!', '"', '#']:
        prefix = data[0]
        tax_map = {' ': 0, '!': 1, '"': 2, '#': 3}
        return "ITEM", [tax_map.get(prefix, 1)]
    
    # Check for non-fiscal
    if data == "80$":
        return "OPEN_NON_FISCAL", []
    elif data == "81":
        return "CLOSE_NON_FISCAL", []
    elif data.startswith("80!"):
        return "PRINT_NON_FISCAL_TEXT", [data[3:]]
    elif data.startswith("80*"):
        return "PRINT_NON_FISCAL_CONTENT", [data[3:]]
    
    # Payment commands
    if data.startswith("100"):
        return "PAYMENT", [data[3:]]
    elif data.startswith("103"):
        return "PAYMENT_DESC", [data[3:]]
    elif data.startswith("700"):
        return "DISCOUNT", [data[3:]]
    elif data.startswith("701"):
        return "SURCHARGE", [data[3:]]
    
    # Customer data (iR*, iS*, i01, i02, iF*, iD*, iI*)
    if data.startswith("iR*"):
        return "CUSTOMER_RIF", [data[3:]]
    elif data.startswith("iS*"):
        return "CUSTOMER_NAME", [data[3:]]
    elif data.startswith("i01"):
        return "CUSTOMER_ADDRESS", [data[3:]]
    elif data.startswith("i02"):
        return "CUSTOMER_PHONE", [data[3:]]
    elif data.startswith("iF*"):
        return "INVOICE_NUMBER", [data[3:]]
    elif data.startswith("iD*"):
        return "INVOICE_DATE", [data[3:]]
    elif data.startswith("iI*"):
        return "FISCAL_SERIAL", [data[3:]]
    
    # Credit note open
    if data == "d1":
        return "OPEN_CREDIT_NOTE", []
    elif data == "d2":
        return "OPEN_DEBIT_NOTE", []
    
    return "UNKNOWN", [data]


def get_status_byte(mode="fiscal", state="waiting", memory="ok"):
    """Get status byte based on printer state"""
    if mode == "test":
        if state == "waiting":
            return 0x01
        elif state == "fiscal":
            return 0x02
        elif state == "non_fiscal":
            return 0x03
    else:  # fiscal mode
        if memory == "ok":
            if state == "waiting":
                return 0x04
            elif state == "fiscal":
                return 0x05
            elif state == "non_fiscal":
                return 0x06
        elif memory == "almost_full":
            if state == "waiting":
                return 0x07
            elif state == "fiscal":
                return 0x08
            elif state == "non_fiscal":
                return 0x09
        elif memory == "full":
            if state == "waiting":
                return 0x0A
            elif state == "fiscal":
                return 0x0B
            elif state == "non_fiscal":
                return 0x0C
    return 0x04  # Default: fiscal mode, waiting


def format_line_item(prefix: str, qty: float, price: float, description: str) -> str:
    """Format a line item: Prefix(1) + Qty(8.3) + Price(10.2) + Desc"""
    qty_str = f"{qty:8.3f}"
    price_str = f"{price:10.2f}"
    return f"{prefix}{qty_str}{price_str}{description}"


def format_credit_note_item(tax_type: int, qty: float, price: float, description: str) -> str:
    """Format credit note item: d + tax_type + qty(8.3) + price(10.2) + desc"""
    qty_str = f"{qty:8.3f}"
    price_str = f"{price:10.2f}"
    return f"d{tax_type}{qty_str}{price_str}{description}"


def format_debit_note_item(tax_type: int, qty: float, price: float, description: str) -> str:
    """Format debit note item: ` + tax_type + qty(8.3) + price(10.2) + desc"""
    qty_str = f"{qty:8.3f}"
    price_str = f"{price:10.2f}"
    return f"`{tax_type}{qty_str}{price_str}{description}"


def line_item_prefix(tax_rate: float) -> str:
    """Get prefix character for tax rate"""
    if tax_rate == 0:
        return " "
    elif tax_rate < 12:
        return '"'
    elif tax_rate >= 16:
        return "#"
    else:
        return "!"
