# Fiscal Printer Docs Database

SQLite database storing complete fiscal printer protocol documentation for the SimuladorFiscalPY project.

## Files

| File | Purpose |
|------|---------|
| `docs.db` | SQLite database (created by `create_database.py`) |
| `schema.sql` | Database schema definition |
| `create_database.py` | Creates empty database with schema |
| `populate_database.py` | Populates database from markdown docs in `C:/c/drivers/*/doc/` |
| `query.py` | CLI query tool to look up commands, status codes, etc. |

## Quick Start

```bash
# Create and populate
cd SimuladorFiscalPY
python create_database.py
python populate_database.py

# Query all commands for Hasar
python query.py commands Hasar "PT-100"

# Query status codes
python query.py status_codes Hasar "PT-100" printer
python query.py status_codes Hasar "PT-100" fiscal

# Query response format
python query.py response OpenFiscalReceipt Hasar

# List all models
python query.py models

# Search
python query.py search "IVA"
```

## Schema

- **printer_models** — Printer brand/model info (Hasar, Epson, Bixolon)
- **commands** — All fiscal commands per model (48 commands for Hasar)
- **command_parameters** — Parameter definitions for each command
- **status_codes** — Printer (IF_ERROR1) and Fiscal (IF_ERROR2) status codes
- **response_formats** — Response field definitions for commands

## Data Sources

Scans `C:/c/drivers/*/doc/` directories for markdown/text documentation.
Currently populated: Hasar VE (from `C:/c/drivers/HasarVE/doc/hasar.md`).
