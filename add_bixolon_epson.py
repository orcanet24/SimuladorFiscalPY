#!/usr/bin/env python3
"""
Agregar modelos Bixolon/Spark y Epson a la DB docs.db con todos los comandos extraídos
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs.db")

def add_bixolon(conn):
    """Agregar modelo Bixolon/Spark con 56 comandos"""
    cursor = conn.cursor()
    
    # Insertar modelo
    cursor.execute("""
        INSERT OR REPLACE INTO printer_models (brand, model, identifier_string, dll_name, protocol_type, description)
        VALUES ('Bixolon', 'SRP-270/350, BMC, ACLAS, OKI', 'BIXOLON', 'FiscalNET.dll', 'IxBatch',
                'Samsung Bixolon SRP-270/350, BMC Camel/Spark 614, ACLAS PP1F3, OKI ML 1120. SDK BixolonVE (IFDrivers Argentina).')
    """)
    model_id = cursor.lastrowid or cursor.execute("SELECT id FROM printer_models WHERE brand='Bixolon'").fetchone()[0]
    
    commands = [
        # Comandos para apertura del sistema
        ("Login", "@Login|<nVar1>", "Logon - Cajero", 1, "system"),
        ("Logoff", "@Logoff|", "Log-off cajero", 0, "system"),
        ("TrainingMode", "@TrainingMode|<byVar1>", "Modo Entrenamiento I/F", 1, "system"),
        
        # Comandos de comprobante fiscal
        ("BarCode", "@BarCode|<nVar1>|<strVar2>|<byVar3>|<byVar4>", "Código de Barras", 4, "fiscal_receipt"),
        ("Cancel", "@Cancel|", "Cancelar comprobante", 0, "fiscal_receipt"),
        ("DirectPayment", "@DirectPayment|<nVar1>", "Pago Directo", 1, "fiscal_receipt"),
        ("LastItemCancel", "@LastItemCancel|", "Cancelar último ítem", 0, "fiscal_receipt"),
        ("LastItemDiscount", "@LastItemDiscount|<dblVar1>|<byVar2>", "Descuento último ítem", 2, "fiscal_receipt"),
        ("PrintFiscalText", "@PrintFiscalText|<strVar1>", "Texto fiscal/comentario", 1, "fiscal_receipt"),
        ("PrintLineItem", "@PrintLineItem|<strVar1>|<dblVar2>|<dblVar3>|<nVar4>|<byVar5>", "Imprimir ítem de línea", 5, "fiscal_receipt"),
        ("RefundClose", "@RefundClose|<dblVar1>|<nVar2>", "Cierre de devolución", 2, "fiscal_receipt"),
        ("RefundItem", "@RefundItem|<strVar1>|<dblVar2>|<dblVar3>|<nVar4>", "Registro producto devolución", 4, "fiscal_receipt"),
        ("SetCustomerData", "@SetCustomerData|<nVar1>|<strVar2>", "Datos comprador", 2, "fiscal_receipt"),
        ("SetCustomerExtraData", "@SetCustomerExtraData|<strVar1>|<strVar2>|<strVar3>", "Razón social y RIF", 3, "fiscal_receipt"),
        ("SetCustomerInfo1", "@SetCustomerInfo1|<strVar1>", "Razón social línea 1", 1, "fiscal_receipt"),
        ("SetCustomerInfo2", "@SetCustomerInfo2|<strVar1>", "Razón social línea 2", 1, "fiscal_receipt"),
        ("SetCustomerTIN", "@SetCustomerTIN|<strVar1>", "RIF o C.I. cliente", 1, "fiscal_receipt"),
        ("Subtotal", "@Subtotal|", "Subtotal con impresión", 0, "fiscal_receipt"),
        ("TotalTender", "@TotalTender|<nVar1>|<dblVar2>", "Medio de pago", 2, "fiscal_receipt"),
        
        # Comandos de comprobante no fiscal
        ("CloseCashReceipt", "@CloseCashReceipt|", "Fin reporte egreso/ingreso", 0, "non_fiscal"),
        ("PrintCashItem", "@PrintCashItem|<nVar1>|<dblVar2>|<byVar3>", "Egreso/ingreso efectivo", 3, "non_fiscal"),
        ("PrintNonFiscalText", "@PrintNonFiscalText|<strVar1>|<byVar2>", "Texto no fiscal", 2, "non_fiscal"),
        
        # Comandos de diagnóstico y consulta
        ("StatusRequest", "@StatusRequest|<byVar1>", "Consulta estado impresora", 1, "diagnostic"),
        
        # Comandos de configuración
        ("ConfigureControllerByOne", "@ConfigureControllerByOne|<nVar1>|<nVar2>", "Configuración controlador", 2, "config"),
        ("PrintConfigurationData", "@PrintConfigurationData|", "Imprimir configuración", 0, "config"),
        ("ProgramClerk", "@ProgramClerk|<nVar1>|<strVar2>|<strVar3>", "Programar cajero", 3, "config"),
        ("ProgramPaymentMedia", "@ProgramPaymentMedia|<nVar1>|<strVar2>", "Programar medio pago", 2, "config"),
        ("ProgramSymbol", "@ProgramSymbol|<nVar1>|<strVar2>", "Programar símbolo", 2, "config"),
        ("ProgramTaxes", "@ProgramTaxes|<nVar1>|<dblVar2>", "Programar tasas IVA", 2, "config"),
        ("SaveTaxes", "@SaveTaxes|", "Guardar tasas", 0, "config"),
        ("SetDate", "@SetSetDate|<strVar1>", "Establecer fecha", 1, "config"),
        ("SetTime", "@SetTime|<strVar1>", "Establecer hora", 1, "config"),
        
        # Comandos de control fiscal
        ("DailyClose", "@DailyClose|<byVar1>", "Cierre diario Z/X", 1, "fiscal_control"),
        ("DailyCloseByDate", "@DailyCloseByDate|<strVar1>|<strVar2>", "Cierre diario por fecha", 2, "fiscal_control"),
        ("DailyCloseByNumber", "@DailyCloseByNumber|<nVar1>|<nVar2>", "Cierre diario por número", 2, "fiscal_control"),
        ("PrintAuditStatusReport", "@PrintAuditStatusReport|", "Reporte auditoría", 0, "fiscal_control"),
        ("Reprint", "@Reprint|", "Reimpresión último", 0, "fiscal_control"),
        ("ReprintByDate", "@ReprintByDate|<strVar1>|<strVar2>", "Reimpresión por fecha", 2, "fiscal_control"),
        ("ReprintByNumber", "@ReprintByNumber|<nVar1>|<nVar2>", "Reimpresión por número", 2, "fiscal_control"),
        
        # Comandos generales
        ("OpenDrawer", "@OpenDrawer|<byVar1>", "Abrir gaveta", 1, "general"),
        ("PrintTest", "@PrintTest|", "Imprimir test", 0, "general"),
        ("ResetPrinterBuffer", "@ResetPrinterBuffer|", "Reset buffer", 0, "general"),
        ("SendRawCommand", "@SendRawCommand|<strVar1>", "Enviar comando raw", 1, "general"),
        ("SetHeaderTrailer", "@SetHeaderTrailer|<nVar1>|<strVar2>", "Encabezado/pie", 2, "general"),
        
        # Comandos de display
        ("DisplayCommercial", "@DisplayCommercial|", "Mostrar mensaje comercial", 0, "display"),
        ("DisplayDateTime", "@DisplayDateTime|", "Mostrar fecha/hora", 0, "display"),
        ("DisplayMessage", "@DisplayMessage|<byVar1>|<strVar2>", "Mostrar mensaje", 2, "display"),
        ("ProgramCommercial", "@ProgramCommercial|<strVar1>", "Programar comercial", 1, "display"),
        ("ProgramMessage", "@ProgramMessage|<nVar1>|<strVar2>", "Programar mensaje", 2, "display"),
        
        # Comandos de cheques
        ("FormatCheck", "@FormatCheck|<nVar1>|<nVar2>|<nVar3>|<nVar4>|<nVar5>|<dblVar6>|<strVar7>|<strVar8>", "Formato cheque frontal", 8, "check"),
        ("FormatEndorse", "@FormatEndorse|<nVar1>|<strVar2>", "Formato endoso", 2, "check"),
        ("ModeSlip", "@ModeSlip|<byVar1>", "Modo slip", 1, "check"),
        ("ModeValidation", "@ModeValidation|<byVar1>", "Modo validación", 1, "check"),
        ("PrintEndorse", "@PrintEndorse|<nVar1>", "Imprimir endoso", 1, "check"),
        ("PrintValidation", "@PrintValidation|<strVar1>", "Imprimir validación", 1, "check"),
        ("ReadMICR", "@ReadMICR|", "Lectura MICR", 0, "check"),
    ]
    
    for cmd_name, syntax, desc, param_count, category in commands:
        cursor.execute("""
            INSERT OR REPLACE INTO commands (model_id, cmd_name, syntax, description, param_count, category)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (model_id, cmd_name, syntax, desc, param_count, category))
    
    conn.commit()
    print(f"Bixolon: {len(commands)} comandos agregados (model_id={model_id})")

def add_epson(conn):
    """Agregar modelo Epson TM2000 con comandos fiscales via EpsonVE SDK"""
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO printer_models (brand, model, identifier_string, dll_name, protocol_type, description)
        VALUES ('Epson', 'TM-2000/3000', 'EPSON', 'TM2032.DLL', 'IxBatch',
                'Epson TM-2000/3000 fiscales. SDK EpsonVE (IFDrivers Argentina). Usa IF_OPEN/IF_WRITE/IF_READ.')
    """)
    model_id = cursor.lastrowid or cursor.execute("SELECT id FROM printer_models WHERE brand='Epson'").fetchone()[0]
    
    # Los comandos de Epson son similares a Bixolon (mismo SDK IFDrivers) pero con diferencias sutiles
    commands = [
        # Fiscales
        ("OpenFiscalReceipt", "@OpenFiscalReceipt|<nVar1>|<strVar2>|<strVar3>", "Abrir comprobante fiscal", 3, "fiscal_receipt"),
        ("CloseFiscalReceipt", "@CloseFiscalReceipt|<byVar1>", "Cerrar comprobante fiscal", 1, "fiscal_receipt"),
        ("CancelFiscalReceipt", "@CancelFiscalReceipt|", "Cancelar comprobante", 0, "fiscal_receipt"),
        ("PrintLineItem", "@PrintLineItem|<strVar1>|<dblVar2>|<dblVar3>|<nVar4>|<byVar5>|<byVar6>", "Imprimir ítem", 6, "fiscal_receipt"),
        ("Subtotal", "@Subtotal|", "Subtotal", 0, "fiscal_receipt"),
        ("TotalTender", "@TotalTender|<nVar1>|<dblVar2>|<byVar3>", "Pago/total", 3, "fiscal_receipt"),
        ("LastItemDiscount", "@LastItemDiscount|<dblVar1>|<byVar2>|<byVar3>", "Descuento ítem", 3, "fiscal_receipt"),
        ("LastItemCancel", "@LastItemCancel|", "Cancelar último ítem", 0, "fiscal_receipt"),
        ("SetHeader", "@SetHeader|<nVar1>|<strVar1>", "Config encabezado", 2, "fiscal_receipt"),
        ("SetTrailer", "@SetTrailer|<nVar1>|<strVar1>", "Config pie", 2, "fiscal_receipt"),
        ("SetCustomerData", "@SetCustomerData|<nVar1>|<strVar2>|<strVar3>|<strVar4>", "Datos cliente", 4, "fiscal_receipt"),
        ("PrintFiscalText", "@PrintFiscalText|<strVar1>", "Texto fiscal", 1, "fiscal_receipt"),
        
        # No fiscales
        ("OpenNonFiscalReceipt", "@OpenNonFiscalReceipt|", "Abrir DNF", 0, "non_fiscal"),
        ("CloseNonFiscalReceipt", "@CloseNonFiscalReceipt|<byVar1>", "Cerrar DNF", 1, "non_fiscal"),
        ("PrintNonFiscalText", "@PrintNonFiscalText|<strVar1>|<byVar2>", "Texto no fiscal", 2, "non_fiscal"),
        
        # Control
        ("StatusRequest", "@StatusRequest|<byVar1>", "Estado", 1, "diagnostic"),
        ("ConfigureControllerByOne", "@ConfigureControllerByOne|<nVar1>|<nVar2>", "Configuración", 2, "config"),
        ("DailyClose", "@DailyClose|<byVar1>", "Cierre Z/X", 1, "fiscal_control"),
        ("OpenDrawer", "@OpenDrawer|<byVar1>", "Gaveta", 1, "general"),
    ]
    
    for cmd_name, syntax, desc, param_count, category in commands:
        cursor.execute("""
            INSERT OR REPLACE INTO commands (model_id, cmd_name, syntax, description, param_count, category)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (model_id, cmd_name, syntax, desc, param_count, category))
    
    conn.commit()
    print(f"Epson: {len(commands)} comandos agregados (model_id={model_id})")

def main():
    conn = sqlite3.connect(DB_PATH)
    print(f"Conectado a {DB_PATH}")
    
    # Verificar tablas
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tablas: {tables}")
    
    # Agregar modelos
    if "Bixolon" not in [r[0] for r in cursor.execute("SELECT brand FROM printer_models").fetchall()]:
        add_bixolon(conn)
    else:
        print("Bixolon ya existe, actualizando...")
        add_bixolon(conn)
    
    if "Epson" not in [r[0] for r in cursor.execute("SELECT brand FROM printer_models").fetchall()]:
        add_epson(conn)
    else:
        print("Epson ya existe, actualizando...")
        add_epson(conn)
    
    # Resumen final
    cursor.execute("SELECT brand, model, (SELECT COUNT(*) FROM commands WHERE model_id = pm.id) as cmd_count FROM printer_models pm")
    print("\n=== Resumen de la DB ===")
    for row in cursor.fetchall():
        print(f"  {row[0]} {row[1]}: {row[2]} comandos")
    
    cursor.execute("SELECT COUNT(*) FROM commands")
    print(f"\nTotal comandos: {cursor.fetchone()[0]}")
    
    conn.close()

if __name__ == "__main__":
    main()
