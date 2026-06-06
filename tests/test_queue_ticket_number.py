"""Round-trip test: ticket_number harus bertahan setelah save -> load.

Regresi bug "#0000000": pasca-restart, active_tickets dimuat ulang dari DB.
Bila save_*/load_* tidak membawa ticket_number, kartu antrian menampilkan
nomor 0 (0000000). Test ini menjaga ticket_number lolos round-trip untuk
utils pure (robux & vilog) yang tabelnya dibuat oleh fixture `db` via init_db().
"""
from utils import robux_db, vilog_db


def test_robux_ticket_number_round_trip(db):
    ticket = {
        "channel_id": 123,
        "user_id": 456,
        "item_id": 1,
        "item_name": "100 Robux",
        "robux": 100,
        "rate": 130,
        "total": 13000,
        "payment_method": "QRIS",
        "payment_embed_msg_id": None,
        "paid": False,
        "admin_id": None,
        "opened_at": "2026-06-06T00:00:00+00:00",
        "warned": False,
        "ticket_number": 42,
    }
    robux_db.save_robux_ticket(ticket)
    loaded = robux_db.load_robux_tickets()
    assert 123 in loaded
    assert loaded[123]["ticket_number"] == 42


def test_robux_ticket_number_defaults_zero_when_missing(db):
    ticket = {
        "channel_id": 999,
        "user_id": 1,
        "item_id": 1,
        "item_name": "X",
        "robux": 1,
        "rate": 1,
        "total": 1,
        "opened_at": "2026-06-06T00:00:00+00:00",
    }
    robux_db.save_robux_ticket(ticket)
    loaded = robux_db.load_robux_tickets()
    assert loaded[999]["ticket_number"] == 0


def test_vilog_ticket_number_round_trip(db):
    ticket = {
        "channel_id": 321,
        "user_id": 654,
        "username_roblox": None,
        "password": "secret",
        "email": "a@b.com",
        "backup_codes": "",
        "premium": False,
        "boost": {"nama": "Boost 1k", "robux": 1000},
        "metode": "QRIS",
        "nominal": 50000,
        "admin_id": None,
        "opened_at": "2026-06-06T00:00:00+00:00",
        "warned": False,
        "ticket_number": 77,
    }
    vilog_db.save_vilog_ticket(ticket)
    loaded = vilog_db.load_vilog_tickets()
    assert 321 in loaded
    assert loaded[321]["ticket_number"] == 77


def test_vilog_ticket_number_defaults_zero_when_missing(db):
    ticket = {
        "channel_id": 888,
        "user_id": 2,
        "password": "p",
        "email": "x@y.z",
        "boost": {"nama": "B", "robux": 100},
        "metode": "QRIS",
        "nominal": 1000,
        "opened_at": "2026-06-06T00:00:00+00:00",
    }
    vilog_db.save_vilog_ticket(ticket)
    loaded = vilog_db.load_vilog_tickets()
    assert loaded[888]["ticket_number"] == 0
