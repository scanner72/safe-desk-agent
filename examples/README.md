# Sample OHLCV

`btc-ohlcv.csv` is **synthetic** daily data for offline rehearsal of `python -m safe_desk analyze`.

It is not a Binance dump and not a live chart. Do not treat helper output as a live signal.

Columns: `date,open,high,low,close,volume`

`mcp-price.json` and `mcp-balance.json` are **SIMULATED** MCP-shaped payloads (same last / equity as the demo). They are not secrets and not a live account. In a connected session, replace them with a real tool result from `https://agent.binance.com/mcp/agentic`.

Or skip the console: `python -m safe_desk.web` and click **Use sample BTC CSV**.

Replay (no secrets):

```bash
python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT
python -m safe_desk proof examples/btc-ohlcv.csv --symbol BTCUSDT --side BUY
python -m safe_desk quote --price-json examples/mcp-price.json --balance-json examples/mcp-balance.json
```

Expected last close is `102450` on `2026-09-04`. Full printout: [demo/07-cli-offline.md](../demo/07-cli-offline.md).
