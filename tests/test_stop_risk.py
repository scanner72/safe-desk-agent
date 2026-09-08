"""Stop-vs-risk brake: wide stop at the same size must block; ATR/1% still passes."""

from pathlib import Path

import pytest

from safe_desk.cli import main
from safe_desk.desk import DEMO_ENTRY, DEMO_STOP, DEMO_WIDE_STOP, Desk
from safe_desk.i18n import t
from safe_desk.policy import evaluate_policy, hard_policy, load_policy
from safe_desk.position_sizing import (
    actual_risk_pct,
    capital_at_risk_quote,
    max_stop_distance,
    size_spot,
    size_spot_at_quantity,
    stop_side_ok,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config" / "policy.example.yaml"


def test_capital_at_risk_math():
    assert capital_at_risk_quote(100, 99, 10) == pytest.approx(10)
    assert actual_risk_pct(1_000, 10) == pytest.approx(1.0)
    assert max_stop_distance(1_000, 10, 1.0) == pytest.approx(1.0)
    assert stop_side_ok("BUY", 100, 99) is True
    assert stop_side_ok("BUY", 100, 101) is False
    assert stop_side_ok("SELL", 100, 101) is True
    assert stop_side_ok("SELL", 100, 99) is False
    assert stop_side_ok("BUY", 100, 100) is False


def test_size_spot_then_wider_stop_keeps_qty_and_raises_risk():
    sized = size_spot(equity=1_000, entry=102_450, stop=100_200, risk_pct=1.0)
    assert sized.actual_risk_pct == pytest.approx(1.0)
    wide = size_spot_at_quantity(
        1_000, 102_450, 90_000, sized.quantity, risk_pct=1.0
    )
    assert wide.quantity == pytest.approx(sized.quantity)
    assert wide.quantity_locked is True
    assert wide.actual_risk_pct > 1.0
    assert any("too far" in n for n in wide.notes)


def test_tighter_stop_at_locked_qty_stays_under_limit():
    sized = size_spot(equity=1_000, entry=102_450, stop=100_200, risk_pct=1.0)
    tight = size_spot_at_quantity(
        1_000, 102_450, 101_000, sized.quantity, risk_pct=1.0
    )
    assert tight.quantity == pytest.approx(sized.quantity)
    assert tight.actual_risk_pct < 1.0
    assert tight.actual_risk_pct == pytest.approx(
        actual_risk_pct(1_000, capital_at_risk_quote(102_450, 101_000, sized.quantity))
    )


def test_policy_blocks_wide_stop_same_qty():
    sized = size_spot(1_000, 102_450, 100_200, 1.0)
    blocked = evaluate_policy(
        intent="ticket",
        symbol="BTCUSDT",
        side="BUY",
        notional=sized.notional,
        risk_pct=1.0,
        entry=102_450,
        stop=90_000,
        quantity=sized.quantity,
        equity=1_000,
        config=load_policy(POLICY),
    )
    assert blocked.ok is False
    assert any(v.code == "STOP_RISK" for v in blocked.violations)
    msg = " ".join(v.message for v in blocked.violations)
    assert "too far" in msg
    assert "Tighten stop or lower size" in msg
    assert blocked.actual_risk_pct is not None
    assert blocked.actual_risk_pct > blocked.risk_limit_pct


def test_policy_passes_atr_normal_stop_at_one_percent():
    sized = size_spot(1_000, 102_450, 100_200, 1.0)
    ok = evaluate_policy(
        intent="ticket",
        symbol="BTCUSDT",
        side="BUY",
        notional=sized.notional,
        risk_pct=1.0,
        entry=102_450,
        stop=100_200,
        quantity=sized.quantity,
        equity=1_000,
        config=load_policy(POLICY),
    )
    assert ok.ok is True
    assert ok.actual_risk_pct == pytest.approx(1.0, abs=1e-6)
    assert all(v.code != "STOP_RISK" for v in ok.violations)


def test_policy_blocks_wrong_side_stop():
    buy = evaluate_policy(
        intent="ticket",
        symbol="BTCUSDT",
        side="BUY",
        risk_pct=1.0,
        entry=100,
        stop=101,
        config=hard_policy(),
    )
    assert any(v.code == "STOP_WRONG_SIDE" for v in buy.violations)
    sell = evaluate_policy(
        intent="ticket",
        symbol="BTCUSDT",
        side="SELL",
        risk_pct=1.0,
        entry=100,
        stop=99,
        config=hard_policy(),
    )
    assert any(v.code == "STOP_WRONG_SIDE" for v in sell.violations)


def test_stop_risk_message_ru():
    text = t("ru", "stop_risk_block", actual=5.53, limit=1)
    assert "5.53" in text
    assert "1" in text


def test_ticket_cli_blocks_wide_stop_locked_qty(capsys, tmp_path: Path):
    sized = size_spot(1_000, 102_450, 100_200, 1.0)
    log = tmp_path / "proposals.jsonl"
    rc = main(
        [
            "ticket",
            "--symbol",
            "BTCUSDT",
            "--side",
            "BUY",
            "--equity",
            "1000",
            "--entry",
            "102450",
            "--stop",
            "90000",
            "--quantity",
            str(sized.quantity),
            "--policy",
            str(POLICY),
            "--log",
            str(log),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 2
    assert "BLOCKED" in out
    assert "STOP_RISK" in out
    assert "too far" in out


def test_policy_cli_stop_risk_fail_and_pass(capsys):
    sized = size_spot(1_000, 102_450, 100_200, 1.0)
    fail = main(
        [
            "policy",
            "check",
            "--symbol",
            "BTCUSDT",
            "--side",
            "BUY",
            "--entry",
            "102450",
            "--stop",
            "90000",
            "--quantity",
            str(sized.quantity),
            "--equity",
            "1000",
            "--risk-pct",
            "1",
            "--intent",
            "ticket",
            "--policy",
            str(POLICY),
        ]
    )
    out = capsys.readouterr().out
    assert fail == 2
    assert "FAIL" in out
    assert "STOP_RISK" in out

    passed = main(
        [
            "policy",
            "check",
            "--symbol",
            "BTCUSDT",
            "--side",
            "BUY",
            "--entry",
            "102450",
            "--stop",
            "100200",
            "--quantity",
            str(sized.quantity),
            "--equity",
            "1000",
            "--risk-pct",
            "1",
            "--notional",
            str(sized.notional),
            "--intent",
            "ticket",
            "--policy",
            str(POLICY),
        ]
    )
    out = capsys.readouterr().out
    assert passed == 0
    assert "PASS" in out


def test_desk_create_ticket_blocks_wide_stop(tmp_path: Path):
    desk = Desk(root=ROOT, log_dir=tmp_path)
    sized = size_spot(1_000, DEMO_ENTRY, DEMO_STOP, 1.0)
    created = desk.create_ticket(
        symbol="BTCUSDT",
        side="BUY",
        entry=DEMO_ENTRY,
        stop=DEMO_WIDE_STOP,
        equity=1_000,
        quantity=sized.quantity,
        use_sample=True,
    )
    assert created["ticket"]["status"] == "blocked"
    assert any("STOP_RISK" in r for r in created["blocked_reasons"])
    assert created["ticket"]["policy"]["ok"] is False
    assert any(v["code"] == "STOP_RISK" for v in created["ticket"]["policy"]["violations"])


def test_desk_create_ticket_atr_stop_still_awaits(tmp_path: Path):
    desk = Desk(root=ROOT, log_dir=tmp_path)
    created = desk.create_ticket(
        symbol="BTCUSDT",
        side="BUY",
        entry=DEMO_ENTRY,
        stop=DEMO_STOP,
        equity=1_000,
        take_profit=106_950,
        use_sample=True,
    )
    assert created["ticket"]["status"] == "awaiting_approval"
    assert created["ticket"]["policy"]["ok"] is True
    assert created["ticket"]["policy"].get("actual_risk_pct") == pytest.approx(1.0, abs=1e-6)
