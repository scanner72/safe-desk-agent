"""Safe Desk — local risk math for a Binance Agent OS copilot.

No exchange credentials. Market data and orders go through the official
Binance MCP after a human approval. This package only sizes tickets and
scores simple technical setups.
"""

from safe_desk.indicators import atr, realized_vol, sma, trend_state
from safe_desk.position_sizing import size_spot
from safe_desk.risk import evaluate_setup
from safe_desk.ticket import TradeTicket, build_ticket

__all__ = [
    "atr",
    "build_ticket",
    "evaluate_setup",
    "realized_vol",
    "size_spot",
    "sma",
    "trend_state",
    "TradeTicket",
]
__version__ = "0.1.0"
