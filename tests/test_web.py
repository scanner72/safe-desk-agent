import json
import threading
from http.server import ThreadingHTTPServer

from safe_desk.web import DeskHandler

import urllib.request


def _serve():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), DeskHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def _json(url, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if payload is not None else {},
        method="GET" if payload is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def test_health_and_analyze_and_html():
    httpd = _serve()
    try:
        host, port = httpd.server_address
        base = f"http://{host}:{port}"
        status, health = _json(f"{base}/api/health")
        assert status == 200
        assert health["mode"] == "dry-run"
        assert "agent.binance.com/mcp/agentic" in health["mcp_endpoint"]
        assert health["simulated"] is True

        page = urllib.request.urlopen(f"{base}/", timeout=5)
        html = page.read().decode("utf-8")
        assert "SAFE DESK" in html
        assert "Dry-run" in html

        _, analyze = _json(f"{base}/api/analyze", {"symbol": "BTCUSDT"})
        assert analyze["last"] == 102450.0
        assert analyze["signal"] == "BUY"
    finally:
        httpd.shutdown()
        httpd.server_close()
