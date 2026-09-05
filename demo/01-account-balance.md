# SIMULATED — account / balance

**Mode:** dry-run  
**Client:** Claude Code + official Binance MCP  
**Note:** Figures are rehearsal data for an Agentic subaccount. Not your account. Not live PnL.

## User

balance

## Agent

I will read the **Agentic** subaccount only (Account scope). Main-account totals stay hidden unless you granted that extra read.

```
mcp.call  account.balance   # name will match your client's tool list
args      { "account": "agentic" }
```

### Agentic subaccount (SIMULATED)

| Asset | Free | Locked |
|---|---|---|
| USDT | 1,000.00 | 0.00 |
| BTC | 0.00 | 0.00 |

Open orders: none  
Positions: none (SPOT)  
Mode: **DRY-RUN** — I will not place.

Equity I will use for 1% risk: **1,000 USDT**.  
You funded this box in Sub-account Asset Management. I cannot top it up from main.

What next: `price BTCUSDT` or `analyze BTCUSDT`.
