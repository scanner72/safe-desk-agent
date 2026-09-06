# Sample OHLCV

`btc-ohlcv.csv` is **synthetic** daily data for offline rehearsal of `python -m safe_desk analyze`.

It is not a Binance dump and not a live chart. Do not treat helper output as a live signal.

Columns: `date,open,high,low,close,volume`

Replay (no secrets):

```bash
python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT
```

Expected last close is `102450` on `2026-09-04`. Full printout: [demo/07-cli-offline.md](../demo/07-cli-offline.md).
