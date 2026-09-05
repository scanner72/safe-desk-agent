# SIMULATED — price

**Mode:** dry-run  
**Note:** Public market data. No order.

## User

price BTCUSDT

## Agent

```
mcp.call  market.ticker
args      { "symbol": "BTCUSDT" }
```

### BTCUSDT (SIMULATED mark)

| Field | Value |
|---|---|---|
| Last | 102,450.00 |
| Bid / ask | 102,448.50 / 102,451.20 |
| 24h change | +1.8% (rehearsal) |

Source: official Binance MCP market data in a real session; this table is a demo stand-in.

No ticket opened. Say `analyze BTCUSDT` if you want SMA / ATR / risk score.
