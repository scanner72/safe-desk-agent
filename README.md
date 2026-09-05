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
