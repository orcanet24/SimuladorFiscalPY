-- Schema for Fiscal Printer Protocol Documentation Database
-- Database: docs.db
-- Location: SimuladorFiscalPY/

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- ============================================================
-- Table: printer_models
-- Stores information about each fiscal printer model
-- ============================================================
CREATE TABLE IF NOT EXISTS printer_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,           -- 'Hasar', 'Epson', 'Bixolon'
    model TEXT NOT NULL,           -- 'SMH/PT-100FVE', 'TM-2032', etc.
    identifier_string TEXT,        -- ActiveX identifier: 'H250', 'TM20', etc.
    dll_name TEXT,                 -- DLL file name: 'H25032.DLL', 'TM2032.DLL'
    protocol_type TEXT NOT NULL DEFAULT 'IxBatch', -- 'IxBatch', 'PFBATCH', etc.
    description TEXT,
    UNIQUE(brand, model)
);

-- ============================================================
-- Table: commands
-- Stores all fiscal commands for each printer model
-- ============================================================
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    cmd_name TEXT NOT NULL,        -- Command name without @: 'OpenFiscalReceipt'
    syntax TEXT,                   -- Full syntax: '@OpenFiscalReceipt|p1|p2|...'
    description TEXT,              -- Human-readable description
    param_count INTEGER DEFAULT 0, -- Number of parameters
    category TEXT,                 -- 'fiscal_receipt', 'diagnostic', 'config', etc.
    FOREIGN KEY (model_id) REFERENCES printer_models(id) ON DELETE CASCADE,
    UNIQUE(model_id, cmd_name)
);

-- ============================================================
-- Table: command_parameters
-- Stores parameters for each command
-- ============================================================
CREATE TABLE IF NOT EXISTS command_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_id INTEGER NOT NULL,
    param_name TEXT NOT NULL,      -- 'strVar1', 'dblVar2', etc.
    param_type TEXT NOT NULL,      -- 'STRING', 'DOUBLE', 'INT', 'BYTE'
    required INTEGER DEFAULT 1,    -- 1=required, 0=optional
    description TEXT,
    param_order INTEGER DEFAULT 0, -- Position in parameter list
    FOREIGN KEY (command_id) REFERENCES commands(id) ON DELETE CASCADE
);

-- ============================================================
-- Table: status_codes
-- Stores printer and fiscal controller status codes
-- ============================================================
CREATE TABLE IF NOT EXISTS status_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    code_hex TEXT NOT NULL,        -- Hex value: '0x0004'
    code_bit INTEGER NOT NULL,     -- Bit position: 1-16
    description TEXT NOT NULL,
    is_error INTEGER DEFAULT 1,    -- 1=error condition, 0=status/info
    status_type TEXT NOT NULL DEFAULT 'printer', -- 'printer' (IF_ERROR1) or 'fiscal' (IF_ERROR2)
    FOREIGN KEY (model_id) REFERENCES printer_models(id) ON DELETE CASCADE
);

-- ============================================================
-- Table: response_formats
-- Stores response field definitions for each command
-- ============================================================
CREATE TABLE IF NOT EXISTS response_formats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    cmd_name TEXT NOT NULL,        -- Command name
    field_name TEXT NOT NULL,      -- Field description
    field_type TEXT DEFAULT 'STRING', -- 'STRING', 'HEX', 'INT', 'DOUBLE'
    field_order INTEGER DEFAULT 0, -- Position in response
    description TEXT,
    FOREIGN KEY (model_id) REFERENCES printer_models(id) ON DELETE CASCADE
);

-- ============================================================
-- Indexes for performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_commands_model ON commands(model_id);
CREATE INDEX IF NOT EXISTS idx_commands_name ON commands(cmd_name);
CREATE INDEX IF NOT EXISTS idx_params_cmd ON command_parameters(command_id);
CREATE INDEX IF NOT EXISTS idx_status_model ON status_codes(model_id);
CREATE INDEX IF NOT EXISTS idx_response_model_cmd ON response_formats(model_id, cmd_name);
