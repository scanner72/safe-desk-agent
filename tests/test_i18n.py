from datetime import datetime, timezone

from safe_desk.cli import main
from safe_desk.i18n import norm_lang
from safe_desk.position_sizing import size_spot
from safe_desk.ticket import build_ticket


def test_norm_lang():
    assert norm_lang("ru") == "ru"
    assert norm_lang("\u0440\u0443\u0441\u0441\u043a\u0438\u0439") == "ru"
    assert norm_lang("EN") == "en"


def test_russian_notes_and_ticket_render():
    sized = size_spot(1_000, 50, 49, 5.0, lang="ru")
    assert sized.risk_pct == 1.0
    assert any("\u043f\u043e\u0442\u043e\u043b\u043a\u0430 \u0441\u0442\u043e\u043b\u0430" in n for n in sized.notes)

    ticket = build_ticket(
        symbol="BTCUSDT",
        side="BUY",
        entry=100_000,
        stop=98_000,
        equity=1_000,
        take_profit=104_000,
        lang="ru",
        when=datetime(2026, 9, 5, 16, 0, 0, tzinfo=timezone.utc),
    )
    text = ticket.render()
    assert "\u0421\u0442\u0430\u0442\u0443\u0441" in text
    assert "\u0421\u0442\u043e\u043f-\u043b\u043e\u0441\u0441" in text
    assert "OK TKT-20260905-160000" in text
    assert ticket.mcp_action.startswith("none")


def test_cli_lang_ru_size(capsys):
    assert main(["size", "--equity", "1000", "--entry", "100", "--stop", "99", "--lang", "ru"]) == 0
    out = capsys.readouterr().out
    assert "\u041a\u0430\u043f\u0438\u0442\u0430\u043b" in out
    assert "DRY-RUN" in out
