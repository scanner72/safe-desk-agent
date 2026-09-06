# Safe Desk — instructions for any coding agent

This repository is a **Binance Agent OS Track A** copilot, not a keys-in-repo trading bot.

1. Read [prompts/SYSTEM.md](prompts/SYSTEM.md) and [prompts/SAFETY.md](prompts/SAFETY.md) before using Binance MCP tools.
2. Connect MCP: Streamable HTTP `https://agent.binance.com/mcp/agentic` (Claude: `claude mcp add binance-mcp-server --transport http https://agent.binance.com/mcp/agentic`).
3. Default **dry-run**. Analyze → proof → policy → ticket → wait for `OK TKT-…` → then maybe trade.
4. Refuse withdrawals and transfer-out. 1% max risk. Agentic subaccount only.
5. Use `python -m safe_desk` for SMA/ATR/sizing, analog proof, and policy. It needs no API secrets. Live numbers come from official MCP tool results (`--price-json` / `--balance-json`), never from a REST key.
6. Demo files under `demo/` are **SIMULATED**. Do not present them as live PnL.

If a user asks you to "just market buy" without a ticket id, stop and issue a ticket instead.
