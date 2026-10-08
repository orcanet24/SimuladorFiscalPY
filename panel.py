#!/usr/bin/env python3
"""
Fiscal Printer Web Panel - Entry Point

Starts the HTTP panel with the virtual fiscal printer:
  - live command log (everything the printer processes)
  - virtual paper output (receipt / X / Z report)
  - fiscal memory programming (company data required by law)
  - quick-sale controls speaking each brand's real protocol

Usage:
    python panel.py                     # http://127.0.0.1:8080
    python panel.py --port 9000
    python panel.py --host 0.0.0.0 --port 8080
"""

import argparse
import logging
import os
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiscalsim.webapp import run_server


def main():
    parser = argparse.ArgumentParser(
        description="Fiscal Printer Web Panel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python panel.py
  python panel.py --port 9000
  python panel.py --host 0.0.0.0 --port 8080 --no-browser
        """)
    parser.add_argument("--host", default="127.0.0.1",
                        help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8080,
                        help="Port (default: 8080)")
    parser.add_argument("--data-dir", default=None,
                        help="Directory for persisted state "
                             "(default: ./data)")
    parser.add_argument("--no-browser", action="store_true",
                        help="Do not open the browser automatically")
    parser.add_argument("--quiet", action="store_true",
                        help="Less console output")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    url = f"http://{args.host}:{args.port}"
    if not args.no_browser and args.host in ("127.0.0.1", "localhost"):
        import threading
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    run_server(args.host, args.port, args.data_dir)


if __name__ == "__main__":
    main()
