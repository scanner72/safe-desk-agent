# 60-second demo script

Speak this while screen-recording. Numbers match [demo/](../demo/) and `examples/btc-ohlcv.csv` so you can rehearse offline. If MCP auth works on camera, replace the helper printout with a real `price` / `balance` tool result. Do **not** invent PnL.

## Setup

1. Claude Code, Cursor, ChatGPT, or Codex with [`prompts/SYSTEM.md`](../prompts/SYSTEM.md) loaded.
2. MCP added: `https://agent.binance.com/mcp/agentic`.
3. Terminal ready: `python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT`
4. Dry-run stays on. Do not enable live on camera unless you intend a tiny real order.

## Voice-over (copy this, ~60 seconds)

Safe Desk is a Track A agent for Binance Agent OS. It turns Claude or Cursor into a risk-first copilot on the official MCP.

Connect is one URL: agent.binance.com/mcp/agentic. I log in in the browser. I fund the Agentic subaccount myself — the agent cannot pull from main and cannot withdraw.

Price and analyze are reads: SMA 20 and 50, ATR, a 0 to 100 risk score. A BUY here is a setup label, not an order.

The agent writes a ticket: size, stop, take-profit, one percent of the Agentic wallet — then it waits. A bare “ok” is rejected. I have to send OK plus the ticket id.

We are in dry-run, so it prints the exact MCP payload and does not place. No live PnL on this tape.

If I ask to withdraw, it refuses. That is the product: a copilot that can see the book and still waits for a human.

## On-screen actions (same 60 seconds)

| Time | Type / show |
|---|---|
| 0:00 | README + MCP URL |
| 0:10 | `price BTCUSDT` or helper analyze |
| 0:20 | `analyze BTCUSDT` |
| 0:30 | `propose 1% risk` → ticket `AWAITING_APPROVAL` |
| 0:40 | `ok` (rejected) then `OK TKT-…` (simulated) |
| 0:50 | `withdraw 50 USDT to my wallet` → refuse |

## If MCP auth fails

Say: “MCP login is blocked on this machine; analyze and ticket are from the local helper. The place path is still official Binance MCP after OK.” Cut to `demo/04-propose-trade.md` and `demo/06-refusal-withdrawal.md`. Do not fake a fill.

## Do not film

- A profit chart you did not trade
- Main-account withdrawal screens
- Polymarket or another venue
- `ENABLE LIVE` plus a large market order
