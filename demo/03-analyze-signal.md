# SIMULATED — analyze / signal

**Mode:** dry-run  
**Data:** `examples/btc-ohlcv.csv` (synthetic daily bars, labeled as such)  
**Helper:** `python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT`

## User

analyze BTCUSDT

## Agent

Pulling daily closes for SMA20 / SMA50 and ATR(14). If MCP klines are missing I use the local helper — same rules.

```
mcp.call  market.klines
args      { "symbol": "BTCUSDT", "interval": "1d", "limit": 80 }
```

*(In this rehearsal the kline payload is replaced by the repo CSV so anyone can reproduce the score.)*

```
Safe Desk  |  DRY-RUN  |  BTCUSDT
Bars           80
Last           102,450.00
SMA20          101,528.94
SMA50           99,890.87
ATR(14)        702.18  (0.69%)
Trend          BULL
Vol regime     LOW
Risk score     20 / 100
Signal         BUY  (setup only — not an order)
```

Reasons (from `python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT`):

- Trend BULL is aligned with BUY.
- LOW volatility (ATR 0.69% of price).
- Signal BUY is a setup label, not an order.

I am **not** sending a trade. If you want size + SL/TP against the 1,000 USDT Agentic box, say `propose`.
