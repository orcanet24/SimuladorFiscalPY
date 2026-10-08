#!/usr/bin/env python3
"""
populate_database.py - Populates the fiscal printer docs database from markdown files.
Scans C:/c/drivers/*/doc/ directories for documentation.
Currently processes: HasarVE (hasar.md)
"""

import sqlite3
import os
import re

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs.db")
DOC_BASE = "C:/c/drivers"


def insert_model(conn, brand, model, identifier_string, dll_name, protocol_type, description=""):
    """Insert a printer model and return its ID."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO printer_models (brand, model, identifier_string, dll_name, protocol_type, description)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (brand, model, identifier_string, dll_name, protocol_type, description))
    cursor.execute("""
        SELECT id FROM printer_models WHERE brand = ? AND model = ?
    """, (brand, model))
    return cursor.fetchone()[0]


def insert_command(conn, model_id, cmd_name, syntax, description, param_count, category=""):
    """Insert a command and return its ID."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO commands (model_id, cmd_name, syntax, description, param_count, category)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (model_id, cmd_name, syntax, description, param_count, category))
    cursor.execute("""
        SELECT id FROM commands WHERE model_id = ? AND cmd_name = ?
    """, (model_id, cmd_name))
    return cursor.fetchone()[0]


def insert_param(conn, command_id, param_name, param_type, required, description, param_order):
    """Insert a command parameter."""
    conn.execute("""
        INSERT INTO command_parameters (command_id, param_name, param_type, required, description, param_order)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (command_id, param_name, param_type, required, description, param_order))


def insert_status_code(conn, model_id, code_hex, code_bit, description, is_error, status_type):
    """Insert a status code."""
    conn.execute("""
        INSERT INTO status_codes (model_id, code_hex, code_bit, description, is_error, status_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (model_id, code_hex, code_bit, description, is_error, status_type))


def insert_response_field(conn, model_id, cmd_name, field_name, field_type, field_order, description):
    """Insert a response format field."""
    conn.execute("""
        INSERT INTO response_formats (model_id, cmd_name, field_name, field_type, field_order, description)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (model_id, cmd_name, field_name, field_type, field_order, description))


def populate_hasar(conn):
    """Populate all Hasar VE printer data."""
    model_id = insert_model(
        conn,
        brand="Hasar",
        model="SMH/PT-100FVE/SMH/PT-250FVE",
        identifier_string="H100/H250",
        dll_name="H25032.DLL",
        protocol_type="IxBatch",
        description="Impresoras fiscales HASAR SMH/PT-100FVE y SMH/PT-250FVE. Cumplen con Providencias 591 y 592 del SENIAT."
    )

    # ---- STATUS CODES: Printer status (IF_ERROR1) ----
    printer_status = [
        ("0x0001", 1, "No se Usa", 0),
        ("0x0002", 2, "No se Usa", 0),
        ("0x0004", 3, "Error/falla de impresora.", 1),
        ("0x0008", 4, "Impresora fuera de línea.", 1),
        ("0x0010", 5, "No utilizado", 0),
        ("0x0020", 6, "No utilizado", 0),
        ("0x0040", 7, "Buffer de impresora lleno.", 1),
        ("0x0080", 8, "Buffer de impresora vacío.", 0),
        ("0x0100", 9, "Tapa de impresora abierta.", 1),
        ("0x0200", 10, "Siempre 0.", 0),
        ("0x0400", 11, "Siempre 0.", 0),
        ("0x0800", 12, "Siempre 0.", 0),
        ("0x1000", 13, "Siempre 0.", 0),
        ("0x2000", 14, "Siempre 0.", 0),
        ("0x4000", 15, "Impresora sin papel para ser impreso.", 1),
        ("0x8000", 16, "OR lógico de los bits { 1 - 7} y 15", 1),
    ]
    for code_hex, code_bit, desc, is_err in printer_status:
        insert_status_code(conn, model_id, code_hex, code_bit, desc, is_err, "printer")

    # ---- STATUS CODES: Fiscal controller status (IF_ERROR2) ----
    fiscal_status = [
        ("0x0001", 1, "Error en chequeo de memoria fiscal.", 1),
        ("0x0002", 2, "Error en chequeo de memoria de trabajo", 1),
        ("0x0004", 3, "No utilizado", 0),
        ("0x0008", 4, "Comando no reconocido.", 1),
        ("0x0010", 5, "Campo de datos Inválido.", 1),
        ("0x0020", 6, "Comando no válido para estado fiscal.", 1),
        ("0x0040", 7, "Desbordamiento de totales", 1),
        ("0x0080", 8, "Memoria fiscal llena, bloqueada o dada de baja", 1),
        ("0x0100", 9, "Memoria fiscal casi llena", 1),
        ("0x0200", 10, "Terminal fiscal certificada", 0),
        ("0x0400", 11, "Terminal fiscal fiscalizada", 0),
        ("0x0800", 12, "Es necesario hacer un cierre de la jornada fiscal / Max items en factura", 1),
        ("0x1000", 13, "Documento fiscal abierto.", 0),
        ("0x2000", 14, "Documento abierto", 0),
        ("0x4000", 15, "Sin uso, siempre en 0", 0),
        ("0x8000", 16, "OR lógico de los bits { 1 - 9 } y 12", 1),
    ]
    for code_hex, code_bit, desc, is_err in fiscal_status:
        insert_status_code(conn, model_id, code_hex, code_bit, desc, is_err, "fiscal")

    # ---- COMMANDS ----
    # Format: (cmd_name, syntax, description, param_count, category)
    commands_data = [
        # Fiscal Receipt commands
        ("OpenFiscalReceipt", "@OpenFiscalReceipt|Nombre|RIF|NroCompOrig|NroRegistro|Fecha|Hora|TipoDoc",
         "Abrir comprobante fiscal (Factura, Nota de Débito, Nota de Crédito)", 7, "fiscal_receipt"),
        ("PrintLineItem", "@PrintLineItem|Descripcion|Cantidad|PrecioUnitario|TasaIVA|Calificador",
         "Imprimir ítem de línea en comprobante fiscal", 5, "fiscal_receipt"),
        ("PrintFiscalText", "@PrintFiscalText|Texto",
         "Imprimir texto fiscal dentro de un comprobante fiscal", 1, "fiscal_receipt"),
        ("Subtotal", "@Subtotal",
         "Consultar subtotal del comprobante fiscal", 0, "fiscal_receipt"),
        ("TotalTender", "@TotalTender|Texto|Monto|Calificador|MontoDescuento",
         "Pago/Cancelación/Descuento en documentos fiscales", 4, "fiscal_receipt"),
        ("CloseFiscalReceipt", "@CloseFiscalReceipt|Copia",
         "Cerrar comprobante fiscal", 1, "fiscal_receipt"),
        ("Cancel", "@Cancel",
         "Cancelar comprobante fiscal abierto", 0, "fiscal_receipt"),
        ("SetBarCode", "@SetBarCode|Tipo|Dato|Protocolo",
         "Configurar código de barras para el comprobante", 3, "fiscal_receipt"),

        # Non-Fiscal Receipt commands
        ("OpenNonFiscalReceipt", "@OpenNonFiscalReceipt",
         "Abrir comprobante no fiscal", 0, "non_fiscal"),
        ("PrintNonFiscalText", "@PrintNonFiscalText|Texto",
         "Imprimir texto no fiscal", 1, "non_fiscal"),
        ("CloseNonFiscalReceipt", "@CloseNonFiscalReceipt",
         "Cerrar comprobante no fiscal", 0, "non_fiscal"),

        # Diagnostic & Status commands
        ("StatusExtra", "@StatusExtra",
         "Consultar estado extendido del controlador fiscal", 0, "diagnostic"),
        ("Status_IF", "@Status_IF|Tipo",
         "Consultar estado del controlador fiscal o impresora", 1, "diagnostic"),
        ("Status", "@Status",
         "Consultar estado del controlador fiscal", 0, "diagnostic"),
        ("GetPrinterVersion", "@GetPrinterVersion",
         "Consultar versión de la impresora fiscal", 0, "diagnostic"),
        ("GetSerial", "@GetSerial",
         "Consultar número de serie de la impresora fiscal", 0, "diagnostic"),
        ("GetInitData", "@GetInitData",
         "Consultar datos de inicialización de la memoria EPROM", 0, "diagnostic"),
        ("GetConfigCFData", "@GetConfigCFData",
         "Consultar configuración del controlador fiscal", 0, "diagnostic"),
        ("GetWorkingMemory", "@GetWorkingMemory",
         "Consultar memoria de trabajo", 0, "diagnostic"),

        # Fiscal Close commands
        ("DailyClose", "@DailyClose|Tipo",
         "Efectuar cierre de jornada fiscal (Z o X)", 1, "fiscal_close"),
        ("DailyCloseByDate", "@DailyCloseByDate|FechaDesde|FechaHasta|Tipo",
         "Efectuar cierre de jornada fiscal por rango de fechas", 3, "fiscal_close"),
        ("DailyCloseByNumber", "@DailyCloseByNumber|NumeroDesde|NumeroHasta|Tipo",
         "Efectuar cierre de jornada fiscal por rango de números", 3, "fiscal_close"),
        ("GetDailyReport", "@GetDailyReport|TipoReporte|TipoSalida",
         "Obtener reporte diario", 2, "fiscal_close"),

        # Configuration commands
        ("GetIVARates", "@GetIVARates",
         "Consultar tasas de IVA configuradas", 0, "config"),
        ("SetIVARates", "@SetIVARates|TasaStandard|TasaReducida|TasaAumentada|Fecha",
         "Configurar tasas de IVA", 4, "config"),
        ("SetDateTime", "@SetDateTime|Fecha|Hora",
         "Programar fecha y hora", 2, "config"),
        ("GetDateTime", "@GetDateTime",
         "Consultar fecha y hora", 0, "config"),
        ("SetHeader", "@SetHeader|NroLinea|Texto",
         "Programar línea de encabezamiento", 2, "config"),
        ("SetTrailer", "@SetTrailer|NroLinea|Texto",
         "Programar línea de cola", 2, "config"),
        ("GetHeader", "@GetHeader|NroLinea",
         "Consultar línea de encabezamiento", 1, "config"),
        ("GetTrailer", "@GetTrailer|NroLinea",
         "Consultar línea de cola", 1, "config"),
        ("SetFantasy", "@SetFantasy|Texto",
         "Configurar nombre de fantasía", 1, "config"),
        ("SetFiscalAddress", "@SetFiscalAddress|NroLinea|Texto",
         "Programar línea de domicilio fiscal", 2, "config"),
        ("GetFiscalAddress", "@GetFiscalAddress|NroLinea",
         "Consultar línea de domicilio fiscal", 1, "config"),
        ("SetCustExtraData", "@SetCustExtraData|NroLinea|Texto",
         "Programar datos adicionales del comprador", 2, "config"),
        ("GetCustExtraData", "@GetCustExtraData|NroLinea",
         "Consultar datos adicionales del comprador", 1, "config"),

        # Logo commands
        ("ResetLogoData", "@ResetLogoData",
         "Resetear logotipo de usuario", 0, "logo"),
        ("StoreLogoData", "@StoreLogoData|TipoInfo|Datos",
         "Cargar logotipo de usuario (BMP monocromo 128x576)", 2, "logo"),

        # Printer control commands
        ("FeedReceipt", "@FeedReceipt|Lineas",
         "Avanzar papel del comprobante", 1, "printer_control"),
        ("CutPaper", "@CutPaper|Tipo",
         "Cortar papel", 1, "printer_control"),
        ("OpenDrawer1", "@OpenDrawer1",
         "Abrir gaveta 1 de dinero", 0, "printer_control"),
        ("OpenDrawer2", "@OpenDrawer2",
         "Abrir gaveta 2 de dinero", 0, "printer_control"),
        ("OpenDrawer", "@OpenDrawer",
         "Abrir gaveta de dinero", 0, "printer_control"),

        # Audit commands
        ("GetAuditFirstBlock", "@GetAuditFirstBlock",
         "Obtener primer bloque de auditoría", 0, "audit"),
        ("GetAuditNextBlock", "@GetAuditNextBlock",
         "Obtener siguiente bloque de auditoría", 0, "audit"),
        ("GetAuditRangeZNum", "@GetAuditRangeZNum",
         "Obtener rango de números Z de auditoría", 0, "audit"),
        ("GetAuditSeqNum", "@GetAuditSeqNum",
         "Obtener número de secuencia de auditoría", 0, "audit"),

        # Crypto commands
        ("GetPublicKey", "@GetPublicKey",
         "Obtener clave pública", 0, "crypto"),
    ]

    # Insert commands
    for cmd_name, syntax, desc, param_count, category in commands_data:
        insert_command(conn, model_id, cmd_name, syntax, desc, param_count, category)

    # ---- COMMAND PARAMETERS ----
    # Parameters for each command (from hasar.md documentation)
    params_data = {
        "OpenFiscalReceipt": [
            ("strVar1", "STRING", 1, "Nombre o Razón Social del comprador (max 125 bytes)", 1),
            ("strVar2", "STRING", 1, "Número de Registro de Información Fiscal (RIF) / Documento (CI) del comprador (max 30 bytes)", 2),
            ("strVar3", "STRING", 0, "Número del comprobante original (max 24 bytes)", 3),
            ("strVar4", "STRING", 0, "Número de registro de la impresora fiscal que emitió el comprobante original (max 22 bytes)", 4),
            ("strVar5", "STRING", 0, "Fecha del comprobante original (formato AAMMDD) (max 6 bytes)", 5),
            ("strVar6", "STRING", 0, "Hora del comprobante original (formato HHMMSS) (max 6 bytes)", 6),
            ("byVar7", "BYTE", 1, "Tipo de documento {ABD}: A=Factura, B=Nota de Débito, D=Nota de Crédito", 7),
        ],
        "PrintLineItem": [
            ("strVar1", "STRING", 1, "Texto descripción del item (max 20 bytes)", 1),
            ("dblVar2", "DOUBLE", 1, "Cantidad (nnnnnn.nnn)", 2),
            ("dblVar3", "DOUBLE", 1, "Precio unitario (nnnnnnnnn.nn)", 3),
            ("dblVar4", "DOUBLE", 1, "Tasa de IVA (nn.nn)", 4),
            ("byVar5", "BYTE", 1, "Calificador de la operación {Mm}: M=Suma monto, m=Resta monto", 5),
        ],
        "PrintFiscalText": [
            ("strVar1", "STRING", 1, "Texto fiscal a imprimir (max 46 bytes)", 1),
        ],
        "TotalTender": [
            ("strVar1", "STRING", 1, "Texto de descripción (max 20 bytes)", 1),
            ("dblVar2", "DOUBLE", 1, "Monto pagado (nnnnnnnnn.nn)", 2),
            ("byVar3", "BYTE", 1, "Calificador de operación {Tt}: T=Pago, t=Descuento", 3),
            ("dblVar4", "DOUBLE", 0, "Monto de descuento (nnnnnnnnn.nn)", 4),
        ],
        "CloseFiscalReceipt": [
            ("byVar1", "BYTE", 1, "Copia: N=Original, S=Copia", 1),
        ],
        "SetBarCode": [
            ("nVar1", "INT", 1, "Tipo de código de barras", 1),
            ("strVar2", "STRING", 1, "Dato del código de barras", 2),
            ("byVar3", "BYTE", 1, "Protocolo {Pp}", 3),
        ],
        "Cancel": [],
        "OpenNonFiscalReceipt": [],
        "PrintNonFiscalText": [
            ("strVar1", "STRING", 1, "Texto no fiscal a imprimir", 1),
        ],
        "CloseNonFiscalReceipt": [],
        "StatusExtra": [],
        "Status_IF": [
            ("strVar1", "STRING", 1, "Tipo de estado a consultar: N=Normal, E=Extendido", 1),
        ],
        "Status": [],
        "GetPrinterVersion": [],
        "GetSerial": [],
        "GetInitData": [],
        "GetConfigCFData": [],
        "GetWorkingMemory": [],
        "DailyClose": [
            ("strVar1", "STRING", 1, "Tipo de cierre: Z=Cierre Z (cierre fiscal), X=Cierre X (reporte sin cierre)", 1),
        ],
        "DailyCloseByDate": [
            ("strVar1", "STRING", 1, "Fecha desde (formato AAMMDD)", 1),
            ("strVar2", "STRING", 1, "Fecha hasta (formato AAMMDD)", 2),
            ("byVar3", "BYTE", 1, "Tipo: D=Reporte por fecha", 3),
        ],
        "DailyCloseByNumber": [
            ("nVar1", "INT", 1, "Número desde", 1),
            ("nVar2", "INT", 1, "Número hasta", 2),
            ("byVar3", "BYTE", 1, "Tipo: P=Reporte por número", 3),
        ],
        "GetDailyReport": [
            ("nVar1", "INT", 1, "Tipo de reporte", 1),
            ("strVar2", "STRING", 1, "Tipo de salida: Z, X", 2),
        ],
        "GetIVARates": [],
        "SetIVARates": [
            ("dblVar1", "DOUBLE", 1, "Tasa estándar de IVA", 1),
            ("dblVar2", "DOUBLE", 1, "Tasa reducida de IVA", 2),
            ("dblVar3", "DOUBLE", 1, "Tasa aumentada de IVA", 3),
            ("nVar4", "INT", 1, "Fecha de entrada en vigencia (AAAAMMDD)", 4),
        ],
        "SetDateTime": [
            ("strVar1", "STRING", 1, "Fecha (formato AAMMDD)", 1),
            ("strVar2", "STRING", 1, "Hora (formato HHMMSS)", 2),
        ],
        "GetDateTime": [],
        "SetHeader": [
            ("nVar1", "INT", 1, "Número de línea de encabezamiento", 1),
            ("strVar2", "STRING", 1, "Texto de encabezamiento (max 46 caracteres)", 2),
        ],
        "SetTrailer": [
            ("nVar1", "INT", 1, "Número de línea de cola", 1),
            ("strVar2", "STRING", 1, "Texto de cola (max 46 caracteres)", 2),
        ],
        "GetHeader": [
            ("nVar1", "INT", 1, "Número de línea de encabezamiento a consultar", 1),
        ],
        "GetTrailer": [
            ("nVar1", "INT", 1, "Número de línea de cola a consultar", 1),
        ],
        "SetFantasy": [
            ("strVar1", "STRING", 1, "Texto de nombre de fantasía", 1),
        ],
        "SetFiscalAddress": [
            ("nVar1", "INT", 1, "Número de línea de domicilio fiscal", 1),
            ("strVar2", "STRING", 1, "Texto de domicilio fiscal", 2),
        ],
        "GetFiscalAddress": [
            ("nVar1", "INT", 1, "Número de línea de domicilio fiscal a consultar", 1),
        ],
        "SetCustExtraData": [
            ("nVar1", "INT", 1, "Número de línea de datos adicionales (1-5, 0=borrar)", 1),
            ("strVar2", "STRING", 1, "Texto de hasta 46 caracteres", 2),
        ],
        "GetCustExtraData": [
            ("nVar1", "INT", 1, "Número de línea de datos adicionales a consultar (1-5)", 1),
        ],
        "ResetLogoData": [],
        "StoreLogoData": [
            ("byVar1", "BYTE", 1, "Tipo de información {ICF}: I=Inicia, C=Continúa, F=Finaliza", 1),
            ("strVar2", "STRING", 1, "Datos (nro de caracteres en cantidad par, max 128 bytes)", 2),
        ],
        "FeedReceipt": [
            ("nVar1", "INT", 1, "Número de líneas a avanzar", 1),
        ],
        "CutPaper": [
            ("strVar1", "STRING", 1, "Tipo de corte", 1),
        ],
        "OpenDrawer1": [],
        "OpenDrawer2": [],
        "OpenDrawer": [],
        "GetAuditFirstBlock": [],
        "GetAuditNextBlock": [],
        "GetAuditRangeZNum": [],
        "GetAuditSeqNum": [],
        "GetPublicKey": [],
    }

    for cmd_name, params in params_data.items():
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM commands WHERE model_id = ? AND cmd_name = ?", (model_id, cmd_name))
        row = cursor.fetchone()
        if row:
            cmd_id = row[0]
            for param in params:
                insert_param(conn, cmd_id, *param)

    # ---- RESPONSE FORMATS ----
    # Response fields for key commands
    response_data = {
        "OpenFiscalReceipt": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal en formato hexadecimal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal en formato hexadecimal"),
        ],
        "PrintLineItem": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal en formato hexadecimal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal en formato hexadecimal"),
            ("Cantidad de operaciones de venta / anulación realizadas", "INT", 3, "Contador de operaciones de venta o anulación"),
        ],
        "Subtotal": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
            ("Campo reservado", "STRING", 3, "Reservado"),
            ("Campo reservado", "STRING", 4, "Reservado"),
            ("Monto venta exento", "DOUBLE", 5, "Monto de venta exento"),
            ("Monto venta base imponible standard", "DOUBLE", 6, "Monto de venta base imponible standard"),
            ("Tasa imponible standard", "DOUBLE", 7, "Tasa de IVA standard"),
            ("Monto impuesto base imponible standard", "DOUBLE", 8, "Monto del impuesto base imponible standard"),
            ("Monto venta base imponible reducida", "DOUBLE", 9, "Monto de venta base imponible reducida"),
            ("Tasa imponible reducida", "DOUBLE", 10, "Tasa de IVA reducida"),
            ("Monto impuesto base imponible reducida", "DOUBLE", 11, "Monto del impuesto base imponible reducida"),
            ("Monto venta base imponible aumentada", "DOUBLE", 12, "Monto de venta base imponible aumentada"),
            ("Tasa imponible aumentada", "DOUBLE", 13, "Tasa de IVA aumentada"),
            ("Monto impuesto base imponible aumentada", "DOUBLE", 14, "Monto del impuesto base imponible aumentada"),
        ],
        "TotalTender": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
            ("Vuelto", "DOUBLE", 3, "Vuelto o cambio devuelto al cliente"),
            ("Comprobante fiscal", "STRING", 4, "Número de comprobante fiscal emitido"),
        ],
        "CloseFiscalReceipt": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
            ("Número de comprobante fiscal", "INT", 3, "Número de comprobante fiscal emitido"),
        ],
        "DailyClose": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
        ],
        "StatusExtra": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
            ("Status auxiliar", "HEX", 3, "Estado auxiliar del parser del controlador fiscal"),
            ("Status documento", "HEX", 4, "Estado del documento actual"),
            ("Última Factura emitida", "INT", 5, "Número de la última factura emitida"),
            ("Última Nota de Crédito emitida", "INT", 6, "Número de la última nota de crédito emitida"),
            ("Última Nota de Débito emitida", "INT", 7, "Número de la última nota de débito emitida"),
            ("Fecha última Z", "STRING", 8, "Fecha del último cierre Z (AAMMDD)"),
            ("Hora última Z", "STRING", 9, "Hora del último cierre Z (HHMMSS)"),
            ("Cantidad de Z emitidas", "INT", 10, "Cantidad de cierres Z emitidos"),
        ],
        "GetDateTime": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
            ("Fecha", "STRING", 3, "Fecha actual (AAMMDD)"),
            ("Hora", "STRING", 4, "Hora actual (HHMMSS)"),
        ],
        "GetSerial": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
            ("Número de serie", "STRING", 3, "Número de serie de la impresora fiscal"),
        ],
        "GetPrinterVersion": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
            ("Modelo", "STRING", 3, "Modelo de la impresora"),
            ("Versión de firmware", "STRING", 4, "Versión del firmware"),
        ],
        "GetHeader": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
            ("Texto de encabezamiento", "STRING", 3, "Texto de encabezamiento almacenado"),
        ],
        "GetTrailer": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
            ("Texto de cola", "STRING", 3, "Texto de cola almacenado"),
        ],
        "GetCustExtraData": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
            ("Texto de datos adicionales", "STRING", 3, "Texto de datos adicionales almacenado (hasta 46 caracteres)"),
        ],
        "OpenDrawer1": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
        ],
        "OpenDrawer2": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
        ],
        "Cancel": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
        ],
        "CutPaper": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
        ],
        "FeedReceipt": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
        ],
        "GetIVARates": [
            ("Status de la impresora", "HEX", 1, "Estado de la impresora fiscal"),
            ("Status del controlador fiscal", "HEX", 2, "Estado del controlador fiscal"),
            ("Tasa standard", "DOUBLE", 3, "Tasa de IVA standard"),
            ("Tasa reducida", "DOUBLE", 4, "Tasa de IVA reducida"),
            ("Tasa aumentada", "DOUBLE", 5, "Tasa de IVA aumentada"),
        ],
    }

    for cmd_name, fields in response_data.items():
        for field_name, field_type, field_order, desc in fields:
            insert_response_field(conn, model_id, cmd_name, field_name, field_type, field_order, desc)

    print(f"Hasar data populated (model_id={model_id})")


def populate_from_markdown(conn, md_path, brand, model, identifier_string, dll_name, protocol_type, description=""):
    """
    Generic parser to extract command data from markdown files.
    This can be extended for other brands as needed.
    """
    if not os.path.exists(md_path):
        print(f"Warning: Documentation file not found: {md_path}")
        return

    model_id = insert_model(conn, brand, model, identifier_string, dll_name, protocol_type, description)

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Basic command extraction pattern: @CommandName|param1|param2|...
    cmd_pattern = re.compile(r'^@([A-Z][a-zA-Z]+)\|.*$', re.MULTILINE)
    for match in cmd_pattern.finditer(content):
        cmd_name = match.group(1)
        if cmd_name == "COMANDO":
            continue
        syntax = match.group(0)
        # Count params (rough estimate from pipe count)
        param_count = syntax.count("|")
        description = f"Comando {cmd_name} para impresoras {brand}"
        insert_command(conn, model_id, cmd_name, syntax, description, param_count, "")

    print(f"Generic markdown data populated for {brand} {model} (model_id={model_id})")


def scan_and_populate(conn):
    """Scan C:/c/drivers/*/doc/ directories and populate database."""
    if not os.path.exists(DOC_BASE):
        print(f"Warning: Doc base directory not found: {DOC_BASE}")
        return

    for brand_dir in os.listdir(DOC_BASE):
        brand_path = os.path.join(DOC_BASE, brand_dir)
        if not os.path.isdir(brand_path):
            continue

        doc_dir = os.path.join(brand_path, "doc")
        if not os.path.isdir(doc_dir):
            continue

        print(f"\nScanning documentation: {doc_dir}")
        for md_file in os.listdir(doc_dir):
            if md_file.endswith((".md", ".txt")):
                md_path = os.path.join(doc_dir, md_file)
                print(f"  Found: {md_path}")

                # Route to specific parsers based on brand
                if "Hasar" in brand_dir:
                    populate_hasar(conn)
                elif "Epson" in brand_dir:
                    # Use generic parser for now
                    populate_from_markdown(
                        conn, md_path,
                        brand="Epson",
                        model="TM-2032",
                        identifier_string="TM20",
                        dll_name="TM2032.DLL",
                        protocol_type="IxBatch",
                        description="Impresora fiscal Epson para Venezuela"
                    )
                elif "Bixolon" in brand_dir:
                    populate_from_markdown(
                        conn, md_path,
                        brand="Bixolon",
                        model="SPK-S300",
                        identifier_string="BIX",
                        dll_name="Spark32.DLL",
                        protocol_type="IxBatch",
                        description="Impresora fiscal Bixolon para Venezuela"
                    )


def main():
    """Main entry point: create and populate the database."""
    # Step 1: Create database
    from create_database import create_database
    create_database()

    # Step 2: Populate
    conn = sqlite3.connect(DB_PATH)

    # Populate Hasar (detailed data from known documentation)
    populate_hasar(conn)
    conn.commit()

    # Scan other driver directories for additional docs (skip Hasar - already done)
    # ... (rest of scan logic below)
    if os.path.exists(DOC_BASE):
        for brand_dir in os.listdir(DOC_BASE):
            brand_path = os.path.join(DOC_BASE, brand_dir)
            if not os.path.isdir(brand_path):
                continue
            if "Hasar" in brand_dir:
                continue  # Already populated

            doc_dir = os.path.join(brand_path, "doc")
            if not os.path.isdir(doc_dir):
                continue

            print(f"\nScanning documentation: {doc_dir}")
            for md_file in os.listdir(doc_dir):
                if md_file.endswith((".md", ".txt")):
                    md_path = os.path.join(doc_dir, md_file)
                    print(f"  Found: {md_path}")

                    if "Epson" in brand_dir:
                        populate_from_markdown(
                            conn, md_path,
                            brand="Epson",
                            model="TM-2032",
                            identifier_string="TM20",
                            dll_name="TM2032.DLL",
                            protocol_type="IxBatch",
                            description="Impresora fiscal Epson para Venezuela"
                        )
                    elif "Bixolon" in brand_dir:
                        populate_from_markdown(
                            conn, md_path,
                            brand="Bixolon",
                            model="SPK-S300",
                            identifier_string="BIX",
                            dll_name="Spark32.DLL",
                            protocol_type="IxBatch",
                            description="Impresora fiscal Bixolon para Venezuela"
                        )

    conn.commit()
    conn.close()

    print(f"\nDatabase populated successfully at: {DB_PATH}")


if __name__ == "__main__":
    main()
