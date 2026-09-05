# Safe Desk Agent

**Risk-first trading copilot for [Binance Agent OS](https://www.binance.com/en/agent-os).**  
Track A — Mini Hackathon (deadline **8 Sep 2026 23:59 UTC**).

Safe Desk turns any MCP-compatible LLM (Claude, ChatGPT, Cursor, Codex) into a desk clerk: read the Agentic subaccount, score a simple setup, write a ticket, **wait for a human OK**, then optionally place through the **official Binance MCP**.

- Venue: Agentic subaccount only
- No withdrawals, no transfer-out
- **Dry-run by default**
- **Human approval (`OK TKT-…`) before any trade**
- Max **1%** of Agentic equity per ticket
- No API secrets in this repo — MCP does market data and trading

> Not financial advice. Not a live track record. Demo numbers are labeled **SIMULATED**. This project is unofficial and not endorsed by Binance.

MCP endpoint (Streamable HTTP):

```
https://agent.binance.com/mcp/agentic
```

Docs: [MCP server](https://developers.binance.com/en/docs/agent-native/mcp-server) · [Agent OS](https://www.binance.com/en/agent-os)

---

## Connect Binance MCP

### Claude Code

```bash
claude mcp add binance-mcp-server --transport http https://agent.binance.com/mcp/agentic
```

Then complete the browser login and grant scopes. Start with **Market data** + **Account**. Add **Trade** only when you are ready to leave dry-run.

### Cursor / ChatGPT / Codex / other clients

Add a Streamable HTTP MCP server:

- URL: `https://agent.binance.com/mcp/agentic`
- Example file: [`config/mcp.example.json`](config/mcp.example.json)

### Fund the box

1. In Binance: Profile → Dashboard → **Sub-account** → Asset Management.
2. Transfer a **small** amount into the **Agentic** virtual subaccount (treat it as a prepaid card).
3. The agent cannot pull from main and cannot withdraw. You move leftovers back yourself.
4. Load this repo’s skill: [`prompts/SYSTEM.md`](prompts/SYSTEM.md) or [`skills/safe-desk-agent/SKILL.md`](skills/safe-desk-agent/SKILL.md).

---

## 60-second demo

Full voice-over: [docs/demo-script.md](docs/demo-script.md).

1. Show MCP connected to `agent.binance.com/mcp/agentic`.
2. `balance` — Agentic equity only.
3. `analyze BTCUSDT` — SMA20/50, ATR, risk score 0–100.
4. `propose` — ticket with size, SL/TP, **1%** risk. Agent **stops**.
5. Bare `ok` is rejected. `OK TKT-…` in **dry-run** prints a simulated MCP payload — no live fill, no PnL claim.
6. `withdraw 50 USDT` — **refused**.

Rehearse offline (synthetic CSV, not a live chart):

```bash
python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT
```

---

## Safety model

Exchange-level (Binance) and desk-level (this repo) — both required. Details: [prompts/SAFETY.md](prompts/SAFETY.md).

| Control | Default |
|---|---|
| Mode | `dry-run` every new session |
| Approval | `OK TKT-<id>` only — not a bare “ok” |
| Risk | ≤ 1% of **Agentic** equity; never auto-raise |
| Product | SPOT (futures only after an explicit ask + liquidation warning) |
| Withdraw / send-out / main sweep | Always refuse |
| Live switch | `ENABLE LIVE` then `I ACCEPT LIVE RISK` |
| Log | every proposal → `logs/proposals.jsonl` |
| Secrets | none |

The Agentic box can still go to **zero** from losing trades. A locked withdrawal door is not a max-loss formula. Fund only what you can lose.

---

## Agent commands

Natural language is fine. Canonical forms:

| Intent | Examples | Places an order? |
|---|---|---|
| Account | `balance`, `account` | No |
| Price | `price BTCUSDT` | No |
| Analyze | `analyze BTCUSDT`, `signal BTCUSDT` | No |
| Propose | `propose`, `ticket` | No — wait |
| Approve | `OK TKT-20260905-160000` | Dry-run: simulate. Live: yes |
| Cancel | `CANCEL TKT-…` | No |
| Live on | `ENABLE LIVE` then `I ACCEPT LIVE RISK` | Session flag only |
| Forbidden | `withdraw`, `send to 0x…` | **Refuse** |

---

## Python helper (optional, no secrets)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m safe_desk size --equity 1000 --entry 102450 --stop 100200
python -m safe_desk ticket --symbol BTCUSDT --side BUY --equity 1000 \
  --entry 102450 --stop 100200 --tp 106950
```

Stdlib only at runtime. MCP still does the trading.

---

## Repo map

```
prompts/SYSTEM.md          canonical agent spec
prompts/SAFETY.md          exchange + desk controls
prompts/COMMANDS.md        intents
prompts/TICKET.md          ticket template
skills/safe-desk-agent/    portable skill
src/safe_desk/             SMA, ATR, 1% sizing, tickets
docs/architecture.md
docs/submission.md         how to enter the hackathon
docs/demo-script.md        60-second voice-over
demo/                      SIMULATED transcripts (not live PnL)
```

---

## Hackathon checklist

See [docs/submission.md](docs/submission.md).

- [ ] Follow [@Binance](https://x.com/binance)
- [ ] Repost https://x.com/binance/status/2094810011557838988
- [ ] Reply/quote with **video + GitHub**
- [ ] Survey: https://www.binance.com/en/survey/2913aa200aac462c89a737779393f3d4
- [ ] Before **2026-09-08 23:59 UTC**
- [ ] Not in US, UK, EEA, HK, Singapore, or other prohibited regions

---

## Disclaimer

Crypto is volatile. You can lose the entire Agentic subaccount. Safe Desk is an unofficial community agent that uses the official Binance MCP. Binance does not endorse this project. Outputs are not advice. Demo conversations are synthetic. No live PnL is claimed.

MIT — see [LICENSE](LICENSE).
