# Binance Agent OS Mini Hackathon — Track A submission

**Project:** Safe Desk Agent  
**Track:** A — Build an AI agent with Agent OS  
**Deadline:** 8 September 2026, 23:59 UTC  
**Prize pool (track):** 20,000 USDC (part of a 60,000 USDC event; confirm on the official post)

This file is the how-to-enter sheet. Official links win if anything here drifts.

## Official links

| What | URL |
|---|---|
| Agent OS | https://www.binance.com/en/agent-os |
| MCP docs | https://developers.binance.com/en/docs/agent-native/mcp-server |
| MCP endpoint | https://agent.binance.com/mcp/agentic |
| Announcement to repost | https://x.com/binance/status/2094810011557838988 |
| Entry survey | https://www.binance.com/en/survey/2913aa200aac462c89a737779393f3d4 |
| Binance on X | https://x.com/binance |

## How to enter

1. **Follow** [@Binance](https://x.com/binance) on X.
2. **Repost** the announcement: https://x.com/binance/status/2094810011557838988
3. **Reply or quote** that post with:
   - a short **demo video** (60–90 seconds is enough; see [demo-script.md](demo-script.md))
   - the **GitHub URL** of this repo (after you click **Create repo** if this is still a local/cloud project)
4. **Complete** the survey: https://www.binance.com/en/survey/2913aa200aac462c89a737779393f3d4
5. Finish before **8 Sep 2026 23:59 UTC**.

## What judges should see in the video

Keep it honest. Do not show invented live PnL.

1. README + safety model (5–10s).
2. MCP connected to `https://agent.binance.com/mcp/agentic`.
3. `balance` or `price BTCUSDT` via MCP (or a clearly labeled dry-run if auth is not available on camera).
4. `analyze BTCUSDT` → ticket with 1% risk, SL/TP.
5. Agent **waits**. You type `OK TKT-…`. Dry-run simulates, does not brag about profit.
6. You ask to withdraw. Agent **refuses**.

## Restricted participation

Not available in the **United States, United Kingdom, EEA, Hong Kong, Singapore**, plus any market on Binance’s prohibited list. This is not an invitation to trade if you are ineligible. Check Binance terms yourself.

## Track A vs Track B

| | Track A (this project) | Track B |
|---|---|---|
| Ask | Build an **AI agent** on Agent OS | Connect MCPs / market-data + trading workflows |
| Safe Desk | Prompt/skill + safety loop + helper + docs | We do **not** submit here |

Do not also claim Track B unless you build a separate integration story.

## Submission checklist

- [ ] Repo is public (or the URL you put on X resolves)
- [ ] README in English: what it is, MCP connect, 60–90s demo, safety, disclaimer
- [ ] System prompt / skill committed (`prompts/`, `skills/`)
- [ ] Demo video recorded from [demo-script.md](demo-script.md)
- [ ] Follow + repost + reply/quote with video + GitHub
- [ ] Survey submitted
- [ ] No fake live PnL in the video or README
- [ ] No Polymarket / off-venue claims
- [ ] You are outside restricted regions

## Suggested X reply (edit the URL)

```
Track A — Safe Desk Agent

Risk-first Binance Agent OS copilot.
Agentic subaccount only. No withdrawals. Human OK before any order. Dry-run by default.

GitHub: <your-repo-url>
Demo: <video>
```

## Disclaimer

Unofficial community project. Not affiliated with or endorsed by Binance. Not financial advice. Not an offer of securities or an invitation to trade in restricted jurisdictions.
