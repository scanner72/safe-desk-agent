from safe_desk.approval import is_bare_approval, parse_ok_phrase, phrase_matches_ticket


def test_ok_requires_ticket_id():
    assert parse_ok_phrase("ok") is None
    assert parse_ok_phrase("OK") is None
    assert parse_ok_phrase("lgtm") is None
    assert is_bare_approval("ok")
    assert parse_ok_phrase("OK TKT-20260905-160000") == "TKT-20260905-160000"
    assert parse_ok_phrase("ok TKT-20260905-160000") == "TKT-20260905-160000"
    assert phrase_matches_ticket("OK TKT-20260905-160000", "TKT-20260905-160000")
    assert not phrase_matches_ticket("OK TKT-20260905-160000", "TKT-20260905-160001")
