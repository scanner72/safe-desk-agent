# Track A submission checklist

**Deadline: 8 September 2026, 23:59 UTC.**  
Miss the clock and the entry does not count.

This is the day-of sheet. Background and official links live in [submission.md](submission.md). Paste-ready X text lives in [x-submission-draft.md](x-submission-draft.md). Official posts win if anything here drifts.

Repo (must stay public): https://github.com/scanner72/safe-desk-agent

---

## 1. X account

- [ ] Follow [@Binance](https://x.com/binance)
- [ ] Confirm the follow is on the same account you will use for the reply

## 2. Repost the announcement

- [ ] Repost (retweet) this exact post: https://x.com/binance/status/2094810011557838988
- [ ] Do this **before** or **with** your reply/quote so the judges can see both

## 3. Reply or quote with GitHub + demo

Record from [demo-script.md](demo-script.md) and [demo/WALKTHROUGH.md](../demo/WALKTHROUGH.md). 60–90 seconds. No invented live PnL.

- [ ] Video file is ready (screen recording, English voice-over or on-screen English captions)
- [ ] Reply **or** quote-repost the announcement
- [ ] Attach the demo video
- [ ] Include the GitHub URL **https://github.com/scanner72/safe-desk-agent**
- [ ] Paste from [x-submission-draft.md](x-submission-draft.md) (edit only the video handle if needed)
- [ ] After posting, copy your reply URL into the survey

## 4. Survey

- [ ] Open https://www.binance.com/en/survey/2913aa200aac462c89a737779393f3d4
- [ ] Paste GitHub: `https://github.com/scanner72/safe-desk-agent`
- [ ] Paste X reply / quote URL
- [ ] Paste demo video URL if the form asks separately
- [ ] Submit **before 8 Sep 2026 23:59 UTC**

## 5. Jurisdictions (do this before you post)

Hackathon and product access are **not** available in the **United States, United Kingdom, EEA, Hong Kong, Singapore**, or any market on Binance’s [prohibited-countries list](https://www.binance.com/en/legal/list-of-prohibited-countries).

- [ ] You confirm you are **outside** those regions
- [ ] You will follow Binance eligibility rules yourself
- [ ] This repo is a research copilot. It is not an invitation to trade if you are ineligible

If you are in a restricted region: **do not submit**. Do not ask the agent to bypass geo rules.

## 6. Repo / judge pack (English)

- [ ] README Demo section is obvious (video placeholder + offline CLI)
- [ ] `prompts/SYSTEM.md` and `skills/safe-desk-agent/SKILL.md` are in the repo
- [ ] Demo transcripts under `demo/` are labeled **SIMULATED**
- [ ] No live PnL, Sharpe, or win-rate claims
- [ ] No Polymarket / off-venue claims
- [ ] Dry-run and `OK TKT-…` remain the defaults in every judge-facing sentence

## 7. Offline sanity check (no secrets, no MCP)

From a clean clone:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m safe_desk analyze examples/btc-ohlcv.csv --symbol BTCUSDT
```

- [ ] `pip install -e ".[dev]"` succeeds
- [ ] `pytest` is green
- [ ] Analyze prints `DRY-RUN`, last `102,450.00`, trend `BULL`, signal `BUY` (setup only)

## 8. After you post

- [ ] X reply is public (not protected)
- [ ] GitHub link in the reply opens this repo
- [ ] Survey confirmation saved (screenshot is enough)
- [ ] You did **not** enable live trading on camera unless you intended a tiny real order

---

Not financial advice. Unofficial community project. Not endorsed by Binance.
