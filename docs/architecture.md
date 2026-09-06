# Architecture

Safe Desk is a **policy layer** around the official Binance MCP. The LLM stays in Claude, ChatGPT, Cursor, or Codex. Binance hosts the MCP. This repo ships the behavior (prompts / skill) and a secret-less sizing helper.

```
┌─────────────────────────────────────────────┐
│  Human                                      │
│  fund Agentic box · say OK TKT-… · revoke   │
│  or open http://127.0.0.1:8765 (local UI)   │
└────────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│  Local web UI  (`python -m safe_desk.web`)  │
│  and/or MCP client (Claude / Cursor / …)    │
│  + Safe Desk skill / system prompt          │
│  + optional `python -m safe_desk` CLI       │
└────────────────┬─────────────────────────────┘
                │ Streamable HTTP
                ▼
┌─────────────────────────────────────────────┐
│  https://agent.binance.com/mcp/agentic      │
│  scopes: market · account · trade · xfer    │
│  no withdrawal scope                        │
└────────────────┬─────────────────────────────┘
                ▼
┌─────────────────────────────────────────────┐
│  Agentic virtual subaccount                 │
│  prepaid balance is the loss cap            │
└─────────────────────────────────────────────┘
```

## Trust boundaries

| Layer | Sees | Cannot see |
|---|---|---|
| LLM client | Prompt, skill, your files, MCP tool results | Binance custody |
| Safe Desk prompts | Whatever you paste into the client | Nothing by itself — they are text |
| `safe_desk` Python | Local CSV / numbers you pass | Exchange, wallet, secrets |
| Binance MCP | Auth session, granted scopes, **orders** | The system prompt and chain-of-thought |

Binance has said it can monitor resulting trades and cannot see agent reasoning. Plan for prompt injection: keep the Agentic box small.

## Data flow for one idea

1. **Read** — live path: MCP market data + Account at `https://agent.binance.com/mcp/agentic`. Offline path: local CSV + stated equity. The helper can format MCP-shaped JSON (`safe_desk.mcp_input`) but never calls Binance REST.
2. **Score** — SMA20/SMA50, ATR, risk score. Helper optional but reproducible.
3. **Proof** — leakage-safe analog windows on OHLCV (median forward return / hit rate → APPROVE, WAIT, REJECT).
4. **Policy** — allowlist, max notional, 1% risk, daily caps, emergency stop. Withdrawals always fail. Fail → ticket `BLOCKED`.
5. **Why** — 2–4 plain sentences (ENTER / WAIT / SKIP) a non-trader can read. Not an order.
6. **Ticket** — qty from `1% equity / stop distance`. Status `awaiting_approval` only if gates pass. Append `logs/proposals.jsonl`.
7. **Gate** — no Trade tool until `OK TKT-…` (web Approve button stays disabled until that phrase is typed).
8. **Act** — dry-run: simulated payload + **PAPER** journal line (`logs/paper_journal.jsonl`). Live (MCP client only): one MCP place, then status read-back. The local UI stays dry-run.
9. **Alerts** — proof REJECT, policy BLOCKED, withdraw refused, daily cap → `logs/alerts.jsonl`.

## Why there is no trading SDK here

Track A is "build an AI agent with Agent OS". Execution belongs to the [official MCP](https://developers.binance.com/en/docs/agent-native/mcp-server). Shipping API keys or a shadow REST client would fight the safety story (no secrets, Agentic-only, human OK).

Core math stays stdlib (indicators, sizing, MCP-shaped JSON, analog proof, YAML/JSON policy, why-entry, ticket JSON, paper journal, alerts). The optional local UI is FastAPI + static HTML (no login, no secrets). JSON keys stay English.

## Defaults

| Knob | Value | Why |
|---|---|---|
| Mode | dry-run | Hosted MCP can be live the moment Trade is granted |
| Risk | 1% Agentic equity | Desk-level max-loss *per ticket* (box can still be emptied over many tickets) |
| Product | SPOT | Futures can liquidate the prepaid card without a withdrawal |
| Approval | ticket id required | Stops "ok" on the wrong dialog |
| Venue | Agentic subaccount | Main book is read-only at most |

## Files

```
prompts/SYSTEM.md     canonical agent behavior
prompts/SAFETY.md     exchange + desk controls
prompts/COMMANDS.md   intents
prompts/TICKET.md     ticket / log schema
skills/…/SKILL.md     portable skill
src/safe_desk/                 local math (SMA, ATR, 1% sizing, proof, policy, why, tickets)
src/safe_desk/web/             local trader UI
config/policy.example.yaml     desk policy example (no secrets)
prompts/LIVE_VS_OFFLINE.md     MCP live path vs CSV offline path
docs/submission.md             how to enter
docs/submission-checklist.md   day-of follow / repost / reply / survey
docs/x-submission-draft.md     ready-to-paste English X text
demo/                          labeled SIMULATED transcripts
```
