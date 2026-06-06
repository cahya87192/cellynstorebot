"""Test logika antrian dengan handling_map sebagai SUMBER KEBENARAN TUNGGAL.

Sejak PR C, status 'diproses' tidak lagi ditebak dari isi tiket melainkan
ditentukan oleh handling_map {channel_id: admin_id} (hasil command !pay).
Test ini murni (utils/queue.py tidak meng-import discord).
"""
from utils import queue as q


class _FakeCog:
    def __init__(self, active_tickets):
        self.active_tickets = active_tickets


class _FakeBot:
    def __init__(self, cogs):
        self.cogs = cogs


def _ticket(user_id, opened_at, number=0):
    return {"user_id": user_id, "opened_at": opened_at, "ticket_number": number}


def test_normalize_handling_only_from_map():
    tk = _ticket(1, "2026-06-06T00:00:00+00:00", 5)
    # Tidak di map -> menunggu, tanpa admin.
    n = q.normalize_ticket("ml", 100, tk, {})
    assert n["handling"] is False
    assert n["admin_id"] is None
    # Di map -> diproses, admin sesuai map.
    n2 = q.normalize_ticket("ml", 100, tk, {100: 777})
    assert n2["handling"] is True
    assert n2["admin_id"] == 777


def test_normalize_ignores_legacy_signals():
    # Tiket punya admin_id/paid/status lama, tapi TANPA entry di map -> menunggu.
    tk = {
        "user_id": 1,
        "opened_at": "2026-06-06T00:00:00+00:00",
        "ticket_number": 9,
        "admin_id": 555,
        "paid": True,
        "status": "diproses",
    }
    n = q.normalize_ticket("robux", 100, tk, {})
    assert n["handling"] is False
    assert n["admin_id"] is None


def test_coerce_handling_map_accepts_string_keys():
    tk = _ticket(1, "2026-06-06T00:00:00+00:00")
    n = q.normalize_ticket("gp", 123, tk, {"123": 42})  # kunci string (mis. json)
    assert n["handling"] is True
    assert n["admin_id"] == 42


def test_collect_tickets_uses_handling_map():
    bot = _FakeBot({
        "MLStore": _FakeCog({
            100: _ticket(1, "2026-06-06T00:00:00+00:00", 1),
            200: _ticket(2, "2026-06-06T01:00:00+00:00", 2),
        }),
    })
    out = q.collect_tickets(bot, guild=None, handling_map={100: 999})
    by_ch = {t["channel_id"]: t for t in out}
    assert by_ch[100]["handling"] is True and by_ch[100]["admin_id"] == 999
    assert by_ch[200]["handling"] is False and by_ch[200]["admin_id"] is None


def test_build_queue_handling_excluded_from_waiting():
    bot = _FakeBot({
        "MLStore": _FakeCog({
            10: _ticket(1, "2026-06-06T00:00:00+00:00", 1),  # oldest -> diproses
            20: _ticket(2, "2026-06-06T01:00:00+00:00", 2),  # waiting #1
            30: _ticket(3, "2026-06-06T02:00:00+00:00", 3),  # waiting #2
        }),
    })
    ordered = q.build_queue(q.collect_tickets(bot, None, {10: 999}))
    by_ch = {t["channel_id"]: t for t in ordered}
    assert by_ch[10]["handling"] is True
    assert by_ch[10]["position"] is None
    assert by_ch[20]["position"] == 1 and by_ch[20]["ahead"] == 0
    assert by_ch[30]["position"] == 2 and by_ch[30]["ahead"] == 1
    waiting, handling = q.queue_counts(ordered)
    assert (waiting, handling) == (2, 1)
