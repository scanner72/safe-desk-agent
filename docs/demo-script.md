# 60–90 second demo script

Speak this while screen-recording. Numbers match [demo/](../demo/) and `examples/btc-ohlcv.csv` so you can rehearse offline. Shot list: [demo/WALKTHROUGH.md](../demo/WALKTHROUGH.md). If MCP auth works on camera, replace the helper printout with a real `price` / `balance` tool result. Do **not** invent PnL.

**Video URL placeholder (paste after upload):** `https://x.com/REPLACE_ME` or YouTube unlisted.

## Setup

1. Claude Code, Cursor, ChatGPT, or Codex with [`prompts/SYSTEM.md`](../prompts/SYSTEM.md) loaded.
2. MCP added: `https://agent.binance.com/mcp/agentic`.
3. Terminal ready with the exact offline commands:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT
python -m safe_desk proof examples/btc-ohlcv.csv --symbol BTCUSDT --side BUY
python -m safe_desk policy check --symbol BTCUSDT --side BUY --notional 455 --risk-pct 1 --intent ticket
python -m safe_desk size --equity 1000 --entry 102450 --stop 100200
python -m safe_desk ticket --symbol BTCUSDT --side BUY --equity 1000 \
  --entry 102450 --stop 100200 --tp 106950 \
  --proof-csv examples/btc-ohlcv.csv
```

4. Dry-run stays on. Do not enable live on camera unless you intend a tiny real order.

**Optional (preferred for a normal trader):** start the local UI instead of the terminal.

```bash
python -m safe_desk.web
```

Open `http://127.0.0.1:8765`. Walk Dashboard → Analyze (sample CSV) → Ticket (`ok` fails, `OK TKT-…` writes a **PAPER** fill) → Paper journal → Alerts (withdraw refused). Say out loud that the journal is **SIMULATED / PAPER**, not live PnL. Transcript: [demo/09-web-ui.md](../demo/09-web-ui.md).

## Voice-over (copy this, ~60–75 seconds)

Safe Desk is a Track A agent for Binance Agent OS. It turns Claude or Cursor into a risk-first copilot on the official MCP.

Connect is one URL: agent.binance.com/mcp/agentic. I log in in the browser. I fund the Agentic subaccount myself — the agent cannot pull from main and cannot withdraw.

Price and analyze are reads: SMA 20 and 50, ATR, a 0 to 100 risk score. A BUY here is a setup label, not an order.

Before a ticket, two extra gates: a leakage-safe analog proof, and a desk policy — allowlist, one percent risk, no withdrawals. Then the agent writes the ticket and waits. A bare “ok” is rejected. I have to send OK plus the ticket id.

We are in dry-run, so it prints the exact MCP payload and does not place. No live PnL on this tape.

If I ask to withdraw, it refuses. That is the product: a copilot that can see the book and still waits for a human.

## On-screen actions (60–90 seconds)

| Time | Type / show |
|---|---|
| 0:00 | Web UI dashboard **or** README + MCP URL |
| 0:08 | Analyze sample — plain-language why ENTER/WAIT/SKIP |
| 0:22 | Create ticket; type `ok` (rejected) then `OK TKT-…` |
| 0:40 | Paper journal: **SIMULATED / PAPER** running PnL |
| 0:55 | Alerts: withdraw refused |
| 1:10 | Optional CLI / agent chat |
| 1:25 | Disclaimer: SIMULATED, not live PnL |

## If MCP auth fails

Say: “MCP login is blocked on this machine; analyze and ticket are from the local helper. The place path is still official Binance MCP after OK.” Cut to `demo/04-propose-trade.md` and `demo/06-refusal-withdrawal.md`. Do not fake a fill.

## Do not film

- A profit chart you did not trade
- Main-account withdrawal screens
- Polymarket or another venue
- `ENABLE LIVE` plus a large market order
