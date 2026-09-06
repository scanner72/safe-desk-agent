from pathlib import Path

from safe_desk.cli import main
from safe_desk.policy import (
    evaluate_policy,
    hard_policy,
    load_policy,
    policy_from_dict,
    usage_from_log,
)
from safe_desk.yaml_lite import load_yaml_lite, parse_yaml_lite

ROOT = Path(__file__).resolve().parents[1]
YAML = ROOT / "config" / "policy.example.yaml"
JSON = ROOT / "config" / "policy.example.json"


def test_yaml_example_loads_and_matches_json():
    y = load_policy(YAML)
    j = load_policy(JSON)
    assert y.emergency_stop is False
    assert y.product_default == "SPOT"
    assert "BTCUSDT" in y.symbols_allowlist
    assert y.max_risk_pct == 1.0
    assert y.max_notional_quote == 5000.0
    assert y.max_loss_quote == 50.0
    assert y.symbols_allowlist == j.symbols_allowlist
    raw = load_yaml_lite(YAML)
    assert raw["symbols"]["allowlist"][0] == "BTCUSDT"


def test_config_cannot_raise_risk_above_one():
    cfg = policy_from_dict({"risk": {"max_risk_pct": 5.0}}, source="test")
    assert cfg.max_risk_pct == 1.0


def test_withdraw_always_refused():
    for intent in ("withdraw", "transfer_out", "main_to_agentic", "send out", "cash-out"):
        result = evaluate_policy(intent=intent, config=hard_policy())
        assert result.ok is False
        assert any(v.code == "FORBIDDEN_INTENT" for v in result.violations)


def test_allowlist_and_notional_and_emergency():
    cfg = load_policy(YAML)
    ok = evaluate_policy(
        intent="ticket",
        symbol="BTCUSDT",
        side="BUY",
        notional=455.0,
        risk_pct=1.0,
        config=cfg,
    )
    assert ok.ok is True

    blocked = evaluate_policy(
        intent="ticket",
        symbol="DOGEUSDT",
        side="BUY",
        notional=100.0,
        risk_pct=1.0,
        config=cfg,
    )
    assert blocked.ok is False
    assert any(v.code == "SYMBOL_NOT_ALLOWLISTED" for v in blocked.violations)

    fat = evaluate_policy(
        intent="ticket",
        symbol="BTCUSDT",
        side="BUY",
        notional=9000.0,
        risk_pct=1.0,
        config=cfg,
    )
    assert any(v.code == "MAX_NOTIONAL" for v in fat.violations)

    halt = evaluate_policy(
        intent="ticket",
        symbol="BTCUSDT",
        side="BUY",
        notional=100.0,
        risk_pct=1.0,
        config=policy_from_dict({"emergency_stop": True, "symbols": {"allowlist": ["BTCUSDT"]}}, source="halt"),
    )
    assert any(v.code == "EMERGENCY_STOP" for v in halt.violations)


def test_daily_caps_and_risk():
    cfg = load_policy(YAML)
    vol = evaluate_policy(
        intent="ticket",
        symbol="BTCUSDT",
        notional=100.0,
        risk_pct=1.0,
        daily_volume=9950.0,
        config=cfg,
    )
    assert any(v.code == "DAILY_VOLUME_CAP" for v in vol.violations)
    loss = evaluate_policy(
        intent="ticket",
        symbol="BTCUSDT",
        notional=100.0,
        risk_pct=1.0,
        daily_loss=51.0,
        config=cfg,
    )
    assert any(v.code == "DAILY_LOSS_CAP" for v in loss.violations)
    risk = evaluate_policy(
        intent="ticket",
        symbol="BTCUSDT",
        notional=100.0,
        risk_pct=2.0,
        config=cfg,
    )
    assert any(v.code == "RISK_CAP" for v in risk.violations)


def test_usage_from_log(tmp_path: Path):
    log = tmp_path / "proposals.jsonl"
    log.write_text(
        '{"ts":"2026-09-06T10:00:00+00:00","action":"simulated","notional":100,"realized_loss":5}\n'
        '{"ts":"2026-09-06T11:00:00+00:00","action":"proposed","notional":999}\n'
        '{"ts":"2026-09-05T11:00:00+00:00","action":"placed","notional":50,"realized_loss":1}\n',
        encoding="utf-8",
    )
    loss, volume = usage_from_log(log, day="2026-09-06")
    assert volume == 100.0
    assert loss == 5.0


def test_cli_policy_check_pass_and_withdraw(capsys):
    rc = main(
        [
            "policy",
            "check",
            "--symbol",
            "BTCUSDT",
            "--side",
            "BUY",
            "--notional",
            "455",
            "--risk-pct",
            "1",
            "--intent",
            "ticket",
            "--policy",
            str(YAML),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "PASS" in out
    assert "https://agent.binance.com/mcp/agentic" in out

    rc = main(["policy", "check", "--intent", "withdraw", "--no-policy"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "FAIL" in out
    assert "FORBIDDEN" in out or "always refused" in out


def test_yaml_lite_comments_and_bools():
    data = parse_yaml_lite(
        """
# comment
flag: true
empty:
nested:
  k: 2
items:
  - BTCUSDT
  - ETHUSDT
"""
    )
    assert data["flag"] is True
    assert data["nested"]["k"] == 2
    assert data["items"] == ["BTCUSDT", "ETHUSDT"]
