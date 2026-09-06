# Architecture

Safe Desk is a **policy layer** around the official Binance MCP. The LLM stays in Claude, ChatGPT, Cursor, or Codex. Binance hosts the MCP. This repo ships the behavior (prompts / skill) and a secret-less sizing helper.

```
┌─────────────────────────────────────────────┐
│  Human                                      │
│  fund Agentic box · say OK TKT-… · revoke   │
└────────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│  MCP client  (Claude / ChatGPT / Cursor /   │
│  Codex)                                     │
│  + Safe Desk skill / system prompt          │
│  + optional `python -m safe_desk`           │
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
5. **Ticket** — qty from `1% equity / stop distance`. Status `awaiting_approval` only if gates pass. Append `logs/proposals.jsonl`.
6. **Gate** — no Trade tool until `OK TKT-…`.
7. **Act** — dry-run: simulated payload. Live: one MCP place, then status read-back.

## Why there is no trading SDK here

Track A is "build an AI agent with Agent OS". Execution belongs to the [official MCP](https://developers.binance.com/en/docs/agent-native/mcp-server). Shipping API keys or a shadow REST client would fight the safety story (no secrets, Agentic-only, human OK).

The Python package is deliberately stdlib-only: indicators, sizing, MCP-shaped JSON formatting, analog proof, YAML/JSON policy, ticket JSON, and an append-only log. JSON keys stay English.

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
src/safe_desk/                 local math (SMA, ATR, 1% sizing, proof, policy, tickets)
config/policy.example.yaml     desk policy example (no secrets)
prompts/LIVE_VS_OFFLINE.md     MCP live path vs CSV offline path
docs/submission.md             how to enter
docs/submission-checklist.md   day-of follow / repost / reply / survey
docs/x-submission-draft.md     ready-to-paste English X text
demo/                          labeled SIMULATED transcripts
```
