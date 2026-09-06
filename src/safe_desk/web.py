"""Stdlib dry-run desk UI. No Flask. No API keys. No Binance REST."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from safe_desk import __version__
from safe_desk.desk import (
    DeskSession,
    handle_phrase,
    meta,
    propose_ticket,
    run_analyze,
    run_policy_gate,
    run_proof_gate,
)
from safe_desk.paths import static_dir

SESSION = DeskSession()


class DeskHandler(BaseHTTPRequestHandler):
    server_version = f"SafeDesk/{__version__}"

    def log_message(self, fmt: str, *args: object) -> None:
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._send_file("index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            name = path[len("/static/") :]
            self._send_file(name)
            return
        if path == "/api/health":
            self._json(200, {"ok": True, "mode": "dry-run", "version": __version__, **meta()})
            return
        if path == "/api/session":
            self._json(200, SESSION.snapshot())
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        body = self._read_json()
        try:
            if path == "/api/analyze":
                SESSION.last_analyze = run_analyze(
                    symbol=str(body.get("symbol") or "BTCUSDT"),
                    side=str(body.get("side") or "BUY"),
                )
                SESSION.events.append({"action": "analyze", "symbol": SESSION.last_analyze["symbol"]})
                self._json(200, SESSION.last_analyze)
                return
            if path == "/api/proof":
                SESSION.last_proof = run_proof_gate(
                    symbol=str(body.get("symbol") or "BTCUSDT"),
                    side=str(body.get("side") or "BUY"),
                )
                SESSION.events.append({"action": "proof", "verdict": SESSION.last_proof.get("verdict")})
                self._json(200, SESSION.last_proof)
                return
            if path == "/api/policy":
                SESSION.last_policy = run_policy_gate(
                    intent=str(body.get("intent") or "ticket"),
                    symbol=str(body.get("symbol") or "BTCUSDT"),
                    side=str(body.get("side") or "BUY"),
                    notional=_opt_float(body.get("notional"), 455.0),
                    risk_pct=_opt_float(body.get("risk_pct"), 1.0),
                )
                SESSION.events.append({"action": "policy", "ok": SESSION.last_policy.get("ok")})
                self._json(200, SESSION.last_policy)
                return
            if path == "/api/ticket":
                payload = propose_ticket(
                    SESSION,
                    symbol=str(body.get("symbol") or "BTCUSDT"),
                    side=str(body.get("side") or "BUY"),
                )
                self._json(200, payload)
                return
            if path == "/api/command":
                result = handle_phrase(SESSION, str(body.get("phrase") or ""))
                self._json(200, result)
                return
        except Exception as exc:  # noqa: BLE001 — surface to the desk UI
            self._json(400, {"ok": False, "error": str(exc)})
            return
        self._json(404, {"ok": False, "error": "not found"})

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        blob = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(blob)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(blob)

    def _send_file(self, name: str, content_type: str | None = None) -> None:
        if "/" in name or "\\" in name or name.startswith("."):
            self._json(404, {"ok": False, "error": "not found"})
            return
        path = static_dir() / name
        if not path.is_file():
            self._json(404, {"ok": False, "error": "not found"})
            return
        data = path.read_bytes()
        guessed, _ = mimetypes.guess_type(name)
        self.send_response(200)
        self.send_header("Content-Type", content_type or guessed or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _opt_float(value: Any, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    httpd = ThreadingHTTPServer((host, port), DeskHandler)
    print(f"Safe Desk UI  |  DRY-RUN  |  http://{host}:{port}")
    print("No API keys. No Binance REST. Official MCP after OK TKT-… only.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
