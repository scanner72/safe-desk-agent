# SIMULATED — propose trade (wait for OK)

**Mode:** dry-run  
**Equity used:** 1,000 USDT Agentic (from demo 01)  
**Rule:** stop and wait. No MCP Trade call.

## User

propose a long, 1% risk, stop under the swing

## Agent

Using last 102,450, stop 100,200 (~3.2× ATR under the last higher low), TP 106,950 (about 2R). Risk cap stays 1%.

```
python -m safe_desk ticket \
  --symbol BTCUSDT --side BUY \
  --equity 1000 --entry 102450 --stop 100200 --tp 106950 \
  --rationale "Daily SMA stack BULL, ATR LOW, stop ~3.2x ATR"
```

```
TICKET TKT-20260905-160000
Status       AWAITING_APPROVAL
Mode         DRY-RUN
Venue        Binance Agentic subaccount only
Product      SPOT
Symbol       BTCUSDT
Side         BUY
Type         LIMIT
Entry        102,450.00
Stop loss    100,200.00
Take profit  106,950.00
Equity       1,000.00
Risk         1%  (10.00 USDT)
Quantity     0.00444444
Notional     455.3333
R:R          2.00
Rationale    Daily close holds above SMA20/SMA50. ATR% is LOW. Stop sits about 3.2× ATR under the last swing.
Invalidation Daily close below 100,200 cancels the idea — I will not trail the stop further away without a new ticket.
MCP action   none until the user says OK TKT-20260905-160000
```

Logged → `logs/proposals.jsonl` (`action=proposed`).

I am waiting. Reply `OK TKT-20260905-160000` or `CANCEL TKT-20260905-160000`.  
A bare "ok" will not place or simulate.
