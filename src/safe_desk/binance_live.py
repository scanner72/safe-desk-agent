"""Public Binance market data shaped like official Agent OS MCP tools.

No API keys. No orders. This is for Analyze / ATR sizing when the LLM
has not pasted MCP JSON yet (Docker / local UI / judge path).

Official MCP market tools we mirror:

- ``spot.tickerPrice``  → GET /api/v3/ticker/price
- ``spot.klines``       → GET /api/v3/klines

The helper still never stores secrets and never places a trade. Trading
stays dry-run until ``OK TKT-…`` on the official MCP.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from safe_desk.mcp_input import (
    MCP_ENDPOINT,
    LivePrice,
    parse_klines_payload,
    parse_price_payload,
)
from safe_desk.ohlcv import Bar, bars_to_csv, bars_to_dicts

BINANCE_REST = "https://api.binance.com"
BINANCE_REST_FALLBACK = "https://data-api.binance.vision"
SOURCE = "binance_public_mcp_shaped"
MCP_TOOLS = ("spot.tickerPrice", "spot.klines")
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_INTERVAL = "1h"
DEFAULT_LIMIT = 120
DEFAULT_TIMEOUT = 8.0
MIN_LIMIT = 10
MAX_LIMIT = 500
SYMBOL_RE = re.compile(r"^[A-Z0-9]{4,20}$")
ALLOWED_INTERVALS = frozenset(
    {
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    }
)

UrlOpen = Callable[..., Any]


class LiveMarketError(Exception):
    """User-facing live-market failure (timeout, HTTP, empty payload)."""


@dataclass(frozen=True)
class LiveMarket:
    symbol: str
    interval: str
    limit: int
    price: LivePrice
    bars: list[Bar]
    ticker: dict[str, Any]
    klines: list[Any]
    source: str = SOURCE
    mcp_tools: tuple[str, ...] = MCP_TOOLS
    mcp_url: str = MCP_ENDPOINT
    rest_base: str = BINANCE_REST

    @property
    def bars_csv(self) -> str:
        return bars_to_csv(self.bars)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "limit": self.limit,
            "price": self.price.to_dict(),
            "last": self.price.last,
            "bars": bars_to_dicts(self.bars),
            "bars_csv": self.bars_csv,
            "ticker": self.ticker,
            "source": self.source,
            "mcp_tools": list(self.mcp_tools),
            "mcp_url": self.mcp_url,
            "rest_base": self.rest_base,
            "note": (
                "Public REST mirroring Agent OS MCP market tools "
                f"{', '.join(self.mcp_tools)}. No API keys. Not an order."
            ),
        }


def normalize_symbol(symbol: str | None) -> str:
    value = (symbol or DEFAULT_SYMBOL).strip().upper().replace("-", "").replace("_", "")
    if not SYMBOL_RE.fullmatch(value):
        raise ValueError("symbol must be a Binance pair like BTCUSDT")
    return value


def normalize_interval(interval: str | None) -> str:
    value = (interval or DEFAULT_INTERVAL).strip()
    if value not in ALLOWED_INTERVALS:
        allowed = ", ".join(sorted(ALLOWED_INTERVALS))
        raise ValueError(f"interval must be one of: {allowed}")
    return value


def normalize_limit(limit: int | str | None) -> int:
    raw = DEFAULT_LIMIT if limit is None or limit == "" else limit
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit must be an integer") from exc
    return max(MIN_LIMIT, min(MAX_LIMIT, value))


def rest_bases() -> tuple[str, ...]:
    override = (os.environ.get("SAFE_DESK_BINANCE_REST") or "").strip().rstrip("/")
    if override:
        return (override,)
    return (BINANCE_REST, BINANCE_REST_FALLBACK)


def rest_base() -> str:
    return rest_bases()[0]


def live_timeout() -> float:
    raw = os.environ.get("SAFE_DESK_LIVE_TIMEOUT")
    if not raw:
        return DEFAULT_TIMEOUT
    try:
        return max(1.0, min(30.0, float(raw)))
    except ValueError:
        return DEFAULT_TIMEOUT


def fetch_live_market(
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    limit: int = DEFAULT_LIMIT,
    *,
    timeout: float | None = None,
    urlopen: UrlOpen | None = None,
) -> LiveMarket:
    """Fetch last price + klines. Public REST only. No secrets. No orders."""
    pair = normalize_symbol(symbol)
    tf = normalize_interval(interval)
    count = normalize_limit(limit)
    wait = DEFAULT_TIMEOUT if timeout is None else max(1.0, float(timeout))
    opener = urlopen or urllib.request.urlopen
    ticker, klines, base = _fetch_from_bases(pair, tf, count, wait, opener)

    price = parse_price_payload(ticker, default_symbol=pair, source=SOURCE)
    bars = parse_klines_payload(klines)
    if price.symbol and price.symbol != pair:
        raise LiveMarketError(f"ticker symbol {price.symbol} does not match {pair}")
    return LiveMarket(
        symbol=pair,
        interval=tf,
        limit=len(bars),
        price=price,
        bars=bars,
        ticker=_as_object(ticker),
        klines=_as_list(klines),
        rest_base=base,
    )


def _fetch_from_bases(
    pair: str,
    tf: str,
    count: int,
    timeout: float,
    urlopen: UrlOpen,
) -> tuple[Any, Any, str]:
    errors: list[str] = []
    for base in rest_bases():
        try:
            ticker = _http_get_json(
                f"{base}/api/v3/ticker/price?{urllib.parse.urlencode({'symbol': pair})}",
                timeout=timeout,
                urlopen=urlopen,
                what=f"spot.tickerPrice for {pair}",
            )
            klines = _http_get_json(
                f"{base}/api/v3/klines?{urllib.parse.urlencode({'symbol': pair, 'interval': tf, 'limit': count})}",
                timeout=timeout,
                urlopen=urlopen,
                what=f"spot.klines for {pair} {tf}",
            )
            return ticker, klines, base
        except LiveMarketError as exc:
            errors.append(f"{base}: {exc}")
            continue
    detail = " | ".join(errors) if errors else "no public REST host configured"
    raise LiveMarketError(
        f"Could not fetch MCP-shaped market data for {pair}. {detail} "
        "Offline fallback: Use sample BTC CSV."
    )


def _as_object(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {"price": payload}


def _as_list(payload: Any) -> list[Any]:
    return payload if isinstance(payload, list) else [payload]


def _http_get_json(
    url: str,
    *,
    timeout: float,
    urlopen: UrlOpen,
    what: str,
) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "safe-desk-agent/live-market (no-api-key; mcp-shaped)",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as resp:
            raw = resp.read()
    except TimeoutError as exc:
        raise LiveMarketError(
            f"Timed out after {timeout:.0f}s fetching {what}. "
            "Try again or use the sample BTC CSV offline."
        ) from exc
    except urllib.error.HTTPError as exc:
        detail = _http_error_detail(exc)
        raise LiveMarketError(f"Binance public market data failed for {what}: {detail}") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise LiveMarketError(
            f"Could not reach Binance public market data for {what}: {reason}. "
            "Offline fallback: Use sample BTC CSV."
        ) from exc
    except OSError as exc:
        raise LiveMarketError(
            f"Could not reach Binance public market data for {what}: {exc}. "
            "Offline fallback: Use sample BTC CSV."
        ) from exc

    if not raw:
        raise LiveMarketError(f"Empty response fetching {what}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LiveMarketError(f"Invalid JSON fetching {what}") from exc
    if isinstance(payload, dict) and payload.get("code") not in (None, 0):
        msg = payload.get("msg") or payload.get("message") or payload
        raise LiveMarketError(f"Binance rejected {what}: {msg}")
    return payload


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    body = ""
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except OSError:
        body = ""
    if body:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            msg = parsed.get("msg") or parsed.get("message")
            if msg:
                return f"HTTP {exc.code} {msg}"
        snippet = body.strip().replace("\n", " ")[:180]
        return f"HTTP {exc.code} {snippet}"
    return f"HTTP {exc.code} {exc.reason}"
