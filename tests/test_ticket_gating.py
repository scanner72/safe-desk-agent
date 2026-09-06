from pathlib import Path

from safe_desk.cli import main

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "examples" / "btc-ohlcv.csv"
POLICY = ROOT / "config" / "policy.example.yaml"
PRICE = ROOT / "examples" / "mcp-price.json"
BALANCE = ROOT / "examples" / "mcp-balance.json"


def test_ticket_policy_fail_is_blocked(capsys, tmp_path: Path):
    log = tmp_path / "proposals.jsonl"
    rc = main(
        [
            "ticket",
            "--symbol",
            "DOGEUSDT",
            "--side",
            "BUY",
            "--equity",
            "1000",
            "--entry",
            "0.20",
            "--stop",
            "0.19",
            "--policy",
            str(POLICY),
            "--log",
            str(log),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 2
    assert "Status" in out and "BLOCKED" in out
    assert "Status       AWAITING_APPROVAL" not in out
    assert "no place path" in out
    assert "SYMBOL_NOT_ALLOWLISTED" in log.read_text(encoding="utf-8") or "blocked" in log.read_text(
        encoding="utf-8"
    )


def test_ticket_live_wait_or_reject_blocks(tmp_path: Path, capsys):
    log = tmp_path / "proposals.jsonl"
    rc = main(
        [
            "ticket",
            "--symbol",
            "BTCUSDT",
            "--side",
            "SELL",
            "--equity",
            "1000",
            "--entry",
            "102450",
            "--stop",
            "104000",
            "--mode",
            "live",
            "--proof-csv",
            str(CSV),
            "--policy",
            str(POLICY),
            "--log",
            str(log),
        ]
    )
    out = capsys.readouterr().out
    # Sample tape trends up — SELL proof should be WAIT or REJECT, which blocks live.
    assert rc == 2
    assert "BLOCKED" in out


def test_ticket_dry_run_with_proof_can_still_draft(capsys, tmp_path: Path):
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
            "--proof-csv",
            str(CSV),
            "--policy",
            str(POLICY),
            "--log",
            str(log),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "AWAITING_APPROVAL" in out
    assert "Proof" in out
    assert "OK TKT-" in out
    assert "proposed" in log.read_text(encoding="utf-8")


def test_ticket_require_proof_rejects_opposing_side(capsys, tmp_path: Path):
    log = tmp_path / "proposals.jsonl"
    # Falling tape + BUY should REJECT, and --require-proof blocks even dry-run.
    falling = tmp_path / "fall.csv"
    rows = ["date,open,high,low,close,volume"]
    price = 200.0
    for i in range(60):
        price *= 0.97
        rows.append(f"2026-01-{i+1:02d},{price},{price},{price},{price},1")
    falling.write_text("\n".join(rows) + "\n", encoding="utf-8")
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
            "50",
            "--stop",
            "49",
            "--proof-csv",
            str(falling),
            "--require-proof",
            "--no-policy",
            "--log",
            str(log),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 2
    assert "BLOCKED" in out
    assert "Status       AWAITING_APPROVAL" not in out


def test_ticket_from_mcp_shaped_json(capsys, tmp_path: Path):
    log = tmp_path / "proposals.jsonl"
    rc = main(
        [
            "ticket",
            "--symbol",
            "BTCUSDT",
            "--side",
            "BUY",
            "--stop",
            "100200",
            "--tp",
            "106950",
            "--price-json",
            str(PRICE),
            "--balance-json",
            str(BALANCE),
            "--policy",
            str(POLICY),
            "--log",
            str(log),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "AWAITING_APPROVAL" in out
    assert "102,450.00" in out
    assert "0.00444444" in out
    assert "MCP-shaped JSON" in out


def test_quote_cli(capsys):
    rc = main(
        [
            "quote",
            "--price-json",
            str(PRICE),
            "--balance-json",
            str(BALANCE),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "LIVE PATH" in out
    assert "https://agent.binance.com/mcp/agentic" in out
    assert "102,450.00" in out
    assert "1,000.00" in out
    assert "no API keys" in out
