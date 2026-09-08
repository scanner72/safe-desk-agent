from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from safe_desk.desk import Desk
from safe_desk.web.app import create_app

ROOT = Path(__file__).resolve().parents[1]


def _client(tmp_path: Path) -> TestClient:
    app = create_app(root=ROOT, log_dir=tmp_path)
    return TestClient(app)


def test_dashboard_and_health(tmp_path: Path):
    client = _client(tmp_path)
    home = client.get("/")
    assert home.status_code == 200
    assert "DRY-RUN" in home.text
    assert "PAPER" in home.text
    assert "OK TKT" in home.text
    assert "Demo presets" in home.text
    assert "Ideal setup (Approved path)" in home.text
    assert "Wide stop (Blocked by risk brake)" in home.text
    assert "t-stop-risk-warn" in home.text
    assert "A wider stop at the same size is blocked" in home.text
    assert "Live from Binance" in home.text
    assert "Offline sample (CSV)" in home.text
    assert "Use sample BTC CSV" not in home.text
    live_pos = home.text.find('id="btn-live"')
    sample_pos = home.text.find('id="btn-sample"')
    assert 0 <= live_pos < sample_pos
    assert 'class="btn primary" id="btn-live"' in home.text
    assert 'class="btn outline" id="btn-sample"' in home.text
    assert "default for judges" in home.text
    assert "fallback when there is no network" in home.text
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["mode"] == "dry-run"
    status = client.get("/api/status")
    body = status.json()
    assert body["dry_run"] is True
    assert body["live_trading"] is False
    assert body["secrets_stored"] is False
    assert "agent.binance.com/mcp/agentic" in body["mcp_url"]
    assert body["paper"]["label"] == "PAPER / SIMULATED"


def test_analyze_sample_then_ticket_ok_journal(tmp_path: Path):
    client = _client(tmp_path)
    analyzed = client.post(
        "/api/analyze",
        json={
            "use_sample": True,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "stop": 100200,
            "equity": 1000,
            "risk_pct": 1,
        },
    )
    assert analyzed.status_code == 200
    data = analyzed.json()
    assert data["setup"]["signal"] == "BUY"
    assert data["setup"]["htf_trend"] == "BULL"
    assert data["setup"]["mtf_state"] == "ALIGNED"
    assert data["setup"]["rsi_state"] == "OVERBOUGHT"
    assert data["setup"]["volume_flag"] == "NORMAL"
    assert data["why"]["action"] == "ENTER"
    assert "overbought" in " ".join(data["why"]["sentences"]).lower()
    assert "not an order" in " ".join(data["why"]["sentences"]).lower()
    assert data["size"]["quantity"] == 10.0 / 2250.0
    assert data["levels"]["k_sl"] == 1.2
    assert data["chart"]["ohlcv"]
    assert data["chart"]["levels"]["sl"] == data["levels"]["sl"]

    ticket = client.post(
        "/api/ticket",
        json={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "entry": 102450,
            "stop": 100200,
            "equity": 1000,
            "take_profit": 106950,
            "use_sample": True,
        },
    )
    assert ticket.status_code == 200
    tid = ticket.json()["ticket"]["id"]
    assert ticket.json()["ticket"]["status"] == "awaiting_approval"
    assert ticket.json()["ok_phrase"] == f"OK {tid}"

    bare = client.post("/api/ticket/approve", json={"phrase": "ok", "ticket_id": tid})
    assert bare.status_code == 400
    assert "bare" in bare.json()["message"].lower() or "OK TKT" in bare.json()["message"]

    ok = client.post("/api/ticket/approve", json={"phrase": f"OK {tid}", "ticket_id": tid})
    assert ok.status_code == 200
    assert ok.json()["simulated"]["status"] == "simulated"
    assert ok.json()["simulated"]["label"] == "SIMULATED / PAPER"
    assert ok.json()["journal"]["label"] == "PAPER"
    assert ok.json()["journal"]["kind"] == "entry"

    journal = client.get("/api/journal").json()
    assert journal["event_count"] == 1
    assert journal["open_count"] == 1
    assert "not live" in journal["note"].lower()

    closed = client.post(
        "/api/journal/close",
        json={"ticket_id": tid, "reason": "take_profit"},
    )
    assert closed.status_code == 200
    assert closed.json()["event"]["kind"] == "exit"
    assert closed.json()["paper"]["running_pnl"] > 0


def test_analyze_without_stop_sizes_from_atr(tmp_path: Path):
    client = _client(tmp_path)
    analyzed = client.post(
        "/api/analyze",
        json={
            "use_sample": True,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "equity": 1000,
            "risk_pct": 1,
        },
    )
    assert analyzed.status_code == 200
    data = analyzed.json()
    assert data["stop_source"] == "atr"
    lv = data["levels"]
    assert lv["k_sl"] == 1.2
    assert lv["k_tp1"] == 1.5
    assert lv["k_tp2"] == 2.5
    assert lv["sl"] < lv["entry"] < lv["tp1"] < lv["tp2"]
    assert data["size"]["stop"] == pytest.approx(lv["sl"])
    assert data["size"]["stop_distance"] == pytest.approx(lv["sl_distance"])
    raw_qty = 10.0 / lv["sl_distance"]
    if raw_qty * data["last"] > 1000:
        assert data["size"]["clamped_to_equity"] is True
        assert data["size"]["quantity"] == pytest.approx(1000 / data["last"])
    else:
        assert data["size"]["quantity"] == pytest.approx(raw_qty)
    assert data["chart"]["ohlcv"][0]["time"]
    assert data["suggested_tp2"] == lv["tp2"]

    ticket = client.post(
        "/api/ticket",
        json={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "entry": data["last"],
            "equity": 1000,
            "use_sample": True,
        },
    )
    assert ticket.status_code == 200
    body = ticket.json()
    assert body["ticket"]["stop_loss"] == pytest.approx(lv["sl"])
    assert body["ticket"]["take_profit"] == pytest.approx(lv["tp1"])
    assert body["ticket"]["take_profit_2"] == pytest.approx(lv["tp2"])
    assert body["ticket"]["quantity"] == pytest.approx(data["size"]["quantity"])


def test_withdraw_refused_writes_alert(tmp_path: Path):
    client = _client(tmp_path)
    client.post(
        "/api/analyze",
        json={
            "use_sample": True,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "stop": 100200,
            "equity": 1000,
        },
    )
    before = client.get("/api/status").json()
    assert before["last_policy"] is not None
    assert before["last_policy"]["ok"] is True
    refused = client.post("/api/withdraw", json={"note": "withdraw 50 USDT"})
    assert refused.status_code == 403
    assert refused.json()["refused"] is True
    alerts = client.get("/api/alerts").json()
    assert alerts["count"] >= 1
    assert any(a["kind"] == "WITHDRAW_REFUSED" for a in alerts["alerts"])
    after = client.get("/api/status").json()
    assert after["last_policy"]["ok"] is True
    assert after["last_policy"]["intent"] == "ticket"


def test_desk_approve_requires_full_phrase(tmp_path: Path):
    desk = Desk(root=ROOT, log_dir=tmp_path)
    created = desk.create_ticket(
        symbol="BTCUSDT",
        side="BUY",
        entry=102450,
        stop=100200,
        equity=1000,
        take_profit=106950,
        use_sample=True,
    )
    tid = created["ticket"]["id"]
    assert desk.approve("ok")["ok"] is False
    assert desk.approve(f"OK {tid}")["ok"] is True
    paper = desk.journal()
    assert paper["events"][0]["simulated"] is True


def test_ticket_api_blocks_wide_stop_locked_qty(tmp_path: Path):
    client = _client(tmp_path)
    sized = client.post(
        "/api/analyze",
        json={
            "use_sample": True,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "stop": 100200,
            "equity": 1000,
            "risk_pct": 1,
        },
    ).json()["size"]
    ticket = client.post(
        "/api/ticket",
        json={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "entry": 102450,
            "stop": 90000,
            "equity": 1000,
            "quantity": sized["quantity"],
            "use_sample": True,
        },
    )
    assert ticket.status_code == 200
    body = ticket.json()
    assert body["ticket"]["status"] == "blocked"
    assert any("STOP_RISK" in r for r in body["blocked_reasons"])
    assert any(v["code"] == "STOP_RISK" for v in body["ticket"]["policy"]["violations"])
