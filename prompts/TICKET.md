# Ticket template

Fill every field. Leave `mcp_action` as `none` until the user sends `OK <id>`.

```text
TICKET TKT-YYYYMMDD-HHMMSS
Status       AWAITING_APPROVAL
Mode         DRY-RUN
Venue        Binance Agentic subaccount only
Product      SPOT
Symbol       BTCUSDT
Side         BUY
Type         LIMIT
Entry        100000.00
Stop loss    98000.00
Take profit  104000.00
Equity       1000.00 USDT (Agentic, not main)
Risk         1%  (10.00 USDT)
Quantity     0.005
Notional     500.00 USDT
R:R          2.00
Rationale    Daily close holds above SMA20/SMA50. ATR% is NORMAL. Stop sits ~1.1× ATR under the last swing.
Invalidation Daily close below 98000 cancels the idea — do not move the stop further away.
MCP action   none until the user says OK TKT-YYYYMMDD-HHMMSS

Notes
  - Dry-run default. This will not place until live is enabled AND OK is sent.
  - Max risk remains 1% even if the user asked for more.

Not financial advice. Crypto can go to zero inside the Agentic box.
Reply: OK TKT-YYYYMMDD-HHMMSS
Reply: CANCEL TKT-YYYYMMDD-HHMMSS
```

JSON twin (for `logs/proposals.jsonl`):

```json
{
  "ts": "2026-09-05T16:00:00+00:00",
  "action": "proposed",
  "ticket_id": "TKT-20260905-160000",
  "mode": "dry-run",
  "status": "awaiting_approval",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "entry": 100000,
  "stop_loss": 98000,
  "take_profit": 104000,
  "quantity": 0.005,
  "notional": 500,
  "risk_pct": 1.0,
  "risk_quote": 10
}
```

Helper:

```
python -m safe_desk ticket \
  --symbol BTCUSDT --side BUY \
  --equity 1000 --entry 100000 --stop 98000 --tp 104000 \
  --rationale "SMA stack + NORMAL ATR"
```
