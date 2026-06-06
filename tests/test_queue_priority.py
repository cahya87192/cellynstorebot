"""Test prioritas Top Spender pada antrian (FIFO dengan tier prioritas).

Top Spender bulan berjalan didahulukan di barisan tunggu, FIFO di dalam tier.
Deteksi via set `priority_ids` (member_id), bukan role. Murni (tanpa discord).
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


def test_normalize_sets_is_priority():
    tk = _ticket(7, "2026-06-06T00:00:00+00:00")
    assert q.normalize_ticket("ml", 1, tk, {}, {7})["is_priority"] is True
    assert q.normalize_ticket("ml", 1, tk, {}, {99})["is_priority"] is False
    # Tanpa priority_ids -> default tidak prioritas.
    assert q.normalize_ticket("ml", 1, tk, {})["is_priority"] is False


def test_priority_jumps_ahead_of_older_non_priority():
    # Tiket non-prioritas dibuka lebih dulu, tapi tiket prioritas harus di depan.
    bot = _FakeBot({
        "MLStore": _FakeCog({
            10: _ticket(1, "2026-06-06T00:00:00+00:00", 1),  # non-prioritas, terlama
            20: _ticket(2, "2026-06-06T01:00:00+00:00", 2),  # non-prioritas
            30: _ticket(3, "2026-06-06T02:00:00+00:00", 3),  # PRIORITAS (terbaru)
        }),
    })
    ordered = q.build_queue(q.collect_tickets(bot, None, {}, {3}))
    by_ch = {t["channel_id"]: t for t in ordered}
    # Top Spender (ch 30) jadi posisi 1 walau paling baru.
    assert by_ch[30]["is_priority"] is True
    assert by_ch[30]["position"] == 1 and by_ch[30]["ahead"] == 0
    # Non-prioritas tetap FIFO di belakang tier prioritas.
    assert by_ch[10]["position"] == 2
    assert by_ch[20]["position"] == 3


def test_fifo_within_priority_tier():
    bot = _FakeBot({
        "MLStore": _FakeCog({
            10: _ticket(1, "2026-06-06T03:00:00+00:00", 1),  # prioritas, lebih baru
            20: _ticket(2, "2026-06-06T01:00:00+00:00", 2),  # prioritas, lebih lama
            30: _ticket(3, "2026-06-06T00:00:00+00:00", 3),  # non-prioritas, terlama
        }),
    })
    ordered = q.build_queue(q.collect_tickets(bot, None, {}, {1, 2}))
    by_ch = {t["channel_id"]: t for t in ordered}
    # Sesama prioritas: yang lebih lama (ch 20) di depan ch 10.
    assert by_ch[20]["position"] == 1
    assert by_ch[10]["position"] == 2
    # Non-prioritas terakhir meski paling lama dibuka.
    assert by_ch[30]["position"] == 3


def test_priority_with_handling_excluded_from_waiting():
    bot = _FakeBot({
        "MLStore": _FakeCog({
            10: _ticket(1, "2026-06-06T00:00:00+00:00", 1),  # prioritas + diproses
            20: _ticket(2, "2026-06-06T01:00:00+00:00", 2),  # prioritas, menunggu
            30: _ticket(3, "2026-06-06T02:00:00+00:00", 3),  # non-prioritas, menunggu
        }),
    })
    ordered = q.build_queue(q.collect_tickets(bot, None, {10: 555}, {1, 2}))
    by_ch = {t["channel_id"]: t for t in ordered}
    assert by_ch[10]["handling"] is True and by_ch[10]["position"] is None
    assert by_ch[20]["position"] == 1  # prioritas menunggu di depan
    assert by_ch[30]["position"] == 2
    assert q.queue_counts(ordered) == (2, 1)
