#!/usr/bin/env python3
"""Minimal dependency-free OCPP-J 1.6 Central System server.

Run:
    python3 ocpp_server.py --port 3000

Use ws://localhost:3000/OCPP as the EVSE simulator URL.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import os
import pathlib
import socket
import socketserver
import struct
import sys
import threading
import time
import urllib.parse
from datetime import datetime, timezone


AUTHORIZED_CHARGERS = {
    # ISPIT 1
    # Dodajte personaliziranu punionicu. Identifikator punionice i lozinka
    # moraju biti izvedeni iz vašeg JMBAG-a prema pravilu iz teksta zadatka.
    "FER7606000088": "7606000088",
}

AUTHORIZED_TAGS = {
    # ISPIT 1:
    # Dodajte personaliziranu RFID oznaku povezanu s vašim JMBAG-om.
    "TAG7606000088": "7606000088",
}

SERVER_CONFIG = {
    "heartbeat_interval": 30,
    "meter_value_sample_interval": 15,
}

BASE_DIR = pathlib.Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
FER_LOGO = BASE_DIR / "fer_white_logo.png"
SERVER_UI_HTML = BASE_DIR / "ocpp_server_ui.html"

CALL = 2
CALL_RESULT = 3
CALL_ERROR = 4


def ocpp_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log_line(filename: str, message: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    with (LOG_DIR / filename).open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line)


def json_compact(payload: object) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def read_recent_logs(max_lines: int = 250) -> list[str]:
    LOG_DIR.mkdir(exist_ok=True)
    lines: list[str] = []
    for path in sorted(LOG_DIR.glob("*.log")):
        if path.name == "ui.log":
            continue
        try:
            file_lines = path.read_text(encoding="utf-8").splitlines()[-80:]
        except OSError:
            continue
        lines.extend(f"{path.name}: {line}" for line in file_lines)
    return lines[-max_lines:]


class ChargerSession:
    def __init__(self, charger_id: str, ws: object) -> None:
        self.charger_id = charger_id
        self.ws = ws
        self.connected_at = ocpp_timestamp()
        self.last_seen = self.connected_at
        self.transactions: dict[int, dict[str, object]] = {}
        self.remote_start_authorizations: list[dict[str, object]] = []
        self.connector_statuses: dict[str, dict[str, object]] = {}
        self.last_meter_values: dict[str, dict[str, object]] = {}
        self.next_transaction_id = int(time.time())
        self.next_server_call_id = 0
        self.lock = threading.Lock()

    def new_transaction_id(self) -> int:
        with self.lock:
            self.next_transaction_id += 1
            return self.next_transaction_id

    def new_server_call_id(self) -> str:
        with self.lock:
            self.next_server_call_id += 1
            return f"server-{int(time.time() * 1000)}-{self.next_server_call_id}-{os.urandom(3).hex()}"


class OcppCentralSystem:
    def __init__(self) -> None:
        self.sessions: dict[str, ChargerSession] = {}
        self.lock = threading.Lock()

    def register(self, charger_id: str, ws: object) -> ChargerSession:
        session = ChargerSession(charger_id, ws)
        with self.lock:
            self.sessions[charger_id] = session
        log_line("server.log", f"{charger_id}: connected")
        return session

    def unregister(self, charger_id: str) -> None:
        with self.lock:
            self.sessions.pop(charger_id, None)
        log_line("server.log", f"{charger_id}: disconnected")

    def list_chargers(self) -> list[str]:
        with self.lock:
            return sorted(self.sessions)

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            sessions = list(self.sessions.values())
        chargers: list[dict[str, object]] = []
        for session in sessions:
            with session.lock:
                chargers.append({
                    "chargerId": session.charger_id,
                    "connectedAt": session.connected_at,
                    "lastSeen": session.last_seen,
                    "transactions": [
                        {"transactionId": transaction_id, **transaction}
                        for transaction_id, transaction in sorted(session.transactions.items())
                    ],
                    "remoteStartAuthorizations": list(session.remote_start_authorizations),
                    "connectorStatuses": dict(session.connector_statuses),
                    "lastMeterValues": dict(session.last_meter_values),
                })
        return {
            "chargers": chargers,
            "authorizedTags": sorted(AUTHORIZED_TAGS),
            "logs": read_recent_logs(),
        }

    def get_session(self, charger_id: str) -> ChargerSession | None:
        with self.lock:
            return self.sessions.get(charger_id)

    def send_server_call(self, charger_id: str, action: str, payload: dict[str, object]) -> str | None:
        session = self.get_session(charger_id)
        if not session:
            log_line("server.log", f"{charger_id}: cannot send {action}; charger is not connected")
            return None
        unique_id = session.new_server_call_id()
        frame = [CALL, unique_id, action, payload]
        encoded = json_compact(frame)
        session.ws.send_text(encoded)
        log_line(f"{charger_id}.log", f"TX {encoded}")
        return unique_id

    def remote_start_transaction(self, charger_id: str, connector_id: int, id_tag: str) -> str | None:
        session = self.get_session(charger_id)
        if not session:
            log_line("server.log", f"{charger_id}: cannot send RemoteStartTransaction; charger is not connected")
            return None

        # ISPIT 4:
        # Spremite jednokratnu autorizaciju udaljenog pokretanja za zadani
        # connector_id i id_tag. Zatim pošaljite OCPP RemoteStartTransaction
        # zahtjev punionici pomoću metode send_server_call.
        #
        # Važno: RemoteStartTransaction ne stvara aktivnu transakciju. Aktivna
        # transakcija nastaje tek kada punionica pošalje StartTransaction.req.
        #
        # Hint: session.remote_start_authorizations je lista rječnika, a OCPP
        # CALL zahtjev šalje se pomoću metode send_server_call.

        session.remote_start_authorizations.append({
            "connectorId": connector_id,
            "idTag": id_tag
        })

        return self.send_server_call(charger_id, "RemoteStartTransaction", {
            "connectorId": connector_id,
            "idTag": id_tag
        })

    def remote_stop_transaction(self, charger_id: str, transaction_id: int | None = None) -> str | None:
        session = self.get_session(charger_id)
        if not session:
            log_line("server.log", f"{charger_id}: cannot send RemoteStopTransaction; charger is not connected")
            return None
        with session.lock:
            if transaction_id is None:
                transaction_id = next(iter(session.transactions)) # odabrana prva sljedeća aktivna

                if not session.transactions:
                    log_line("server.log", f"{charger_id}: no active transaction for RemoteStopTransaction")
                    return None

            elif transaction_id not in session.transactions: # ako transaction_id nije u session.transactions
                log_line("server.log", f"{charger_id}: unknown transaction for RemoteStopTransaction")
                return None
                

        # ISPIT 5:
        # Ako transaction_id nije zadan, odaberite jednu aktivnu transakciju
        # spojene punionice. Ako je zadan, provjerite postoji li u
        # session.transactions. Ne šaljite naredbu za nepoznatu transakciju.
        # Zatim pošaljite OCPP RemoteStopTransaction zahtjev s transactionId-em.
        #
        # Važno: RemoteStopTransaction.conf ne završava transakciju. Punionica
        # završetak javlja zasebnom porukom StopTransaction.req.
        #
        # Hint: session.transactions je rječnik indeksiran transactionId-em.

        return self.send_server_call(charger_id, "RemoteStopTransaction", {"transactionId": transaction_id})

    def handle_call(self, session: ChargerSession, unique_id: str, action: str, payload: object) -> list[object]:
        if not isinstance(payload, dict):
            return [CALL_ERROR, unique_id, "FormationViolation", "Payload must be an object", {}]

        session.last_seen = ocpp_timestamp()
        log_line(f"{session.charger_id}.log", f"CALL {action}: {json_compact(payload)}")

        handlers = {
            "BootNotification": self.boot_notification,
            "Heartbeat": self.heartbeat,
            "Authorize": self.authorize,
            "StartTransaction": self.start_transaction,
            "StopTransaction": self.stop_transaction,
            "MeterValues": self.meter_values,
            "StatusNotification": self.status_notification,
            "DataTransfer": self.data_transfer,
            "DiagnosticsStatusNotification": self.empty_accepted,
            "FirmwareStatusNotification": self.empty_accepted,
        }
        handler = handlers.get(action)
        if not handler:
            return [CALL_ERROR, unique_id, "NotSupported", f"Action {action} is not supported", {}]

        try:
            response = handler(session, payload)
        except Exception as exc:
            log_line(f"{session.charger_id}.log", f"ERROR handling {action}: {exc}")
            return [CALL_ERROR, unique_id, "InternalError", str(exc), {}]

        log_line(f"{session.charger_id}.log", f"CALL_RESULT {action}: {json_compact(response)}")
        return [CALL_RESULT, unique_id, response]

    def boot_notification(self, session: ChargerSession, payload: dict[str, object]) -> dict[str, object]:
        return {
            "currentTime": ocpp_timestamp(),
            "interval": SERVER_CONFIG["heartbeat_interval"],
            "status": "Accepted",
        }

    def heartbeat(self, session: ChargerSession, payload: dict[str, object]) -> dict[str, object]:
        return {"currentTime": ocpp_timestamp()}

    def authorize(self, session: ChargerSession, payload: dict[str, object]) -> dict[str, object]:
        id_tag = str(payload.get("idTag", ""))
        return {"idTagInfo": self.id_tag_info(id_tag)}

    def start_transaction(self, session: ChargerSession, payload: dict[str, object]) -> dict[str, object]:
        id_tag = str(payload.get("idTag", ""))
        connector_id = payload.get("connectorId")
        tag_info = self.id_tag_info(id_tag)
        if self.consume_remote_start_authorization(session, connector_id, id_tag):
            tag_info = {"status": "Accepted"}
        transaction_id = session.new_transaction_id()

        # ISPIT 3:
        # Ako je idTag prihvaćen, spremite novu aktivnu transakciju u
        # session.transactions. Potrebno je spremiti idTag, connectorId,
        # početno stanje brojila meterStart i vrijeme početka.
        #
        # Ne smije se spremiti transakcija za odbijeni idTag.
        #
        # Hint: session.transactions je rječnik indeksiran transactionId-em.
        if tag_info["status"] == "Accepted":
            session.transactions[transaction_id] = {
                "idTag": id_tag,
                "connectorId": connector_id,
                "meterStart": session.last_meter_values,
                "timestamp": ocpp_timestamp()
            }

        return {
            "transactionId": transaction_id,
            "idTagInfo": tag_info,
        }

    def stop_transaction(self, session: ChargerSession, payload: dict[str, object]) -> dict[str, object]:
        transaction_id = payload.get("transactionId")
        try:
            transaction_id = int(transaction_id)
        except (TypeError, ValueError):
            transaction_id = 0

        # ISPIT 6:
        # Pronađite i uklonite aktivnu transakciju prema transactionId-u.
        # Ako payload ne sadrži idTag, ostatak metode treba moći koristiti idTag
        # koji je bio spremljen uz pronađenu transakciju.
        #
        # Hint: metoda pop može istodobno dohvatiti i ukloniti element rječnika.
        transaction = session.transactions.pop(transaction_id, None)

        id_tag = str(payload.get("idTag") or (transaction or {}).get("idTag") or "")
        response: dict[str, object] = {}
        if id_tag:
            response["idTagInfo"] = self.id_tag_info(id_tag)
        return response

    def meter_values(self, session: ChargerSession, payload: dict[str, object]) -> dict[str, object]:
        connector_id = str(payload.get("connectorId", "0"))
        meter_values = payload.get("meterValue")
        latest = meter_values[-1] if isinstance(meter_values, list) and meter_values else {}
        sampled = latest.get("sampledValue") if isinstance(latest, dict) else []
        flattened: dict[str, object] = {}
        if isinstance(sampled, list):
            for sample in sampled:
                if isinstance(sample, dict):
                    measurand = str(sample.get("measurand", "Value"))
                    flattened[measurand] = sample.get("value")
        with session.lock:
            session.last_meter_values[connector_id] = {
                "timestamp": latest.get("timestamp") if isinstance(latest, dict) else ocpp_timestamp(),
                "transactionId": payload.get("transactionId"),
                "sampledValue": flattened,
                "raw": payload,
            }
        return {}

    def status_notification(self, session: ChargerSession, payload: dict[str, object]) -> dict[str, object]:
        connector_id = payload.get("connectorId")
        status = payload.get("status")
        with session.lock:
            session.connector_statuses[str(connector_id)] = {
                "status": status,
                "errorCode": payload.get("errorCode"),
                "timestamp": payload.get("timestamp", ocpp_timestamp()),
            }
        log_line(f"{session.charger_id}.log", f"Connector {connector_id} status: {status}")
        return {}

    def data_transfer(self, session: ChargerSession, payload: dict[str, object]) -> dict[str, object]:
        return {"status": "UnknownVendorId"}

    def empty_accepted(self, session: ChargerSession, payload: dict[str, object]) -> dict[str, object]:
        return {}

    def id_tag_info(self, id_tag: str) -> dict[str, object]:
        # ISPIT 2:
        # Vratite status "Accepted" ako se id_tag nalazi u AUTHORIZED_TAGS.
        # Za praznu ili nepoznatu RFID oznaku metoda mora vratiti "Invalid".
        if id_tag in AUTHORIZED_TAGS:
            return {"status": "Accepted"}

        return {"status": "Invalid"}

    def consume_remote_start_authorization(self, session: ChargerSession, connector_id: object, id_tag: str) -> bool:
        connector_text = str(connector_id)
        with session.lock:
            for authorization in session.remote_start_authorizations:
                if authorization.get("used"):
                    continue

                # ISPIT 4:
                # Provjerite odgovara li ova neiskorištena autorizacija istom
                # connectorId-u i idTag-u iz poruke StartTransaction.req.
                # Ako odgovara, označite je iskorištenom, spremite vrijeme
                # korištenja i vratite True.
                #
                # Hint: autorizacija udaljenog starta smije se iskoristiti samo
                # jednom i vrijedi samo unutar sessiona iste punionice.
                if (str(authorization.get("connectorId")) == connector_text and authorization.get("idTag") == id_tag):
                    authorization["used"] = True
                    authorization["usedAt"] = ocpp_timestamp()
                    return True
        return False


CENTRAL_SYSTEM = OcppCentralSystem()


class WebSocketConnection:
    def __init__(self, request: socketserver.BaseRequestHandler) -> None:
        self.request = request
        self.lock = threading.Lock()

    def send_text(self, text: str) -> None:
        self.send_frame(0x1, text.encode("utf-8"))

    def send_pong(self, payload: bytes = b"") -> None:
        self.send_frame(0xA, payload)

    def send_close(self, code: int = 1000) -> None:
        self.send_frame(0x8, struct.pack("!H", code))

    def send_frame(self, opcode: int, payload: bytes) -> None:
        first = 0x80 | opcode
        length = len(payload)
        if length < 126:
            header = struct.pack("!BB", first, length)
        elif length < 65536:
            header = struct.pack("!BBH", first, 126, length)
        else:
            header = struct.pack("!BBQ", first, 127, length)
        with self.lock:
            self.request.sendall(header + payload)

    def recv_text(self) -> str | None:
        while True:
            opcode, payload = self.recv_frame()
            if opcode == 0x1:
                return payload.decode("utf-8")
            if opcode == 0x8:
                return None
            if opcode == 0x9:
                self.send_pong(payload)
            if opcode == 0xA:
                return "pong"

    def recv_exact(self, count: int) -> bytes:
        data = b""
        while len(data) < count:
            chunk = self.request.recv(count - len(data))
            if not chunk:
                raise ConnectionError("WebSocket closed")
            data += chunk
        return data

    def recv_frame(self) -> tuple[int, bytes]:
        first, second = self.recv_exact(2)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self.recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self.recv_exact(8))[0]
        mask = self.recv_exact(4) if masked else b""
        payload = self.recv_exact(length) if length else b""
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return opcode, payload


class OcppWebSocketHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        try:
            request_line, headers, body = self.read_http_request()
            method, target, _version = request_line.split(" ", 2)
            if method != "GET":
                self.http_error(405, "Method Not Allowed")
                return

            parsed = urllib.parse.urlparse(target)
            charger_id = self.extract_charger_id(parsed.path)
            if not charger_id:
                self.http_error(404, "Expected /OCPP/<chargerId>")
                return
            if not self.is_authorized(charger_id, headers, parsed.query):
                self.http_error(401, "Unauthorized", {"WWW-Authenticate": 'Basic realm="OCPP"'})
                return
            if headers.get("upgrade", "").lower() != "websocket":
                self.http_error(400, "Expected WebSocket upgrade")
                return

            self.accept_websocket(headers)
            ws = WebSocketConnection(self.request)
            session = CENTRAL_SYSTEM.register(charger_id, ws)
            try:
                self.message_loop(ws, session)
            finally:
                CENTRAL_SYSTEM.unregister(charger_id)
        except ConnectionError as exc:
            log_line("server.log", f"connection closed from {self.client_address}: {exc}")
        except Exception as exc:
            log_line("server.log", f"connection error from {self.client_address}: {exc}")

    def read_http_request(self) -> tuple[str, dict[str, str], bytes]:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = self.request.recv(4096)
            if not chunk:
                raise ConnectionError("Client disconnected before handshake")
            data += chunk
            if len(data) > 65536:
                raise ValueError("HTTP headers too large")
        header_bytes, body = data.split(b"\r\n\r\n", 1)
        lines = header_bytes.decode("iso-8859-1").split("\r\n")
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        return lines[0], headers, body

    def extract_charger_id(self, path: str) -> str | None:
        parts = [urllib.parse.unquote(part) for part in path.split("/") if part]
        if len(parts) >= 2 and parts[0].upper() == "OCPP":
            return parts[1]
        return None

    def is_authorized(self, charger_id: str, headers: dict[str, str], query: str) -> bool:
        expected_password = AUTHORIZED_CHARGERS.get(charger_id)
        if expected_password is None:
            log_line("auth.log", f"{charger_id}: rejected unknown charger")
            return False

        credentials = self.basic_credentials(headers.get("authorization", ""))
        if credentials is None:
            query_params = urllib.parse.parse_qs(query)
            auth_values = query_params.get("auth", [])
            credentials = self.query_auth_credentials(auth_values[0]) if auth_values else None
        if credentials != (charger_id, expected_password):
            log_line("auth.log", f"{charger_id}: rejected invalid password")
            return False
        log_line("auth.log", f"{charger_id}: accepted")
        return True

    def basic_credentials(self, header: str) -> tuple[str, str] | None:
        if not header.lower().startswith("basic "):
            return None
        return self.decode_credentials(header[6:].strip())

    def query_auth_credentials(self, value: str) -> tuple[str, str] | None:
        return self.decode_credentials(value)

    def decode_credentials(self, value: str) -> tuple[str, str] | None:
        try:
            decoded = base64.b64decode(value).decode("utf-8")
            username, password = decoded.split(":", 1)
            return username, password
        except Exception:
            return None

    def accept_websocket(self, headers: dict[str, str]) -> None:
        key = headers.get("sec-websocket-key")
        if not key:
            self.http_error(400, "Missing Sec-WebSocket-Key")
            raise ValueError("Missing Sec-WebSocket-Key")
        accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        protocol_header = ""
        offered = [item.strip() for item in headers.get("sec-websocket-protocol", "").split(",")]
        if "ocpp1.6" in offered:
            protocol_header = "Sec-WebSocket-Protocol: ocpp1.6\r\n"
        elif "ocpp1.5" in offered:
            protocol_header = "Sec-WebSocket-Protocol: ocpp1.5\r\n"
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            f"{protocol_header}"
            "\r\n"
        )
        self.request.sendall(response.encode("ascii"))

    def message_loop(self, ws: WebSocketConnection, session: ChargerSession) -> None:
        while True:
            message = ws.recv_text()
            if message is None:
                break
            if message == "ping":
                ws.send_text("pong")
                continue
            try:
                frame = json.loads(message)
            except json.JSONDecodeError:
                log_line(f"{session.charger_id}.log", f"Invalid JSON: {message}")
                continue
            log_line(f"{session.charger_id}.log", f"RX {json_compact(frame)}")
            response = self.handle_ocpp_frame(session, frame)
            if response is not None:
                encoded = json_compact(response)
                ws.send_text(encoded)
                log_line(f"{session.charger_id}.log", f"TX {encoded}")

    def handle_ocpp_frame(self, session: ChargerSession, frame: object) -> list[object] | None:
        if not isinstance(frame, list) or len(frame) < 3:
            return [CALL_ERROR, "unknown", "FormationViolation", "Frame must be a valid OCPP array", {}]
        message_type = frame[0]
        if message_type == CALL:
            if len(frame) != 4:
                return [CALL_ERROR, str(frame[1]), "FormationViolation", "CALL must have 4 elements", {}]
            return CENTRAL_SYSTEM.handle_call(session, str(frame[1]), str(frame[2]), frame[3])
        if message_type == CALL_RESULT:
            log_line(f"{session.charger_id}.log", f"CALL_RESULT from charger: {json_compact(frame)}")
            return None
        if message_type == CALL_ERROR:
            log_line(f"{session.charger_id}.log", f"CALL_ERROR from charger: {json_compact(frame)}")
            return None
        return [CALL_ERROR, str(frame[1]) if len(frame) > 1 else "unknown", "MessageTypeNotSupported", "Unsupported message type", {}]

    def http_error(self, status: int, message: str, headers: dict[str, str] | None = None) -> None:
        reason = {
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found",
            405: "Method Not Allowed",
        }.get(status, "Error")
        body = f"{status} {reason}: {message}\n".encode("utf-8")
        response_headers = [
            f"HTTP/1.1 {status} {reason}",
            "Content-Type: text/plain; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Connection: close",
        ]
        for key, value in (headers or {}).items():
            response_headers.append(f"{key}: {value}")
        response = "\r\n".join(response_headers).encode("ascii") + b"\r\n\r\n" + body
        self.request.sendall(response)


class ThreadedOcppServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False


class ServerUiHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/state":
            self.send_json(CENTRAL_SYSTEM.snapshot())
            return
        if path == "/fer_white_logo.png":
            self.send_png(FER_LOGO)
            return
        if path not in ("/", "/index.html"):
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
        if not SERVER_UI_HTML.is_file():
            raise FileNotFoundError(f"Missing server UI file: {SERVER_UI_HTML}")
        return SERVER_UI_HTML.read_bytes()

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

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        try:
            payload = self.read_json()
            if path == "/api/remote-start":
                charger_id = str(payload["chargerId"])
                connector_id = int(payload.get("connectorId") or 1)
                id_tag = str(payload["idTag"])
                unique_id = CENTRAL_SYSTEM.remote_start_transaction(charger_id, connector_id, id_tag)
                self.send_json({"ok": bool(unique_id), "uniqueId": unique_id})
                return
            if path == "/api/remote-stop":
                charger_id = str(payload["chargerId"])
                transaction_id = payload.get("transactionId")
                transaction = int(transaction_id) if transaction_id not in (None, "") else None
                unique_id = CENTRAL_SYSTEM.remote_stop_transaction(charger_id, transaction)
                self.send_json({"ok": bool(unique_id), "uniqueId": unique_id})
                return
            self.send_error(404)
        except Exception as exc:
            body = str(exc).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON payload must be an object")
        return data

    def send_json(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return


class ThreadedUiServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False


def command_loop() -> None:
    print("Commands: help | list | remote-start <chargerId> <connectorId> <idTag> | remote-stop <chargerId> [transactionId]")
    while True:
        try:
            command = input("ocpp> ").strip()
        except EOFError:
            return
        except KeyboardInterrupt:
            return
        if not command:
            continue
        parts = command.split()
        name = parts[0].lower()
        if name == "help":
            print("Commands:")
            print("  list")
            print("  remote-start <chargerId> <connectorId> <idTag>")
            print("  remote-stop <chargerId> [transactionId]")
            continue
        if name == "list":
            chargers = CENTRAL_SYSTEM.list_chargers()
            print("Connected chargers: " + (", ".join(chargers) if chargers else "none"))
            continue
        if name == "remote-start":
            if len(parts) != 4:
                print("Usage: remote-start <chargerId> <connectorId> <idTag>")
                continue
            charger_id, connector_text, id_tag = parts[1], parts[2], parts[3]
            try:
                connector_id = int(connector_text)
            except ValueError:
                print("connectorId must be a number")
                continue
            unique_id = CENTRAL_SYSTEM.remote_start_transaction(charger_id, connector_id, id_tag)
            if unique_id:
                print(f"RemoteStartTransaction sent with uniqueId {unique_id}")
            else:
                print("RemoteStartTransaction was not sent")
            continue
        if name == "remote-stop":
            if len(parts) not in (2, 3):
                print("Usage: remote-stop <chargerId> [transactionId]")
                continue
            charger_id = parts[1]
            transaction_id = None
            if len(parts) == 3:
                try:
                    transaction_id = int(parts[2])
                except ValueError:
                    print("transactionId must be a number")
                    continue
            unique_id = CENTRAL_SYSTEM.remote_stop_transaction(charger_id, transaction_id)
            if unique_id:
                print(f"RemoteStopTransaction sent with uniqueId {unique_id}")
            else:
                print("RemoteStopTransaction was not sent")
            continue
        print(f"Unknown command: {parts[0]}")


def run_ui_server(host: str, port: int) -> None:
    with ThreadedUiServer((host, port), ServerUiHandler) as server:
        actual_host, actual_port = server.server_address
        log_line("server.log", f"OCPP server UI listening on http://{actual_host}:{actual_port}/")
        server.serve_forever()


def serve(host: str, port: int, ui_host: str, ui_port: int) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    with ThreadedOcppServer((host, port), OcppWebSocketHandler) as server:
        actual_host, actual_port = server.server_address
        log_line("server.log", f"OCPP 1.6 server listening on ws://{actual_host}:{actual_port}/OCPP/<chargerId>")
        threading.Thread(target=run_ui_server, args=(ui_host, ui_port), daemon=True).start()
        print("Press Ctrl+C to stop.")
        threading.Thread(target=command_loop, daemon=True).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping OCPP server.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a minimal OCPP-J 1.6 Central System WebSocket server.")
    parser.add_argument("--host", default="127.0.0.1", help="Host/interface to bind.")
    parser.add_argument("--port", type=int, default=3000, help="Port to bind.")
    parser.add_argument("--ui-host", default="127.0.0.1", help="UI host/interface to bind.")
    parser.add_argument("--ui-port", type=int, default=3001, help="UI port to bind.")
    args = parser.parse_args()
    serve(args.host, args.port, args.ui_host, args.ui_port)


if __name__ == "__main__":
    main()
