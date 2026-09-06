# Live path vs offline path

Safe Desk has **two analyze paths**. Both stay dry-run by default. Both still wait for `OK TKT-…`. Neither one invents live PnL.

Official MCP (Streamable HTTP):

```
https://agent.binance.com/mcp/agentic
```

Docs: https://developers.binance.com/en/docs/agent-native/mcp-server

This helper **never** calls Binance REST with API keys. Auth is the official Agent OS MCP OAuth / browser login in the LLM client.

---

## Live path (MCP available)

Use this when Claude / Cursor / ChatGPT / Codex has the Binance MCP connected.

1. **Call MCP market + account tools** (discover names at runtime; do not invent endpoints).
   - Price / ticker for `SYMBOL`
   - Agentic subaccount balances (not the main book)
2. **Pass the numbers into Safe Desk** — either:
   - paste the tool JSON into the helper:

     ```bash
     python -m safe_desk quote \
       --price-json examples/mcp-price.json \
       --balance-json examples/mcp-balance.json

     python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT \
       --price-json /tmp/mcp-price.json \
       --balance-json /tmp/mcp-balance.json \
       --stop 100200 --with-proof

     python -m safe_desk ticket --symbol BTCUSDT --side BUY \
       --price-json /tmp/mcp-price.json \
       --balance-json /tmp/mcp-balance.json \
       --stop 100200 --tp 106950 \
       --proof-csv examples/btc-ohlcv.csv
     ```

   - or copy last / equity into the [SYSTEM.md](SYSTEM.md) ticket schema (`Equity` = Agentic free quote, `Entry` = last).
3. **Proof** on OHLCV (MCP klines saved as CSV, or the repo sample if klines are missing).
4. **Policy** (`python -m safe_desk policy check` — also runs inside `ticket`).
5. Emit a ticket. **Wait.** A bare `ok` is rejected. `OK TKT-…` then dry-run simulates.

`examples/mcp-price.json` and `examples/mcp-balance.json` are **SIMULATED** shapes for rehearsal. Replace them with a real MCP tool result in a live session.

---

## Offline path (hackathon demo without auth)

Use this when MCP login is blocked or you are rehearsing on a plane.

```bash
python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT
python -m safe_desk proof examples/btc-ohlcv.csv --symbol BTCUSDT --side BUY
python -m safe_desk policy check --symbol BTCUSDT --side BUY --notional 455 --risk-pct 1 --intent ticket
python -m safe_desk ticket --symbol BTCUSDT --side BUY --equity 1000 \
  --entry 102450 --stop 100200 --tp 106950 \
  --proof-csv examples/btc-ohlcv.csv
```

The CSV is **synthetic**. Say so. Do not present the score as a live signal or as PnL.

The place path is still the official MCP after `OK TKT-…`. Offline mode only does math.

---

## What the LLM should do

| Step | Live | Offline |
|---|---|---|
| Price / balance | Call MCP tools, then pass JSON or numbers into `safe_desk` / the ticket | Use CSV last + a stated rehearsal equity |
| Analyze | MCP klines **or** helper on CSV with `--price-json` overlay | `python -m safe_desk analyze` |
| Proof | Helper on those klines / CSV | `python -m safe_desk proof` |
| Policy | Always | Always |
| Ticket | `awaiting_approval` only if policy passes and proof does not block | Same |
| Place | Only after `OK TKT-…`. Dry-run prints the payload | Same — still no fake fill |

Withdraw / send-out / main-account pull: **refuse on both paths**.
