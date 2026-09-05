# SIMULATED — OK in dry-run (no live order)

**Mode:** dry-run  
**Follows:** [04-propose-trade.md](04-propose-trade.md)

## User

ok

## Agent

That is not enough. I need the ticket id so we do not approve the wrong idea.

Reply exactly:

`OK TKT-20260905-160000`

## User

OK TKT-20260905-160000

## Agent

Re-checking last (still 102,450, above stop 100,200) and Agentic equity (1,000 USDT). Risk still 10 USDT = 1%.

**DRY-RUN is on.** I will not call a Trade tool.

```
SIMULATED MCP CALL (not sent)
tool: spot.place_order          # replaced by the real name in your client
args:
  symbol: BTCUSDT
  side: BUY
  type: LIMIT
  timeInForce: GTC
  quantity: 0.004446
  price: 102450
  newClientOrderId: TKT-20260905-160000
status: simulated
```

Ticket status → `simulated`. Logged `action=simulated`.

To send this for real in a later session: `ENABLE LIVE`, then `I ACCEPT LIVE RISK`, then a **new** ticket and `OK TKT-…`.  
This transcript is not a fill and not PnL.
