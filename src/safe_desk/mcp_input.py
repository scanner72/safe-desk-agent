"""Format MCP-shaped price / balance payloads for Safe Desk.

No network. No API keys. The official Binance Agent OS MCP
(`https://agent.binance.com/mcp/agentic`) is called by the LLM client.
This module only accepts JSON the model already fetched or the human pasted.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MCP_ENDPOINT = "https://agent.binance.com/mcp/agentic"
MCP_DOCS = "https://developers.binance.com/en/docs/agent-native/mcp-server"

QUOTE_ASSETS = ("USDT", "FDUSD", "USDC", "BUSD")


@dataclass(frozen=True)
class LivePrice:
    symbol: str | None
    last: float
    bid: float | None = None
    ask: float | None = None
    change_pct: float | None = None
    source: str = "mcp_json"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveBalance:
    quote_asset: str
    free: float
    locked: float = 0.0
    equity: float = 0.0
    balances: tuple[dict[str, Any], ...] = ()
    account: str = "agentic"
    source: str = "mcp_json"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["balances"] = list(self.balances)
        return data


@dataclass(frozen=True)
class LiveQuote:
    """Merged last + Agentic quote equity for analyze / size / ticket."""

    symbol: str | None
    last: float | None
    equity: float | None
    quote_asset: str
    price: LivePrice | None
    balance: LiveBalance | None
    notes: tuple[str, ...]
    mcp_endpoint: str = MCP_ENDPOINT

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "last": self.last,
            "equity": self.equity,
            "quote_asset": self.quote_asset,
            "price": None if self.price is None else self.price.to_dict(),
            "balance": None if self.balance is None else self.balance.to_dict(),
            "notes": list(self.notes),
            "mcp_endpoint": self.mcp_endpoint,
        }


def load_json_payload(source: Path | str | dict[str, Any]) -> Any:
    if isinstance(source, dict):
        return source
    if isinstance(source, str) and not _looks_like_path(source):
        return json.loads(source)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def _looks_like_path(value: str) -> bool:
    stripped = value.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return False
    return True


def parse_price_payload(payload: Any, *, default_symbol: str | None = None) -> LivePrice:
    obj = _unwrap(payload)
    if isinstance(obj, list):
        if not obj:
            raise ValueError("price payload list is empty")
        obj = _unwrap(obj[0])
    if not isinstance(obj, dict):
        raise ValueError("price payload must be an object")

    last = _first_number(
        obj,
        (
            "lastPrice",
            "last",
            "price",
            "close",
            "markPrice",
            "indexPrice",
            "c",
        ),
    )
    if last is None or last <= 0:
        raise ValueError("price payload has no positive last/price field")

    symbol = _first_str(obj, ("symbol", "s", "pair")) or default_symbol
    bid = _first_number(obj, ("bidPrice", "bid", "b"))
    ask = _first_number(obj, ("askPrice", "ask", "a"))
    change = _first_number(obj, ("priceChangePercent", "change_pct", "changePercent", "P"))
    return LivePrice(
        symbol=symbol.upper() if symbol else None,
        last=float(last),
        bid=bid,
        ask=ask,
        change_pct=change,
    )


def parse_balance_payload(
    payload: Any,
    *,
    quote_asset: str = "USDT",
) -> LiveBalance:
    obj = _unwrap(payload)
    if not isinstance(obj, dict) and not isinstance(obj, list):
        raise ValueError("balance payload must be an object or list")

    account = "agentic"
    rows: list[dict[str, Any]] = []
    if isinstance(obj, list):
        rows = [_normalize_balance_row(x) for x in obj if isinstance(x, dict)]
    else:
        account = str(obj.get("account") or obj.get("accountType") or "agentic")
        raw_balances = obj.get("balances") or obj.get("assets") or obj.get("data")
        if isinstance(raw_balances, list):
            rows = [_normalize_balance_row(x) for x in raw_balances if isinstance(x, dict)]
        else:
            # { "USDT": {"free": 1000} } or { "USDT": "1000" }
            for key, value in obj.items():
                if str(key).upper() in QUOTE_ASSETS or (
                    isinstance(value, dict) and ("free" in value or "locked" in value)
                ):
                    row = {"asset": str(key)}
                    if isinstance(value, dict):
                        row.update(value)
                    else:
                        row["free"] = value
                    rows.append(_normalize_balance_row(row))

    quote = quote_asset.upper()
    match = next((r for r in rows if str(r.get("asset", "")).upper() == quote), None)
    if match is None and len(rows) == 1:
        match = rows[0]
        quote = str(match.get("asset") or quote).upper()
    if match is None:
        # still allow equity if the payload itself has free/equity
        if isinstance(obj, dict):
            free = _first_number(obj, ("free", "equity", "available", "quoteEquity"))
            if free is not None:
                return LiveBalance(
                    quote_asset=quote,
                    free=float(free),
                    locked=float(_first_number(obj, ("locked",)) or 0.0),
                    equity=float(free),
                    balances=tuple(rows),
                    account=account,
                )
        raise ValueError(f"balance payload has no {quote} row")

    free = float(match.get("free") or 0.0)
    locked = float(match.get("locked") or 0.0)
    equity = free + locked
    return LiveBalance(
        quote_asset=str(match.get("asset") or quote).upper(),
        free=free,
        locked=locked,
        equity=equity,
        balances=tuple(rows),
        account=account,
    )


def merge_live_inputs(
    *,
    price: LivePrice | None = None,
    balance: LiveBalance | None = None,
    symbol: str | None = None,
) -> LiveQuote:
    notes: list[str] = []
    last = None if price is None else price.last
    equity = None if balance is None else balance.free
    resolved_symbol = symbol
    if price is not None and price.symbol:
        resolved_symbol = price.symbol
    if price is None and balance is None:
        notes.append("No MCP-shaped JSON provided — offline path.")
    else:
        notes.append(
            f"Live path: numbers from MCP-shaped JSON (endpoint {MCP_ENDPOINT}). "
            "This helper did not call Binance REST and holds no API keys."
        )
    if balance is not None and balance.account and balance.account.lower() not in {
        "agentic",
        "agentic_subaccount",
        "virtual",
    }:
        notes.append(
            f"Balance account field is {balance.account!r}. "
            "Size only against the Agentic subaccount, not the main book."
        )
    quote = "USDT" if balance is None else balance.quote_asset
    return LiveQuote(
        symbol=resolved_symbol.upper() if resolved_symbol else None,
        last=last,
        equity=equity,
        quote_asset=quote,
        price=price,
        balance=balance,
        notes=tuple(notes),
    )


def load_live_quote(
    *,
    price_source: Path | str | dict[str, Any] | None = None,
    balance_source: Path | str | dict[str, Any] | None = None,
    symbol: str | None = None,
    quote_asset: str = "USDT",
) -> LiveQuote:
    price = None
    if price_source is not None:
        price = parse_price_payload(load_json_payload(price_source), default_symbol=symbol)
    balance = None
    if balance_source is not None:
        balance = parse_balance_payload(load_json_payload(balance_source), quote_asset=quote_asset)
    return merge_live_inputs(price=price, balance=balance, symbol=symbol)


def _unwrap(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    for key in ("result", "data", "ticker", "payload", "content", "body"):
        inner = payload.get(key)
        if isinstance(inner, (dict, list)):
            return _unwrap(inner)
    return payload


def _normalize_balance_row(row: dict[str, Any]) -> dict[str, Any]:
    asset = row.get("asset") or row.get("coin") or row.get("currency") or row.get("a")
    free = _first_number(row, ("free", "available", "availableBalance", "f", "walletBalance"))
    locked = _first_number(row, ("locked", "freeze", "l")) or 0.0
    return {
        "asset": str(asset).upper() if asset else "",
        "free": 0.0 if free is None else float(free),
        "locked": float(locked),
    }


def _first_number(obj: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            try:
                return float(obj[key])
            except (TypeError, ValueError):
                continue
    return None


def _first_str(obj: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
