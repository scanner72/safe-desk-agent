# Screen-recording walkthrough (60–90 seconds)

**SIMULATED.** This is a shot list plus a continuous chat you can read aloud. Numbers match `examples/btc-ohlcv.csv` and `python -m safe_desk`. Not live PnL.

Voice-over: [docs/demo-script.md](../docs/demo-script.md).  
Split transcripts: [01](01-account-balance.md) → [02](02-price-check.md) → [03](03-analyze-signal.md) → [04](04-propose-trade.md) → [05](05-approval-dry-run.md) → [06](06-refusal-withdrawal.md).  
Offline CLI capture: [07-cli-offline.md](07-cli-offline.md).

Keep **dry-run** on. Do not say `ENABLE LIVE` on camera unless you intend a tiny real order.

---

## Prep (off camera)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT
```

Open three panes:

1. README (this repo) with the MCP URL visible.
2. Agent chat with `prompts/SYSTEM.md` loaded. MCP = `https://agent.binance.com/mcp/agentic` if login works.
3. Terminal at the repo root (fallback if MCP auth fails).

---

## Timer

| Time | Show | Type / say |
|---|---|---|
| 0:00–0:10 | README + MCP URL | “Safe Desk. Track A. Official Binance MCP. Dry-run.” |
| 0:10–0:20 | Chat or terminal | `balance` **or** `price BTCUSDT` **or** the analyze CLI |
| 0:20–0:35 | Analyze card | `analyze BTCUSDT` — SMA20/50, ATR, risk 20/100, BUY = setup only |
| 0:35–0:50 | Ticket | `propose` → `TKT-20260905-160000` `AWAITING_APPROVAL` — agent **stops** |
| 0:50–1:10 | Gate | type `ok` (rejected) then `OK TKT-20260905-160000` → simulated payload |
| 1:10–1:25 | Refuse | `withdraw 50 USDT to my wallet` → **No** |
| 1:25–1:30 | README disclaimer | “No live PnL on this tape.” |

If you need the full 90 seconds, linger on the ticket fields (1% risk, qty `0.00444444`, R:R 2.00) and the `status: simulated` line.

---

## Continuous chat (copy into the agent, or act both sides)

**User:** `balance`

**Agent:** Agentic USDT free **1,000.00**. Mode **DRY-RUN**. I will not place.

**User:** `analyze BTCUSDT`

**Agent:** Last **102,450.00**. SMA20 **101,528.94**. SMA50 **99,890.87**. ATR 0.69% → **LOW**. Trend **BULL**. Risk **20 / 100**. Signal **BUY** (setup only — not an order).

**User:** `propose 1% risk`

**Agent:** Ticket **TKT-20260905-160000**. Status **AWAITING_APPROVAL**. Risk 10 USDT. Qty **0.00444444**. I am waiting. A bare “ok” is not enough.

**User:** `ok`

**Agent:** That is not enough. Reply `OK TKT-20260905-160000`.

**User:** `OK TKT-20260905-160000`

**Agent:** DRY-RUN. Simulated MCP payload. `status: simulated`. Not a fill. Not PnL.

**User:** `withdraw 50 USDT to my wallet`

**Agent:** **No.** I will not withdraw or transfer-out.

---

## If MCP login fails on camera

Say this once, then cut to the terminal and [07-cli-offline.md](07-cli-offline.md):

> MCP login is blocked on this machine. Analyze and ticket are from the local helper on a synthetic CSV. The place path is still official Binance MCP after `OK TKT-…`. This is not a live fill.

Do not fake an order id from the exchange.
