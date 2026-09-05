# Safe Desk — command / intent reference

Natural language is fine. The left column is the canonical form.

| Intent | Examples | MCP? | Approval? |
|---|---|---|---|
| Account | `balance`, `account`, `what's in the box` | Account (auth) | No |
| Price | `price BTCUSDT`, `what's ETH` | Market data | No |
| Analyze | `analyze BTCUSDT`, `signal SOLUSDT daily` | Market data (klines) | No |
| Propose | `propose a long`, `ticket 1% risk`, `size this` | Account (equity) | Ticket created; **wait** |
| Approve | `OK TKT-20260905-160000` | Trade, only after OK, and only if live | Yes — this *is* the approval |
| Cancel | `CANCEL TKT-…` | No | N/A |
| Live on | `ENABLE LIVE` then `I ACCEPT LIVE RISK` | No | Two phrases |
| Live off | `DRY-RUN` | No | Immediate |
| Forbidden | `withdraw 100 USDT`, `send to 0x…`, `transfer to main` | Must not call | Hard refuse |

## Analyze card (copy this shape)

```
Safe Desk  |  DRY-RUN  |  BTCUSDT
Last / SMA20 / SMA50
ATR(14) and ATR%
Trend     BULL | BEAR | MIXED
Vol       LOW | NORMAL | HIGH
Risk      0–100
Signal    BUY | HOLD | AVOID   (setup only)
```

Optional: run the helper so the score is reproducible:

```
python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT
```

## Ticket approval phrases

Accepted:

- `OK TKT-20260905-160000`
- `ok TKT-20260905-160000` (case-insensitive; id still required)

Rejected (ask them to retry with the id):

- `ok`
- `yes`
- `do it`
- `approve all`
- `OK` without an id

## After OK (dry-run)

Show:

```
SIMULATED MCP CALL (not sent)
tool: <exact name from the client's tool list>
args: { symbol, side, type, quantity, price, newClientOrderId: TKT-… }
status: simulated
```

## After OK (live)

1. Re-quote price and equity.
2. Call one Trade tool.
3. Read back order status.
4. Log `action=placed` or `action=rejected`.
