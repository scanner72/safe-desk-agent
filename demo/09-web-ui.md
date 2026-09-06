# SIMULATED — local web UI for a normal trader

**Mode:** dry-run  
**Label:** every number below is **PAPER / SIMULATED**. Not live PnL.  
**Note:** Start the UI, then stay in the browser. No MCP login required for this rehearsal.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m safe_desk.web
```

Open `http://127.0.0.1:8765`. Toggle **EN / RU** if you want Russian short labels.

## 1. Dashboard

You should see **DRY-RUN**, MCP URL `https://agent.binance.com/mcp/agentic`, emergency stop **off**, and **PAPER PnL** at 0. Secrets stored: none.

## 2. Analyze

Click **Use sample BTC CSV** (or paste `examples/btc-ohlcv.csv`). Defaults match the locked demo: last **102,450**, stop **100,200**, equity **1,000**.

Expected idea (plain language, not jargon):

- Price has been drifting up versus the two average lines.
- Similar past windows leaned the same way — a check, not a promise.
- At 1% risk, size is about **0.00444444 BTC** (worth about **455**).
- **ENTER** here is a setup label, **not an order**.

## 3. Ticket

Create the ticket. Status **AWAITING_APPROVAL**. The Approve button stays disabled until you type exactly:

```
OK TKT-…   (the id on screen)
```

A bare `ok` is rejected and writes an alert.

After a matching `OK TKT-…` the page shows a **SIMULATED / PAPER** payload. No Binance Trade tool is called.

## 4. Paper journal

An **entry** line appears. Label **PAPER**. Running PAPER PnL is still 0 until you close.

Optional: **Close paper at take-profit** (106,950) writes an **exit**. That PnL is still **SIMULATED**. Do not present it as a live track record.

## 5. Alerts

**Try withdraw** must refuse. Kind **WITHDRAW_REFUSED**. Safe Desk never sends coins out.

Proof REJECT / policy BLOCKED / daily cap also land here when those gates fire.

## Honesty line (say this on camera)

> This browser flow is a rehearsal on a synthetic CSV. The paper diary is simulated. Live orders still go only through the official Binance Agent OS MCP after a human types OK TKT-…
