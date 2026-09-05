from datetime import datetime, timezone
from pathlib import Path

import pytest

from safe_desk.log import append_proposal
from safe_desk.risk import evaluate_setup
from safe_desk.ticket import build_ticket


def test_bull_aligned_buy_can_signal_buy():
    report = evaluate_setup(
        last=110,
        sma_fast=105,
        sma_slow=100,
        atr_value=2.0,
        realized_vol_value=0.4,
        side="BUY",
        stop=107,
    )
    assert report.trend == "BULL"
    assert report.signal in {"BUY", "HOLD"}
    assert report.risk_score < 70


def test_high_vol_is_avoid():
    report = evaluate_setup(
        last=100,
        sma_fast=99,
        sma_slow=98,
        atr_value=8.0,  # 8% ATR
        realized_vol_value=1.2,
        side="BUY",
        stop=96,
    )
    assert report.vol_regime == "HIGH"
    assert report.signal == "AVOID"


def test_ticket_awaits_approval_and_logs(tmp_path: Path):
    when = datetime(2026, 9, 5, 16, 0, 0, tzinfo=timezone.utc)
    ticket = build_ticket(
        symbol="btcusdt",
        side="BUY",
        entry=100_000,
        stop=98_000,
        equity=1_000,
        take_profit=104_000,
        risk_pct=1.0,
        mode="dry-run",
        rationale="Demo ticket for tests.",
        when=when,
    )
    assert ticket.id == "TKT-20260905-160000"
    assert ticket.status == "awaiting_approval"
    assert ticket.mode == "dry-run"
    assert ticket.symbol == "BTCUSDT"
    assert ticket.reward_risk == pytest.approx(2.0)
    assert ticket.mcp_action.startswith("none")
    log = tmp_path / "proposals.jsonl"
    append_proposal(ticket, path=log)
    text = log.read_text(encoding="utf-8")
    assert "TKT-20260905-160000" in text
    assert "proposed" in text


def test_reward_risk_exact():
    ticket = build_ticket(
        symbol="ETHUSDT",
        side="BUY",
        entry=4000,
        stop=3900,
        take_profit=4200,
        equity=2000,
        when=datetime(2026, 9, 5, 1, 0, 0, tzinfo=timezone.utc),
    )
    assert ticket.reward_risk == 2.0
