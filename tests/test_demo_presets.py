"""Demo preset handlers — judge one-click paths. Dry-run only, no live orders."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from safe_desk.desk import (
    DEMO_RISK_BREACH_PCT,
    Desk,
    PRESET_IDEAL,
    PRESET_RISK_BREACH,
    PRESET_WITHDRAW,
)
from safe_desk.web.app import create_app

ROOT = Path(__file__).resolve().parents[1]


def _client(tmp_path: Path) -> TestClient:
    app = create_app(root=ROOT, log_dir=tmp_path)
    return TestClient(app)


def test_preset_catalog_and_ui_copy(tmp_path: Path):
    client = _client(tmp_path)
    home = client.get("/")
    assert home.status_code == 200
    assert "Ideal setup (Approved path)" in home.text
    assert "Risk breach (Blocked by Policy)" in home.text
    assert "Withdraw attempt (Forbidden)" in home.text
    catalog = client.get("/api/demo/presets").json()
    names = [row["name"] for row in catalog["presets"]]
    assert names == [PRESET_IDEAL, PRESET_RISK_BREACH, PRESET_WITHDRAW]
    assert catalog["dry_run"] is True
    assert catalog["live_trading"] is False
    assert catalog["secrets_stored"] is False


def test_ideal_preset_awaits_ok_and_is_not_an_order(tmp_path: Path):
    client = _client(tmp_path)
    res = client.post("/api/demo/preset", json={"name": "ideal", "lang": "en"})
    assert res.status_code == 200
    body = res.json()
    assert body["preset"] == PRESET_IDEAL
    assert body["dry_run"] is True
    assert body["blocked"] is False
    assert body["panel"] == "ticket"
    assert body["ticket_status"] == "awaiting_approval"
    ticket = body["ticket"]["ticket"]
    assert ticket["mode"] == "dry-run"
    assert ticket["status"] == "awaiting_approval"
    assert ticket["symbol"] == "BTCUSDT"
    assert ticket["side"] == "BUY"
    assert ticket["risk_pct"] == 1.0
    assert body["ok_phrase"] == f"OK {ticket['id']}"
    assert body["analyze"]["setup"]["signal"] == "BUY"
    assert body["analyze"]["why"]["action"] == "ENTER"
    assert body["analyze"]["policy"]["ok"] is True
    assert "not an order" in body["message"].lower()

    tid = ticket["id"]
    bare = client.post("/api/ticket/approve", json={"phrase": "ok", "ticket_id": tid})
    assert bare.status_code == 400
    ok = client.post("/api/ticket/approve", json={"phrase": f"OK {tid}", "ticket_id": tid})
    assert ok.status_code == 200
    assert ok.json()["simulated"]["status"] == "simulated"
    assert ok.json()["simulated"]["label"] == "SIMULATED / PAPER"


def test_risk_breach_preset_is_policy_blocked(tmp_path: Path):
    client = _client(tmp_path)
    res = client.post("/api/demo/preset", json={"name": "risk_breach"})
    assert res.status_code == 200
    body = res.json()
    assert body["preset"] == PRESET_RISK_BREACH
    assert body["blocked"] is True
    assert body["ticket_status"] == "blocked"
    ticket = body["ticket"]["ticket"]
    assert ticket["status"] == "blocked"
    reasons = " ".join(body["blocked_reasons"])
    assert "RISK_CAP" in reasons
    assert str(DEMO_RISK_BREACH_PCT).rstrip("0").rstrip(".") in reasons or "2%" in reasons
    assert ticket["policy"]["ok"] is False
    assert any(v["code"] == "RISK_CAP" for v in ticket["policy"]["violations"])
    assert body["analyze"]["policy"]["ok"] is False
    assert body["analyze"]["why"]["action"] == "SKIP"

    alerts = client.get("/api/alerts").json()["alerts"]
    assert any(a["kind"] == "POLICY_BLOCKED" for a in alerts)

    blocked = client.post(
        "/api/ticket/approve",
        json={"phrase": body["ok_phrase"], "ticket_id": ticket["id"]},
    )
    assert blocked.status_code == 400
    assert "blocked" in blocked.json()["message"].lower()


def test_withdraw_preset_refuses_and_alerts(tmp_path: Path):
    client = _client(tmp_path)
    res = client.post("/api/demo/preset", json={"name": "withdraw"})
    assert res.status_code == 200
    body = res.json()
    assert body["preset"] == PRESET_WITHDRAW
    assert body["refused"] is True
    assert body["withdraw"]["refused"] is True
    assert body["withdraw"]["policy"]["ok"] is False
    assert any(v["code"] == "FORBIDDEN_INTENT" for v in body["withdraw"]["policy"]["violations"])
    assert "never withdraw" in body["message"].lower()
    kinds = [a["kind"] for a in body["alerts"]]
    assert "WITHDRAW_REFUSED" in kinds
    alerts = client.get("/api/alerts").json()
    assert any(a["kind"] == "WITHDRAW_REFUSED" for a in alerts["alerts"])


def test_unknown_preset_is_400(tmp_path: Path):
    client = _client(tmp_path)
    res = client.post("/api/demo/preset", json={"name": "rsi-multitf"})
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "unknown preset" in detail.lower()


def test_desk_preset_aliases(tmp_path: Path):
    desk = Desk(root=ROOT, log_dir=tmp_path)
    approved = desk.run_preset("approved path")
    assert approved["preset"] == PRESET_IDEAL
    blocked = desk.run_preset("Blocked by Policy")
    assert blocked["preset"] == PRESET_RISK_BREACH
    forbidden = desk.run_preset("forbidden")
    assert forbidden["preset"] == PRESET_WITHDRAW
    with pytest.raises(ValueError, match="unknown preset"):
        desk.run_preset("tradingview")
