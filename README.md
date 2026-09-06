# Safe Desk Agent

**Risk-first trading copilot for [Binance Agent OS](https://www.binance.com/en/agent-os).**  
Track A — Mini Hackathon (deadline **8 Sep 2026 23:59 UTC**).

Safe Desk turns any MCP-compatible LLM (Claude, ChatGPT, Cursor, Codex) into a desk clerk: read the Agentic subaccount, score a simple setup, run a leakage-safe analog **proof**, apply a desk **policy**, write a ticket, **wait for a human OK**, then optionally place through the **official Binance MCP**.

- Venue: Agentic subaccount only
- No withdrawals, no transfer-out
- **Dry-run by default**
- **Human approval (`OK TKT-…`) before any trade**
- **Proof + policy gates** before `AWAITING_APPROVAL`
- Max **1%** of Agentic equity per ticket
- No API secrets in this repo — MCP does market data and trading (no Binance REST keys)

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

## Demo

**Video (60–90s):** _paste a public X / YouTube / Drive URL here after you record_  
Script: [docs/demo-script.md](docs/demo-script.md) · Shot list: [demo/WALKTHROUGH.md](demo/WALKTHROUGH.md) · Transcripts: [demo/](demo/) (all **SIMULATED**)

Do not invent live PnL. Keep dry-run on. A bare `ok` must fail; only `OK TKT-…` continues.

### Live path vs offline path

Details: [prompts/LIVE_VS_OFFLINE.md](prompts/LIVE_VS_OFFLINE.md).

| Path | When | What you run |
|---|---|---|
| **Live** | Official MCP is connected at `https://agent.binance.com/mcp/agentic` | LLM calls price / balance / klines, then passes JSON or numbers into `safe_desk quote` / `analyze` / `ticket` (`--price-json`, `--balance-json`). No REST API keys. |
| **Offline** | Hackathon demo without auth | CSV helper below. Say the bars are **synthetic**. |

Both paths still do **proof → policy → ticket → wait for `OK TKT-…`**. Dry-run stays the default.

### Offline CLI (works without MCP)

Synthetic daily bars in `examples/btc-ohlcv.csv` — not a live chart.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT
python -m safe_desk proof examples/btc-ohlcv.csv --symbol BTCUSDT --side BUY
python -m safe_desk policy check --symbol BTCUSDT --side BUY --notional 455 --risk-pct 1 --intent ticket
python -m safe_desk quote --price-json examples/mcp-price.json --balance-json examples/mcp-balance.json
python -m safe_desk size --equity 1000 --entry 102450 --stop 100200
python -m safe_desk ticket --symbol BTCUSDT --side BUY --equity 1000 \
  --entry 102450 --stop 100200 --tp 106950 \
  --proof-csv examples/btc-ohlcv.csv
```

`analyze` should print **DRY-RUN**, last **102,450.00**, trend **BULL**, vol **LOW**, risk **20 / 100**, signal **BUY** (setup only). Full expected printout: [demo/07-cli-offline.md](demo/07-cli-offline.md). Use `python3` if `python` is missing.

`examples/mcp-*.json` are **SIMULATED** MCP-shaped payloads for rehearsal (same numbers as the CSV). In a live session, replace them with a real MCP tool result.

### 60–90s video script

Speak this (or the longer cut in [docs/demo-script.md](docs/demo-script.md)):

> Safe Desk is a Track A agent for Binance Agent OS. Official MCP only: agent.binance.com/mcp/agentic. I fund the Agentic subaccount myself — the agent cannot pull from main and cannot withdraw. Analyze is a read: SMA 20 and 50, ATR, a 0-to-100 risk score. A BUY here is a setup label, not an order. Before a ticket, an analog proof and a desk policy must pass. The agent writes a ticket at one percent of the Agentic wallet, then it waits. A bare “ok” is rejected. I send OK plus the ticket id. Dry-run prints the MCP payload and does not place. No live PnL on this tape. If I ask to withdraw, it refuses.

On-screen in the same window:

| Time | Show |
|---|---|
| 0:00 | README + MCP URL |
| 0:08 | `price BTCUSDT` / `balance` (MCP) **or** offline analyze CLI |
| 0:18 | `analyze BTCUSDT` |
| 0:28 | proof + policy (CLI or agent card) |
| 0:40 | `propose` → ticket `AWAITING_APPROVAL` |
| 0:52 | `ok` rejected, then `OK TKT-…` → `status: simulated` |
| 1:10 | `withdraw 50 USDT` → refuse |

If MCP auth fails, say so and cut to the helper. Do not fake a fill.

---

## Safety model

Exchange-level (Binance) and desk-level (this repo) — both required. Details: [prompts/SAFETY.md](prompts/SAFETY.md).

| Control | Default |
|---|---|
| Mode | `dry-run` every new session |
| Approval | `OK TKT-<id>` only — not a bare “ok” |
| Proof / policy | Analog gate + allowlist / notional / 1% / daily caps / emergency stop before a ticket |
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
| Proof | `proof BTCUSDT` | No — gate |
| Policy | `policy check` | No — fail blocks ticket |
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
python -m safe_desk proof examples/btc-ohlcv.csv --symbol BTCUSDT --side BUY
python -m safe_desk policy check --symbol BTCUSDT --side BUY --notional 455 --risk-pct 1 --intent ticket
python -m safe_desk ticket --symbol BTCUSDT --side BUY --equity 1000 \
  --entry 102450 --stop 100200 --tp 106950 \
  --proof-csv examples/btc-ohlcv.csv
```

Stdlib only at runtime. MCP still does the trading.

---

## Repo map

```
prompts/SYSTEM.md               canonical agent spec
prompts/SAFETY.md               exchange + desk controls
prompts/LIVE_VS_OFFLINE.md      MCP live path vs CSV offline path
prompts/COMMANDS.md             intents
prompts/TICKET.md               ticket template
skills/safe-desk-agent/         portable skill
src/safe_desk/                  SMA, ATR, 1% sizing, proof, policy, tickets
config/policy.example.yaml      desk policy (no secrets)
docs/architecture.md
docs/submission.md              how to enter
docs/submission-checklist.md    day-of boxes (follow / repost / reply / survey)
docs/x-submission-draft.md      ready-to-paste English X text
docs/demo-script.md             60–90s voice-over
demo/                           SIMULATED transcripts (not live PnL)
```

---

## Hackathon checklist

Day-of boxes: [docs/submission-checklist.md](docs/submission-checklist.md).  
X paste text: [docs/x-submission-draft.md](docs/x-submission-draft.md).  
Background: [docs/submission.md](docs/submission.md).

- [ ] Follow [@Binance](https://x.com/binance)
- [ ] Repost https://x.com/binance/status/2094810011557838988
- [ ] Reply/quote with **video + GitHub** (`https://github.com/scanner72/safe-desk-agent`)
- [ ] Survey: https://www.binance.com/en/survey/2913aa200aac462c89a737779393f3d4
- [ ] Before **2026-09-08 23:59 UTC**
- [ ] Not in US, UK, EEA, HK, Singapore, or other prohibited regions

---

## Disclaimer

Crypto is volatile. You can lose the entire Agentic subaccount. Safe Desk is an unofficial community agent that uses the official Binance MCP. Binance does not endorse this project. Outputs are not advice. Demo conversations are synthetic. No live PnL is claimed.

MIT — see [LICENSE](LICENSE).
