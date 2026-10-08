#!/usr/bin/env python3
"""
Fiscal Printer Simulator - CLI Entry Point
Supports TFHKA, Hasar SMH/P-615F, Bixolon SRP-270, Epson TM2000

Usage:
    python sim.py --model tfhka --port COM5 --log sim.log
    python sim.py --model hasar --port COM3 --log hasar.log
    python sim.py --model bixolon --port COM7
    python sim.py --model epson --port COM9 --baud 115200
"""

import argparse
import sys
import os
import time
import threading
import signal
from datetime import datetime

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiscalsim.simulator import create_simulator, FiscalPrinterSimulator
from fiscalsim.protocol import (
    STATUS_CODES, ERROR_CODES, parse_tfhka_command, parse_ixbatch_command
)


class SerialPortListener:
    """Listen on a serial port and process commands"""
    
    def __init__(self, simulator: FiscalPrinterSimulator, port: str, baud: int = 9600):
        self.sim = simulator
        self.port_name = port
        self.baud = baud
        self.running = False
        self.ser = None
        
        # Try to use real serial port if available
        try:
            import serial
            self.ser = serial.Serial(port, baud, timeout=1)
            self.logger = simulator.logger
            self.logger.info(f"Opened serial port {port} at {baud} baud")
        except ImportError:
            self.logger = simulator.logger
            self.logger.warning("pyserial not installed. Using stdin/stdout mode.")
            self.ser = None
        except Exception as e:
            self.logger = simulator.logger
            self.logger.warning(f"Could not open {port}: {e}. Using stdin/stdout mode.")
            self.ser = None
    
    def start(self):
        """Start listening for commands"""
        self.running = True
        
        if self.ser:
            self._serial_loop()
        else:
            self._interactive_loop()
    
    def _serial_loop(self):
        """Read from serial port"""
        buffer = b""
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    buffer += data
                    
                    # Process complete lines (terminated by newline or CR)
                    while b"\n" in buffer or b"\r" in buffer:
                        # Split on newline
                        if b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                        else:
                            line, buffer = buffer.split(b"\r", 1)
                        
                        line = line.decode("ascii", errors="ignore").strip()
                        if line:
                            response = self.sim.process_command(line)
                            # Write response with CRLF
                            self.ser.write((response + "\r\n").encode("ascii"))
                
                time.sleep(0.01)
            except Exception as e:
                self.logger.error(f"Serial error: {e}")
                time.sleep(0.1)
    
    def _interactive_loop(self):
        """Interactive stdin/stdout mode"""
        print(f"\n{'='*60}")
        print(f"  Fiscal Printer Simulator - {self.sim.brand} {self.sim.model}")
        print(f"  Mode: {'Serial' if self.ser else 'Interactive (no serial port)'}")
        print(f"  Type commands and press Enter. Type 'quit' to exit.")
        print(f"  Type 'help' for command examples.")
        print(f"{'='*60}\n")
        
        while self.running:
            try:
                line = input(f"{self.sim.brand}> ").strip()
                if not line:
                    continue
                
                if line.lower() == "quit":
                    self.running = False
                    break
                
                if line.lower() == "help":
                    self._print_help()
                    continue
                
                if line.lower() == "status":
                    self._print_status()
                    continue
                
                response = self.sim.process_command(line)
                print(f"  <- {response}")
                
            except EOFError:
                self.running = False
                break
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"  ERROR: {e}")
        
        print(f"\n{self.sim.brand} Simulator stopped.")
    
    def _print_help(self):
        """Print command examples"""
        print("\n--- TFHKA Commands ---")
        print("  !  001000 000001500 CAFE       (item general 16%)")
        print('  "  002000 000000800 PAN        (item reduced 8%)')
        print("  #  001000 000003000 LICORES    (item additional 30%)")
        print(" 3                          (subtotal with print)")
        print(" 4                          (subtotal silent)")
        print(" 101                        (close and totalize)")
        print(" 0                          (open cash drawer)")
        print(" S1                         (general status)")
        print(" S2                         (document status)")
        print(" S3                         (tax config)")
        print(" U0X                        (X report)")
        print(" U0Z                        (Z report)")
        print("\n--- Hasar IxBatch Commands ---")
        print("  @OpenFiscalReceipt")
        print("  @PrintLine|Cafe|2|15.00|general")
        print("  @AddPayment|30.00|cash")
        print("  @Close")
        print("  @PrintXReport")
        print("  @PrintZReport")
        print("  @CustomerData|J-12345678-9|EMPRESA C.A.|Av Principal")
        print("\n--- Common ---")
        print("  help                       (show this help)")
        print("  status                     (show printer status)")
        print("  quit                       (exit)")
        print()
    
    def _print_status(self):
        """Print current printer status"""
        state = self.sim.state
        status_code = state.get_status_code()
        error_code = state.get_error_code()
        
        print(f"\n--- {self.sim.brand} {self.sim.model} Status ---")
        print(f"  Serial:        {state.serial_number}")
        print(f"  RIF:           {state.rif}")
        print(f"  Status:        0x{status_code:02X} ({STATUS_CODES.get(status_code, 'Unknown')})")
        print(f"  Error:         0x{error_code:02X} ({ERROR_CODES.get(error_code, 'Unknown')})")
        print(f"  Mode:          {state.mode}")
        print(f"  Doc open:      {state.document_open}")
        print(f"  Doc type:      {state.document_type}")
        print(f"  Invoices:      {state.invoice_counter}")
        print(f"  Credit Notes:  {state.credit_note_counter}")
        print(f"  Debit Notes:   {state.debit_note_counter}")
        print(f"  Non-Fiscal:    {state.non_fiscal_counter}")
        print(f"  Z Reports:     {state.z_report_counter}")
        print(f"  Total Sales:   {state.total_sales:.2f}")
        print(f"  Total Tax:     {state.total_tax:.2f}")
        print(f"  Audit Mem:     {state.audit_memory_free:.2f}/{state.audit_memory_total:.2f} MB")
        print(f"  Commands:      {self.sim.command_count}")
        print()
    
    def stop(self):
        """Stop the listener"""
        self.running = False
        if self.ser:
            try:
                self.ser.close()
            except:
                pass


def setup_logging(log_file: str = None):
    """Setup logging"""
    import logging
    
    # Create logger
    logger = logging.getLogger("fiscalsim")
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    
    # File handler
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(fh)
    
    return logger


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Fiscal Printer Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sim.py --model tfhka --port COM5 --log sim.log
  python sim.py --model hasar --port COM3
  python sim.py --model bixolon --port COM7 --baud 19200
  python sim.py --model epson --port COM9 --baud 115200
        """
    )
    
    parser.add_argument(
        "--model", "-m",
        required=True,
        choices=["tfhka", "hasar", "bixolon", "epson"],
        help="Printer brand/model to simulate"
    )
    
    parser.add_argument(
        "--port", "-p",
        default="COM5",
        help="Serial port (default: COM5)"
    )
    
    parser.add_argument(
        "--baud", "-b",
        type=int,
        default=9600,
        help="Baud rate (default: 9600)"
    )
    
    parser.add_argument(
        "--log", "-l",
        default=None,
        help="Log file path (default: fiscalsim.log)"
    )
    
    parser.add_argument(
        "--mode",
        choices=["fiscal", "test"],
        default="fiscal",
        help="Initial printer mode (default: fiscal)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = args.log or "fiscalsim.log"
    logger = setup_logging(log_file)
    
    # Create simulator
    try:
        sim = create_simulator(args.model)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Set initial mode
    sim.state.mode = args.mode
    
    logger.info(f"Starting {args.model.upper()} simulator on {args.port} at {args.baud} baud")
    logger.info(f"Mode: {args.mode}")
    
    # Create serial listener
    listener = SerialPortListener(sim, args.port, args.baud)
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        listener.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start listening
    listener.start()


if __name__ == "__main__":
    main()
