# SimuladorFiscalGO

Simulador de impresoras fiscales para Venezuela. Soporta las marcas TFHKA, Hasar SMH/P-615F, Bixolon SRP-270 y Epson TM2000, con panel web, memoria fiscal programable, papel virtual y reportes X/Z.

## Panel web (recomendado)

```bash
python panel.py                    # http://127.0.0.1:8080
python panel.py --port 9000
python panel.py --host 0.0.0.0 --port 8080 --no-browser
```

El panel muestra, en una sola ventana:

- **Salida fiscal (lado izquierdo):** el papel virtual con la factura/nota/reportes tal como los imprimiría la máquina, con encabezado legal (RIF, razón social, domicilio, representante, actividad económica), desglose de IVA por alícuota, monto en letras y pie de ley. Mientras el documento está abierto se ve una **vista previa en vivo**.
- **Registro de actividad:** todo lo que procesa la impresora, comando por comando con su respuesta.
- **Memoria fiscal:** formulario con los datos que exige la ley (RIF, razón social, domicilio fiscal, municipio/ciudad/estado, teléfono, representante legal + cédula, actividad económica, condiciones de pago, contribuyente especial / agente de retención). Al programarlo, los datos aparecen en el encabezado de todo documento impreso (S8E).
- **Emisión rápida:** cliente, ítems con alícuota, subtotal, pago, cierre — genera los comandos reales del protocolo de cada marca.
- **Reportes X y Z:** X lee sin reiniciar; Z cierra el día (reinicia acumulados diarios pero conserva contadores históricos).
- **Consola de comandos:** envío de comandos crudos del protocolo real.
- **Selector de marca:** TFHKA / Hasar / Bixolon / Epson, cada uno con su propio estado persistido en `data/state_<marca>.json`.

## API REST (para integración, p.ej. ERPGo)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET  | `/api/state?brand=X` | Estado completo (contadores, documento, memoria) |
| GET  | `/api/history?brand=X&since=N` | Log de comandos desde la secuencia N |
| GET  | `/api/preview?brand=X` | Vista previa del documento en curso |
| GET  | `/api/jobs?brand=X` | Documentos impresos (metadatos) |
| GET  | `/api/job/<id>?brand=X` | Líneas de papel de un job |
| GET  | `/api/company?brand=X` | Memoria fiscal programada |
| POST | `/api/command` | `{"brand":"tfhka","command":"101"}` comando crudo |
| POST | `/api/company` | `{"brand":"tfhka","company":{...}}` programar memoria |
| POST | `/api/sale` | `{"brand":"tfhka","action":"item","params":{...}}` paso de venta |
| POST | `/api/report` | `{"brand":"tfhka","type":"x"\|"z"}` imprimir reporte |

Acciones de `/api/sale`: `open`, `customer`, `item`, `subtotal`, `payment`, `close`, `status`, `cancel`, `drawer`, `report`.

## CLI serial (modo interactivo / pyserial)

```bash
python sim.py --model tfhka --port COM5 --log sim.log
python sim.py --model hasar --port COM3
python sim.py --model bixolon --port COM7 --baud 19200
python sim.py --model epson --port COM9 --baud 115200
python sim.py --model tfhka --port COM5 --mode test
```

## Pruebas

```bash
python test_sim.py
```

Cubre los 4 protocolos: TFHKA (ASCII), Hasar/Bixolon/Epson (IxBatch `@...`), notas crédito/débito, docs no fiscales, reportes X y Z.

## Semántica de contadores

- **Históricos** (nunca se reinician): `invoice_counter`, `credit_note_counter`, `total_sales`, `total_tax` — facturas consecutivas y ventas acumuladas de por vida.
- **Diarios** (los reinicia solo el reporte Z): `daily_sales`, `daily_invoices`, `tax_totals`, `payment_totals` — lo que muestran los reportes X/Z.
- El estado completo, la memoria fiscal y los jobs de impresión se persisten en `data/state_<marca>.json` tras cada comando.

## Modelos soportados

### TFHKA (The Factory HKA)
- Protocolo ASCII: ítems con prefijo de tasa (`!` general 16%, `"` reducida 8%, `#` adicional 30, espacio exento)
- Subtotal `3`, pago `100xx.xx`, cierre `101`, reportes `U0X`/`U0Z`, status `S1`-`S8P`

### Hasar SMH/P-615F · Bixolon SRP-270 · Epson TM2000
- Protocolo IxBatch: `@OpenFiscalReceipt`, `@CustomerData|rif|nombre|dir`, `@PrintLine|desc|cant|precio|tasa`, `@AddPayment|monto|metodo`, `@Close`, `@Status`, `@PrintXReport`, `@PrintZReport`
- Epson envuelve toda respuesta con `0xSTATUS|0xERROR|`

## Estructura del proyecto

```
SimuladorFiscalGO/
├── panel.py                   # Panel web (entry point)
├── sim.py                     # CLI serial
├── test_sim.py                # Suite de pruebas
├── data/                      # Estado persistido por marca
├── fiscalsim/
│   ├── protocol.py            # Constantes y parsers (TFHKA / IxBatch)
│   ├── state.py               # Estado interno + memoria fiscal
│   ├── simulator.py           # Enrutado, handlers, jobs de impresión
│   ├── render.py              # Papel virtual: facturas y reportes X/Z
│   ├── persistence.py         # Guardado/carga en disco
│   ├── webapp.py              # Servidor HTTP + API REST
│   ├── static/index.html      # UI del panel
│   └── models/
└── README.md
```
