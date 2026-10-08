"""
Fiscal Printer State Persistence
Saves/restores simulator state to a JSON file on disk, so counters,
company data and print history survive restarts.
"""

import json
import os
import logging
import threading
from datetime import datetime, date
from typing import Any

logger = logging.getLogger("fiscalsim.persistence")

_SAVE_LOCK = threading.Lock()

# State fields that are JSON-serializable and safe to restore
_PERSIST_KEYS = [
    # identity / config
    "serial_number", "fiscal_registration", "rif", "mode",
    "memory_status", "current_state",
    # counters
    "fiscal_counter", "invoice_counter", "credit_note_counter",
    "debit_note_counter", "non_fiscal_counter", "z_report_counter",
    "x_report_counter", "daily_closure_counter",
    # lifetime totals
    "total_sales", "total_tax", "total_discounts", "total_surcharges",
    # daily totals
    "daily_sales", "daily_tax", "daily_discounts", "daily_surcharges",
    "daily_invoices", "daily_credit_notes", "daily_debit_notes",
    "daily_non_fiscal",
    # breakdowns
    "tax_totals", "credit_note_totals", "debit_note_totals",
    "payment_totals",
    # company / fiscal memory
    "company", "headers", "footers", "flags",
    # in-progress document (so a restart doesn't lose an open sale)
    "document_open", "document_type", "current_items",
    "subtotal_bases", "subtotal_tax", "amount_payable",
    "payments_made", "payment_count", "doc_payments",
    "subtotal_printed", "customer_rif", "customer_name",
    "customer_address", "customer_phone", "reference_invoice",
    "reference_date", "reference_serial",
    # audit memory
    "audit_memory_number", "audit_memory_total", "audit_memory_free",
    "audit_memory_used",
    # reports + paper
    "z_reports", "x_reports", "print_jobs", "print_job_seq",
    # misc
    "tax_rates", "tax_type", "last_invoice_date", "last_z_report_date",
]


def _json_default(obj: Any):
    """Serialize datetime/date objects for JSON."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


def save_state(sim) -> None:
    """Persist the simulator state to sim.state_path (atomic write)."""
    path = getattr(sim, "state_path", None)
    if not path:
        return
    try:
        state = sim.state
        data = {
            "saved_at": datetime.now().isoformat(),
            "brand": sim.brand,
            "model": sim.model,
            "command_count": sim.command_count,
            "history": sim.history[-500:],
        }
        for key in _PERSIST_KEYS:
            if hasattr(state, key):
                data[key] = getattr(state, key)
        # Locks and other non-serializable runtime objects are skipped
        payload = json.dumps(data, ensure_ascii=False, default=_json_default,
                             indent=1)
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        tmp_path = path + ".tmp"
        with _SAVE_LOCK:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp_path, path)
    except Exception as exc:  # never break command processing on save
        logger.warning("Could not save state to %s: %s", path, exc)


def load_state(sim) -> bool:
    """Restore persisted state into sim. Returns True if a file was loaded."""
    path = getattr(sim, "state_path", None)
    if not path or not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        logger.warning("Could not load state from %s: %s", path, exc)
        return False
    try:
        state = sim.state
        for key in _PERSIST_KEYS:
            if key in data:
                setattr(state, key, data[key])
        # Timestamps come back as ISO strings: convert known fields
        for attr in ("last_invoice_date", "last_z_report_date"):
            value = getattr(state, attr, None)
            if isinstance(value, str):
                try:
                    setattr(state, attr, datetime.fromisoformat(value))
                except ValueError:
                    setattr(state, attr, None)
        # Company RIF drives the machine registration
        if isinstance(state.company, dict) and state.company.get("rif"):
            state.rif = state.company["rif"]
            state.fiscal_registration = state.company["rif"]
        # Normalize coherence: no open document => waiting state
        if not state.document_open:
            state.current_state = "waiting"
            state.current_items = []
            state.document_type = None
        sim.command_count = int(data.get("command_count", 0) or 0)
        history = data.get("history") or []
        if isinstance(history, list):
            sim.history = history
        logger.info("Restored state from %s", path)
        return True
    except Exception as exc:
        logger.warning("Could not apply state from %s: %s", path, exc)
        return False
