# Judge MCP checklist — Safe Desk Agent (Track A)

Prove Agent OS / MCP fit. Primary path is the **Docker UI** (~90s). Official Claude / Cursor MCP is optional and closes the Agent OS requirement.

English on camera. Keep **dry-run** on. Do **not** invent a demo video URL. Do **not** present the paper journal as live PnL.

Related: [demo-script.md](demo-script.md) · [demo/WALKTHROUGH.md](../demo/WALKTHROUGH.md) · [submission-checklist.md](submission-checklist.md)

---

## A. Docker UI (~90s) — primary path

**Prereq:** from the repo root, `docker compose up --build` → [http://localhost:8765](http://localhost:8765) (or an already running `safe-desk-ui`). No API secrets.

| # | Show | Pass if |
|---|---|---|
| 1 | **Dashboard** | Badge **DRY-RUN**. Official MCP URL `https://agent.binance.com/mcp/agentic` is visible. |
| 2 | **Analyze → Live from Binance** | **LIVE** chip, chart, and a plain-language why **ENTER / WAIT / SKIP**. Use **Offline sample (CSV)** only if the network is blocked. |
| 3 | **Ticket — wider stop, same size** | **BLOCKED** by the stop-risk brake. Use demo preset **Wide stop (Blocked by risk brake)** if present. |
| 4 | **Ideal / normal ticket** | Status **AWAITING_APPROVAL**. Use **Ideal setup (Approved path)** if present. Still not an order. |
| 5 | **Approval gate** | Bare `ok` is **rejected**. `OK TKT-…` writes a **PAPER** journal entry. |
| 6 | **Withdraw attempt** | Preset **Withdraw attempt (Forbidden)** is **refused** (alert). |
| 7 | **Say aloud** | Journal is **PAPER / SIMULATED**, not live PnL. |

Demo presets replay the locked sample CSV. Dry-run stays on. This UI never places an order.

---

## B. Official MCP + AI client — closes Agent OS requirement

Do this in Claude, Cursor, or another MCP-capable client if login works on the filming machine.

1. Add Streamable HTTP MCP from [`config/mcp.example.json`](../config/mcp.example.json) → `https://agent.binance.com/mcp/agentic`.
2. Complete browser login. Grant **Market data** + **Account**. Add **Trade** only if you are leaving dry-run (do not enable live on camera unless you intend a tiny real order).
3. Load [`prompts/SYSTEM.md`](../prompts/SYSTEM.md) or [`skills/safe-desk-agent/SKILL.md`](../skills/safe-desk-agent/SKILL.md).
4. On camera, show a **real MCP tool result** (price or Agentic balance).  
   If auth is blocked, say this line and do **not** fake a fill:  
   *UI Live is MCP-shaped public REST; the place path remains official MCP after `OK TKT-…`.*
5. Ask to withdraw / send-out. The skill **refuses**.

---

## C. Submission reminders

- Reply or quote the official announcement with the **video + GitHub**. Do not invent a demo URL.
- Survey theme: **Trading processes**.
- After you have a real public video URL, **paste it into the README** Demo section (replace the TODO). No invented URLs.
- Day-of boxes: [submission-checklist.md](submission-checklist.md). X paste text: [x-submission-draft.md](x-submission-draft.md).

Not financial advice. Unofficial community project. Not endorsed by Binance.
