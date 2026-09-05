"""Optional EN/RU CLI strings. JSON keys and ticket ids stay English."""

from __future__ import annotations

from typing import Literal

Lang = Literal["en", "ru"]


def norm_lang(value: str | None) -> Lang:
    if value is None:
        return "en"
    lowered = value.strip().lower()
    if lowered in {"ru", "rus", "russian", "\u0440\u0443\u0441", "\u0440\u0443\u0441\u0441\u043a\u0438\u0439"}:
        return "ru"
    return "en"


_EN: dict[str, str] = {
    "analyze_header": "Safe Desk  |  DRY-RUN  |  {symbol}",
    "bars": "Bars",
    "last": "Last",
    "realized_vol": "Realized vol",
    "ann": "ann.",
    "trend": "Trend",
    "vol_regime": "Vol regime",
    "risk_score": "Risk score",
    "signal": "Signal",
    "signal_note": "(setup only — not an order)",
    "reasons": "Reasons",
    "illustrative_size": "Illustrative size (not an order)",
    "no_mcp": "No MCP call was made. Paste this into the agent, then wait for a human OK.",
    "size_header": "Safe Desk position size  |  SPOT  |  DRY-RUN",
    "equity": "Equity",
    "entry": "Entry",
    "stop": "Stop",
    "stop_distance": "Stop distance",
    "risk_pct": "Risk %",
    "risk_quote": "Risk quote",
    "quantity": "Quantity",
    "notional": "Notional",
    "notes": "Notes",
    "logged": "Logged {ticket_id} → {path}",
    "ticket_status": "Status",
    "ticket_mode": "Mode",
    "ticket_venue": "Venue",
    "ticket_product": "Product",
    "ticket_symbol": "Symbol",
    "ticket_side": "Side",
    "ticket_type": "Type",
    "ticket_sl": "Stop loss",
    "ticket_tp": "Take profit",
    "ticket_rr": "R:R",
    "ticket_rationale": "Rationale",
    "ticket_invalidation": "Invalidation",
    "ticket_mcp": "MCP action",
    "reply_ok": "Reply: OK {ticket_id}   to continue (dry-run simulates; live places via MCP).",
    "reply_cancel": "Reply: CANCEL {ticket_id}   to discard.",
    "none_notes": "none",
    "risk_capped": "Requested risk {requested:g}% exceeds desk max {max:g}%; using {max:g}%.",
    "clamped": "Stop is tight relative to equity; size clamped to 100% of wallet. Effective risk is smaller than the requested risk percent.",
    "stop_tight": "Stop is extremely tight (<0.15%). Noise may stop you out.",
    "stop_wide": "Stop is very wide (>12%). Size will be small; check the thesis.",
    "mixed_trend": "Trend is MIXED (price not stacked vs SMA20/SMA50).",
    "aligned": "Trend {trend} is aligned with {side}.",
    "fights": "Trend {trend} fights the proposed {side}.",
    "vol_high": "HIGH volatility (ATR {atr:.2f}% of price).",
    "vol_normal": "NORMAL volatility (ATR {atr:.2f}% of price).",
    "vol_low": "LOW volatility (ATR {atr:.2f}% of price).",
    "vol_unknown": "ATR unavailable; volatility unknown.",
    "stop_vs_atr_tight": "Stop is tight versus ATR ({multiple:.2f}\u00d7 ATR).",
    "stop_vs_atr_wide": "Stop is wide versus ATR ({multiple:.2f}\u00d7 ATR).",
    "stop_vs_atr_ok": "Stop distance is {multiple:.2f}\u00d7 ATR.",
    "sig_buy": "Signal BUY is a setup label, not an order.",
    "sig_avoid": "Signal AVOID — do not propose size until conditions cool.",
    "sig_hold": "Signal HOLD — wait for a cleaner stack or lower risk score.",
    "rr_low": "Reward/risk is {rr:.2f} — below 1.0. Prefer a wider target or skip.",
    "live_still_waits": "LIVE mode is requested on the ticket, but the agent still waits for OK.",
    "default_rationale": "Local helper ticket — attach MCP market context before showing a human.",
    "default_invalidation": "Daily close through stop {stop:g} cancels the idea.",
    "venue": "Binance Agentic subaccount only",
    "mcp_action": "none until the user says OK on this ticket id",
    "disclaimer": (
        "Not financial advice. This ticket is a proposal, not an order. "
        "Safe Desk never withdraws. Dry-run is the default. "
        "Demo numbers may be synthetic — never treat them as live PnL."
    ),
}

_RU: dict[str, str] = {
    "analyze_header": "Safe Desk  |  DRY-RUN  |  {symbol}",
    "bars": "\u0411\u0430\u0440\u043e\u0432",
    "last": "\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f",
    "realized_vol": "\u0420\u0435\u0430\u043b. \u0432\u043e\u043b\u0430\u0442.",
    "ann": "\u0433\u043e\u0434.",
    "trend": "\u0422\u0440\u0435\u043d\u0434",
    "vol_regime": "\u0420\u0435\u0436\u0438\u043c \u0432\u043e\u043b\u0430\u0442.",
    "risk_score": "\u0420\u0438\u0441\u043a-\u0431\u0430\u043b\u043b",
    "signal": "\u0421\u0438\u0433\u043d\u0430\u043b",
    "signal_note": "(\u0442\u043e\u043b\u044c\u043a\u043e \u0441\u0435\u0442\u0430\u043f — \u043d\u0435 \u0437\u0430\u044f\u0432\u043a\u0430)",
    "reasons": "\u041f\u0440\u0438\u0447\u0438\u043d\u044b",
    "illustrative_size": "\u041f\u0440\u0438\u043c\u0435\u0440 \u0440\u0430\u0437\u043c\u0435\u0440\u0430 (\u043d\u0435 \u0437\u0430\u044f\u0432\u043a\u0430)",
    "no_mcp": "\u0412\u044b\u0437\u043e\u0432\u0430 MCP \u043d\u0435 \u0431\u044b\u043b\u043e. \u0412\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u044d\u0442\u043e \u0430\u0433\u0435\u043d\u0442\u0443 \u0438 \u0436\u0434\u0438\u0442\u0435 OK \u0447\u0435\u043b\u043e\u0432\u0435\u043a\u0430.",
    "size_header": "\u0420\u0430\u0437\u043c\u0435\u0440 \u043f\u043e\u0437\u0438\u0446\u0438\u0438 Safe Desk  |  SPOT  |  DRY-RUN",
    "equity": "\u041a\u0430\u043f\u0438\u0442\u0430\u043b",
    "entry": "\u0412\u0445\u043e\u0434",
    "stop": "\u0421\u0442\u043e\u043f",
    "stop_distance": "\u0414\u043e \u0441\u0442\u043e\u043f\u0430",
    "risk_pct": "\u0420\u0438\u0441\u043a %",
    "risk_quote": "\u0420\u0438\u0441\u043a (\u043a\u043e\u0442\u0438\u0440.)",
    "quantity": "\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e",
    "notional": "\u041d\u043e\u043c\u0438\u043d\u0430\u043b",
    "notes": "\u0417\u0430\u043c\u0435\u0442\u043a\u0438",
    "logged": "\u0417\u0430\u043f\u0438\u0441\u0430\u043d {ticket_id} → {path}",
    "ticket_status": "\u0421\u0442\u0430\u0442\u0443\u0441",
    "ticket_mode": "\u0420\u0435\u0436\u0438\u043c",
    "ticket_venue": "\u041f\u043b\u043e\u0449\u0430\u0434\u043a\u0430",
    "ticket_product": "\u041f\u0440\u043e\u0434\u0443\u043a\u0442",
    "ticket_symbol": "\u0421\u0438\u043c\u0432\u043e\u043b",
    "ticket_side": "\u0421\u0442\u043e\u0440\u043e\u043d\u0430",
    "ticket_type": "\u0422\u0438\u043f",
    "ticket_sl": "\u0421\u0442\u043e\u043f-\u043b\u043e\u0441\u0441",
    "ticket_tp": "\u0422\u0435\u0439\u043a-\u043f\u0440\u043e\u0444\u0438\u0442",
    "ticket_rr": "R:R",
    "ticket_rationale": "\u0422\u0435\u0437\u0438\u0441",
    "ticket_invalidation": "\u041e\u0442\u043c\u0435\u043d\u0430 \u0438\u0434\u0435\u0438",
    "ticket_mcp": "\u0414\u0435\u0439\u0441\u0442\u0432\u0438\u0435 MCP",
    "reply_ok": "\u041e\u0442\u0432\u0435\u0442: OK {ticket_id}   \u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c (dry-run \u0441\u0438\u043c\u0443\u043b\u0438\u0440\u0443\u0435\u0442; live \u0448\u043b\u0451\u0442 \u0447\u0435\u0440\u0435\u0437 MCP).",
    "reply_cancel": "\u041e\u0442\u0432\u0435\u0442: CANCEL {ticket_id}   \u043e\u0442\u043c\u0435\u043d\u0438\u0442\u044c.",
    "none_notes": "\u043d\u0435\u0442",
    "risk_capped": "\u0417\u0430\u043f\u0440\u043e\u0448\u0435\u043d\u043d\u044b\u0439 \u0440\u0438\u0441\u043a {requested:g}% \u0432\u044b\u0448\u0435 \u043f\u043e\u0442\u043e\u043b\u043a\u0430 \u0441\u0442\u043e\u043b\u0430 {max:g}%; \u0441\u0442\u0430\u0432\u043b\u044e {max:g}%.",
    "clamped": "\u0421\u0442\u043e\u043f \u0441\u043b\u0438\u0448\u043a\u043e\u043c \u0443\u0437\u043a\u0438\u0439 \u043e\u0442\u043d\u043e\u0441\u0438\u0442\u0435\u043b\u044c\u043d\u043e \u043a\u0430\u043f\u0438\u0442\u0430\u043b\u0430; \u0440\u0430\u0437\u043c\u0435\u0440 \u0443\u0440\u0435\u0437\u0430\u043d \u0434\u043e 100% \u043a\u043e\u0448\u0435\u043b\u044c\u043a\u0430. \u0424\u0430\u043a\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u0440\u0438\u0441\u043a \u043c\u0435\u043d\u044c\u0448\u0435 \u0437\u0430\u043f\u0440\u043e\u0448\u0435\u043d\u043d\u043e\u0433\u043e \u043f\u0440\u043e\u0446\u0435\u043d\u0442\u0430.",
    "stop_tight": "\u0421\u0442\u043e\u043f \u043e\u0447\u0435\u043d\u044c \u0443\u0437\u043a\u0438\u0439 (<0.15%). \u0428\u0443\u043c \u043c\u043e\u0436\u0435\u0442 \u0432\u044b\u0431\u0438\u0442\u044c.",
    "stop_wide": "\u0421\u0442\u043e\u043f \u043e\u0447\u0435\u043d\u044c \u0448\u0438\u0440\u043e\u043a\u0438\u0439 (>12%). \u0420\u0430\u0437\u043c\u0435\u0440 \u0431\u0443\u0434\u0435\u0442 \u043c\u0430\u043b\u0435\u043d\u044c\u043a\u0438\u043c; \u043f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0442\u0435\u0437\u0438\u0441.",
    "mixed_trend": "\u0422\u0440\u0435\u043d\u0434 MIXED (\u0446\u0435\u043d\u0430 \u043d\u0435 \u0432\u044b\u0441\u0442\u0440\u043e\u0435\u043d\u0430 \u043e\u0442\u043d\u043e\u0441\u0438\u0442\u0435\u043b\u044c\u043d\u043e SMA20/SMA50).",
    "aligned": "\u0422\u0440\u0435\u043d\u0434 {trend} \u0441\u043e\u0432\u043f\u0430\u0434\u0430\u0435\u0442 \u0441\u043e \u0441\u0442\u043e\u0440\u043e\u043d\u043e\u0439 {side}.",
    "fights": "\u0422\u0440\u0435\u043d\u0434 {trend} \u043f\u0440\u043e\u0442\u0438\u0432 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u043d\u043e\u0433\u043e {side}.",
    "vol_high": "HIGH-\u0432\u043e\u043b\u0430\u0442\u0438\u043b\u044c\u043d\u043e\u0441\u0442\u044c (ATR {atr:.2f}% \u0446\u0435\u043d\u044b).",
    "vol_normal": "NORMAL-\u0432\u043e\u043b\u0430\u0442\u0438\u043b\u044c\u043d\u043e\u0441\u0442\u044c (ATR {atr:.2f}% \u0446\u0435\u043d\u044b).",
    "vol_low": "LOW-\u0432\u043e\u043b\u0430\u0442\u0438\u043b\u044c\u043d\u043e\u0441\u0442\u044c (ATR {atr:.2f}% \u0446\u0435\u043d\u044b).",
    "vol_unknown": "ATR \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d; \u0432\u043e\u043b\u0430\u0442\u0438\u043b\u044c\u043d\u043e\u0441\u0442\u044c \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430.",
    "stop_vs_atr_tight": "\u0421\u0442\u043e\u043f \u0443\u0437\u043a\u0438\u0439 \u043e\u0442\u043d\u043e\u0441\u0438\u0442\u0435\u043b\u044c\u043d\u043e ATR ({multiple:.2f}\u00d7 ATR).",
    "stop_vs_atr_wide": "\u0421\u0442\u043e\u043f \u0448\u0438\u0440\u043e\u043a\u0438\u0439 \u043e\u0442\u043d\u043e\u0441\u0438\u0442\u0435\u043b\u044c\u043d\u043e ATR ({multiple:.2f}\u00d7 ATR).",
    "stop_vs_atr_ok": "\u0414\u0438\u0441\u0442\u0430\u043d\u0446\u0438\u044f \u0441\u0442\u043e\u043f\u0430 {multiple:.2f}\u00d7 ATR.",
    "sig_buy": "\u0421\u0438\u0433\u043d\u0430\u043b BUY — \u044f\u0440\u043b\u044b\u043a \u0441\u0435\u0442\u0430\u043f\u0430, \u043d\u0435 \u0437\u0430\u044f\u0432\u043a\u0430.",
    "sig_avoid": "\u0421\u0438\u0433\u043d\u0430\u043b AVOID — \u043d\u0435 \u043f\u0440\u0435\u0434\u043b\u0430\u0433\u0430\u0442\u044c \u0440\u0430\u0437\u043c\u0435\u0440, \u043f\u043e\u043a\u0430 \u0440\u044b\u043d\u043e\u043a \u043d\u0435 \u0443\u0441\u043f\u043e\u043a\u043e\u0438\u0442\u0441\u044f.",
    "sig_hold": "\u0421\u0438\u0433\u043d\u0430\u043b HOLD — \u0436\u0434\u0430\u0442\u044c \u0431\u043e\u043b\u0435\u0435 \u0447\u0438\u0441\u0442\u044b\u0439 \u0441\u0442\u0435\u043a \u0438\u043b\u0438 \u043c\u0435\u043d\u044c\u0448\u0438\u0439 \u0440\u0438\u0441\u043a-\u0431\u0430\u043b\u043b.",
    "rr_low": "R:R {rr:.2f} — \u043d\u0438\u0436\u0435 1.0. \u041b\u0443\u0447\u0448\u0435 \u0448\u0438\u0440\u0435 \u0446\u0435\u043b\u044c \u0438\u043b\u0438 \u043f\u0440\u043e\u043f\u0443\u0441\u043a.",
    "live_still_waits": "\u041d\u0430 \u0442\u0438\u043a\u0435\u0442\u0435 \u0437\u0430\u043f\u0440\u043e\u0448\u0435\u043d LIVE, \u043d\u043e \u0430\u0433\u0435\u043d\u0442 \u0432\u0441\u0451 \u0440\u0430\u0432\u043d\u043e \u0436\u0434\u0451\u0442 OK.",
    "default_rationale": "\u0422\u0438\u043a\u0435\u0442 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0433\u043e \u043f\u043e\u043c\u043e\u0449\u043d\u0438\u043a\u0430 — \u043f\u0435\u0440\u0435\u0434 \u043f\u043e\u043a\u0430\u0437\u043e\u043c \u0447\u0435\u043b\u043e\u0432\u0435\u043a\u0443 \u0434\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442 MCP.",
    "default_invalidation": "\u0414\u043d\u0435\u0432\u043d\u043e\u0435 \u0437\u0430\u043a\u0440\u044b\u0442\u0438\u0435 \u0447\u0435\u0440\u0435\u0437 \u0441\u0442\u043e\u043f {stop:g} \u043e\u0442\u043c\u0435\u043d\u044f\u0435\u0442 \u0438\u0434\u0435\u044e.",
    "venue": "\u0422\u043e\u043b\u044c\u043a\u043e Agentic-\u0441\u0443\u0431\u0430\u043a\u043a\u0430\u0443\u043d\u0442 Binance",
    "mcp_action": "none until the user says OK on this ticket id",
    "disclaimer": (
        "\u041d\u0435 \u0438\u043d\u0432\u0435\u0441\u0442\u0438\u0446\u0438\u043e\u043d\u043d\u0430\u044f \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u044f. \u042d\u0442\u043e \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0435, \u043d\u0435 \u0437\u0430\u044f\u0432\u043a\u0430. "
        "Safe Desk \u043d\u0435 \u0432\u044b\u0432\u043e\u0434\u0438\u0442 \u0441\u0440\u0435\u0434\u0441\u0442\u0432\u0430. \u041f\u043e \u0443\u043c\u043e\u043b\u0447\u0430\u043d\u0438\u044e dry-run. "
        "\u0414\u0435\u043c\u043e-\u0446\u0438\u0444\u0440\u044b \u043c\u043e\u0433\u0443\u0442 \u0431\u044b\u0442\u044c \u0441\u0438\u043d\u0442\u0435\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u043c\u0438 — \u043d\u0435 \u0441\u0447\u0438\u0442\u0430\u0439\u0442\u0435 \u0438\u0445 \u0436\u0438\u0432\u044b\u043c PnL."
    ),
}

_TABLE: dict[Lang, dict[str, str]] = {"en": _EN, "ru": _RU}


def t(lang: Lang, key: str, **kwargs: object) -> str:
    table = _TABLE.get(lang, _EN)
    template = table.get(key) or _EN[key]
    return template.format(**kwargs) if kwargs else template
