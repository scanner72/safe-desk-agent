"""Human approval phrases. A bare 'ok' is never enough."""

from __future__ import annotations

import re

TICKET_ID_RE = re.compile(r"^TKT-\d{8}-\d{6}$", re.IGNORECASE)
OK_RE = re.compile(r"^\s*OK\s+(TKT-\d{8}-\d{6})\s*$", re.IGNORECASE)
CANCEL_RE = re.compile(r"^\s*CANCEL\s+(TKT-\d{8}-\d{6})\s*$", re.IGNORECASE)
BARE_YES = frozenset(
    {
        "ok",
        "okay",
        "lgtm",
        "go",
        "yes",
        "y",
        "fire",
        "approve",
        "do it",
        "ship it",
        "да",
        "ок",
        "окей",
    }
)


def normalize_ticket_id(ticket_id: str) -> str:
    return ticket_id.strip().upper()


def parse_ok_phrase(phrase: str | None) -> str | None:
    """Return `TKT-…` if the phrase is `OK TKT-…`, else None."""
    if not phrase:
        return None
    match = OK_RE.match(phrase)
    if not match:
        return None
    return normalize_ticket_id(match.group(1))


def parse_cancel_phrase(phrase: str | None) -> str | None:
    if not phrase:
        return None
    match = CANCEL_RE.match(phrase)
    if not match:
        return None
    return normalize_ticket_id(match.group(1))


def is_bare_approval(phrase: str | None) -> bool:
    if phrase is None:
        return False
    return phrase.strip().lower() in BARE_YES


def phrase_matches_ticket(phrase: str | None, ticket_id: str) -> bool:
    parsed = parse_ok_phrase(phrase)
    return parsed is not None and parsed == normalize_ticket_id(ticket_id)
