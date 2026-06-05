#!/usr/bin/env python3
"""Self-contained OCPP 1.6 EVSE simulator.

Run:
    python3 ocpp_evse_simulator.py

Then open the printed localhost URL in a browser.
"""

from __future__ import annotations

import argparse
import http.server
import pathlib
import socketserver
import sys
import threading
import webbrowser


BASE_DIR = pathlib.Path(__file__).resolve().parent
FER_LOGO = BASE_DIR / "fer_white_logo.png"
SIMULATOR_HTML = BASE_DIR / "ocpp_evse_simulator.html"


class SimulatorHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/fer_white_logo.png":
            self.send_png(FER_LOGO)
            return
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        try:
            body = self.read_html()
        except FileNotFoundError as exc:
            self.send_error(500, str(exc))
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_html(self) -> bytes:
        if not SIMULATOR_HTML.is_file():
            raise FileNotFoundError(f"Missing simulator UI file: {SIMULATOR_HTML}")
        return SIMULATOR_HTML.read_bytes()

    def send_png(self, path: pathlib.Path) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}", file=sys.stderr)


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False


def serve(host: str, port: int, open_browser: bool) -> None:
    with ReusableTCPServer((host, port), SimulatorHandler) as httpd:
        actual_port = httpd.server_address[1]
        url = f"http://{host}:{actual_port}/"
        print(f"OCPP 1.6 EVSE simulator running at {url}")
        print("Press Ctrl+C to stop.")
        if open_browser:
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping simulator.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a self-contained OCPP 1.6 EVSE simulator UI.")
    parser.add_argument("--host", default="127.0.0.1", help="Host/interface to bind.")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind. Use 0 for a free port.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically.")
    args = parser.parse_args()
    serve(args.host, args.port, not args.no_browser)


if __name__ == "__main__":
    main()
