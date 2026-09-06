# SIMULATED — offline CLI rehearsal

**Mode:** dry-run  
**Data:** `examples/btc-ohlcv.csv` (synthetic daily bars)  
**Note:** No MCP call. No secrets. This is what you run if the camera cannot log in to Binance.

Install once:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## 1. Analyze the sample CSV

```bash
python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT
```

Expected (locked by `tests/test_cli_offline.py`):

```
Safe Desk  |  DRY-RUN  |  BTCUSDT
────────────────────────────────────────────────
Bars          80
Last          102,450.00
SMA20         101,528.94
SMA50         99,890.87
ATR(14)       702.1791  (0.69%)
Realized vol  1.8% ann.
Trend         BULL
Vol regime    LOW
Risk score    20 / 100
Signal        BUY  (setup only — not an order)

Reasons
  - Trend BULL is aligned with BUY.
  - LOW volatility (ATR 0.69% of price).
  - Signal BUY is a setup label, not an order.

No MCP call was made. Paste this into the agent, then wait for a human OK.
```

## 2. Size 1% of a 1,000 USDT Agentic box

```bash
python -m safe_desk size --equity 1000 --entry 102450 --stop 100200
```

```
Safe Desk position size  |  SPOT  |  DRY-RUN
────────────────────────────────────────────────
Equity          1,000.00
Entry           102,450.00
Stop            100,200.00
Stop distance   2,250.00  (2.20%)
Risk %          1%
Risk quote      10.0000
Quantity        0.00444444
Notional        455.3333
```

## 3. Emit a ticket (still not an order)

```bash
python -m safe_desk ticket --symbol BTCUSDT --side BUY --equity 1000 \
  --entry 102450 --stop 100200 --tp 106950 \
  --rationale "Daily SMA stack BULL, ATR LOW, stop ~3.2x ATR"
```

The helper prints `AWAITING_APPROVAL`, `DRY-RUN`, R:R `2.00`, and `Reply: OK TKT-…`.  
It appends `logs/proposals.jsonl`. It does **not** call Binance.

Frozen demo twin (same size, fixed id for the video): [tickets/TKT-20260905-160000.json](tickets/TKT-20260905-160000.json).

## 4. Proof gate (still not an order)

```bash
python -m safe_desk proof examples/btc-ohlcv.csv --symbol BTCUSDT --side BUY
```

Locked by `tests/test_proof.py` (synthetic uptrend — not a live win rate):

```
Proof gate  |  leakage-safe analogs  |  BTCUSDT
────────────────────────────────────────────────
Verdict         APPROVE
Side            BUY
Analogs         8  (k=8, window=10, horizon=5)
Median fwd      +0.17%
Hit rate        100%
Receipt         05b628112ce384a6
Leakage-safe    True
```

## 5. Policy engine

```bash
python -m safe_desk policy check --symbol BTCUSDT --side BUY --notional 455 --risk-pct 1 --intent ticket
python -m safe_desk policy check --intent withdraw
```

The ticket intent should **PASS** against `config/policy.example.yaml`. The withdraw intent should **FAIL** (always).

## 6. MCP-shaped quote (no network)

```bash
python -m safe_desk quote --price-json examples/mcp-price.json --balance-json examples/mcp-balance.json
```

Prints last **102,450.00** and Agentic equity **1,000.00** from **SIMULATED** JSON. In a live session, replace the files with a real MCP tool result from `https://agent.binance.com/mcp/agentic`. No API keys.
