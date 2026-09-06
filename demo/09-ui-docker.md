# SIMULATED — desk UI + Docker

**Mode:** dry-run  
**Note:** The UI is a local rehearsal surface. It does not place orders, does not call Binance REST, and holds no API keys.

## Without Docker

```bash
python -m safe_desk serve --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080`. Click:

1. Analyze BTCUSDT (offline CSV)
2. Run analog proof
3. Check policy
4. Propose 1% ticket → `AWAITING_APPROVAL`
5. `bare ok` → rejected
6. `OK TKT-…` → `status: simulated` payload, not a fill
7. `withdraw` → refused

## Docker

```bash
docker compose up --build
```

Same URL. Same dry-run rules. Image contains examples + policy only — no secrets.

## What you must say on camera

Numbers are **SIMULATED**. This is not live PnL. The place path is still the official MCP after a matching `OK TKT-…`.
