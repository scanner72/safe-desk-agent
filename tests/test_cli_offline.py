"""Lock the README / demo CLI path to the sample CSV. No network."""

from pathlib import Path

from safe_desk.cli import main
from safe_desk.indicators import atr, sma_last
from safe_desk.ohlcv import load_ohlcv
from safe_desk.position_sizing import size_spot
from safe_desk.risk import evaluate_setup
from safe_desk.ticket import build_ticket

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "examples" / "btc-ohlcv.csv"


def test_sample_csv_analyze_matches_demo(capsys):
    assert main(["analyze", str(CSV), "--symbol", "BTCUSDT"]) == 0
    out = capsys.readouterr().out
    assert "Safe Desk  |  DRY-RUN  |  BTCUSDT" in out
    assert "102,450.00" in out
    assert "101,528.94" in out
    assert "99,890.87" in out
    assert "702.1791" in out
    assert "(0.69%)" in out
    assert "BULL" in out
    assert "LOW" in out
    assert "20 / 100" in out
    assert "BUY  (setup only — not an order)" in out
    assert "Why (plain language)" in out
    assert "Why ENTER" in out
    assert "No MCP call was made" in out


def test_analyze_live_overlay_keeps_offline_honesty(capsys):
    rc = main(
        [
            "analyze",
            str(CSV),
            "--symbol",
            "BTCUSDT",
            "--price-json",
            str(ROOT / "examples" / "mcp-price.json"),
            "--balance-json",
            str(ROOT / "examples" / "mcp-balance.json"),
            "--stop",
            "100200",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "102,450.00" in out
    assert "BUY  (setup only — not an order)" in out
    assert "No MCP call was made" in out
    assert "MCP-shaped JSON" in out
    assert "Illustrative size" in out


def test_readme_size_and_ticket_commands(capsys, tmp_path: Path):
    assert main(["size", "--equity", "1000", "--entry", "102450", "--stop", "100200"]) == 0
    size_out = capsys.readouterr().out
    assert "DRY-RUN" in size_out
    assert "0.00444444" in size_out
    assert "455.3333" in size_out
    assert "1%" in size_out

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
            "100200",
            "--tp",
            "106950",
            "--rationale",
            "Daily SMA stack BULL, ATR LOW, stop ~3.2x ATR",
            "--log",
            str(log),
        ]
    )
    assert rc == 0
    ticket_out = capsys.readouterr().out
    assert "AWAITING_APPROVAL" in ticket_out
    assert "DRY-RUN" in ticket_out
    assert "0.00444444" in ticket_out
    assert "2.00" in ticket_out
    assert "OK TKT-" in ticket_out
    assert "none until the user says OK" in ticket_out
    assert log.exists()
    assert "proposed" in log.read_text(encoding="utf-8")


def test_sample_csv_locked_math():
    bars = load_ohlcv(CSV)
    assert len(bars) == 80
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    last = closes[-1]
    assert last == 102_450.0
    fast = sma_last(closes, 20)
    slow = sma_last(closes, 50)
    atr_value = atr(highs, lows, closes, 14)
    assert fast is not None and slow is not None and atr_value is not None
    assert round(fast, 2) == 101_528.94
    assert round(slow, 2) == 99_890.87
    report = evaluate_setup(
        last=last,
        sma_fast=fast,
        sma_slow=slow,
        atr_value=atr_value,
        realized_vol_value=None,
        side="BUY",
    )
    assert report.trend == "BULL"
    assert report.vol_regime == "LOW"
    assert report.signal == "BUY"
    assert report.risk_score == 20

    sized = size_spot(1_000, 102_450, 100_200, 1.0)
    assert sized.quantity == 10.0 / 2_250.0
    assert sized.notional == sized.quantity * 102_450.0
    ticket = build_ticket(
        symbol="BTCUSDT",
        side="BUY",
        entry=102_450,
        stop=100_200,
        equity=1_000,
        take_profit=106_950,
    )
    assert ticket.mode == "dry-run"
    assert ticket.status == "awaiting_approval"
    assert ticket.reward_risk == 2.0
    assert ticket.mcp_action.startswith("none")
