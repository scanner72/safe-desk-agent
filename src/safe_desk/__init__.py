"""Safe Desk — local risk math for a Binance Agent OS copilot.

No exchange credentials. Market data and orders go through the official
Binance MCP after a human approval. This package sizes tickets, scores
simple setups, runs a leakage-safe analog proof, and applies desk policy.
"""

from safe_desk.indicators import atr, realized_vol, sma, trend_state
from safe_desk.mcp_input import MCP_ENDPOINT, load_live_quote
from safe_desk.policy import evaluate_policy, load_policy
from safe_desk.position_sizing import size_spot
from safe_desk.proof import run_proof
from safe_desk.risk import evaluate_setup
from safe_desk.ticket import TradeTicket, build_ticket

__all__ = [
    "MCP_ENDPOINT",
    "atr",
    "build_ticket",
    "evaluate_policy",
    "evaluate_setup",
    "load_live_quote",
    "load_policy",
    "realized_vol",
    "run_proof",
    "size_spot",
    "sma",
    "trend_state",
    "TradeTicket",
]
__version__ = "0.2.0"
