# SIMULATED — proof + policy gates

**Mode:** dry-run  
**Data:** `examples/btc-ohlcv.csv` (synthetic) + `config/policy.example.yaml`  
**Note:** Not a live backtest and not a win-rate claim. The analog check is leakage-safe: it only scores *past* windows that already have a known forward return.

## User

proof BTCUSDT buy

## Agent

```
python -m safe_desk proof examples/btc-ohlcv.csv --symbol BTCUSDT --side BUY
```

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

Analogs lean BUY: hit rate 100%, median forward +0.17%. Setup only — not an order.
```

This is a **gate**, not an order, and not a live win rate. The sample CSV is a synthetic uptrend, so nearby windows also printed small positive forwards. `WAIT` would block a *live* ticket; dry-run may still draft with a WARNING. `REJECT` plus `--require-proof` blocks even dry-run.

## User

policy check this 1% BTCUSDT ticket, notional about 455

## Agent

```
python -m safe_desk policy check \
  --symbol BTCUSDT --side BUY --notional 455 --risk-pct 1 --intent ticket
```

```
Policy engine  |  ticket
────────────────────────────────────────────────
Result          PASS
Config          config/policy.example.yaml
Emergency       False
Symbol          BTCUSDT
Notional        455.0000
Risk %          1
```

PASS — a ticket may be drafted at `AWAITING_APPROVAL`. It still waits for `OK TKT-…`.

## User

policy check withdraw 50 USDT

## Agent

```
python -m safe_desk policy check --intent withdraw
```

**FAIL.** Intent `withdraw` is always refused. I will not call an MCP tool.

---

Next in the rehearsal: [04-propose-trade.md](04-propose-trade.md) → [05-approval-dry-run.md](05-approval-dry-run.md) → [06-refusal-withdrawal.md](06-refusal-withdrawal.md).
