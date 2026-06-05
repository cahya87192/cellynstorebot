"""Unit test fitur garansi manual (pending-grant + override durasi).

Menguji lapisan murni/SQLite saja (subscription + reviews), tanpa Discord:
- parsing durasi garansi dari command (angka & satuan)
- override durasi di days_remaining/expiry_date
- CRUD pending-grant + logika pencocokan (item-specific > wildcard, FIFO)
- alur lengkap: grant -> poller reconcile -> rating -> sisa garansi
"""
import datetime
import importlib

import utils.subscription as sub


def _rv():
    import utils.reviews as rv
    importlib.reload(rv)
    rv.init_reviews_db()
    return rv


# ── parse_warranty_duration ────────────────────────────────────────────────────────
def test_parse_warranty_duration_bare_int_is_days():
    assert sub.parse_warranty_duration("30") == 30
    assert sub.parse_warranty_duration("  7 ") == 7
    assert sub.parse_warranty_duration("1") == 1


def test_parse_warranty_duration_units():
    assert sub.parse_warranty_duration("2 minggu") == 14
    assert sub.parse_warranty_duration("1 bulan") == 30
    assert sub.parse_warranty_duration("1 tahun") == 365
    assert sub.parse_warranty_duration("30 hari") == 30
    assert sub.parse_warranty_duration("3bln") == 90


def test_parse_warranty_duration_invalid():
    assert sub.parse_warranty_duration(None) is None
    assert sub.parse_warranty_duration("") is None
    assert sub.parse_warranty_duration("abc") is None
    assert sub.parse_warranty_duration("0") is None
    assert sub.parse_warranty_duration("-5") is None


# ── override_days di days_remaining / expiry_date ───────────────────────────────────
def test_days_remaining_override_beats_name_and_default():
    start = "2026-01-01T00:00:00+00:00"
    now = datetime.datetime(2026, 1, 6, tzinfo=datetime.timezone.utc)  # 5 hari berlalu
    # item langganan 1 bulan (30) & default 7, tapi override 10 -> sisa 5
    assert sub.days_remaining(start, "CANVA PRO 1 Bulan", now=now,
                              default_days=7, override_days=10) == 5
    # non-langganan + override 3 -> sudah habis di hari ke-5
    assert sub.days_remaining(start, "100 Robux", now=now,
                              default_days=7, override_days=3) < 0


def test_override_none_falls_back_to_name_or_default():
    start = "2026-01-01T00:00:00+00:00"
    now = datetime.datetime(2026, 1, 3, tzinfo=datetime.timezone.utc)  # 2 hari berlalu
    # override None, non-langganan -> pakai default 7 -> sisa 5
    assert sub.days_remaining(start, "100 Robux", now=now,
                              default_days=7, override_days=None) == 5
    # override None, langganan 1 bulan -> 30 - 2 = 28
    assert sub.days_remaining(start, "CANVA PRO 1 Bulan", now=now,
                              default_days=7) == 28


def test_expiry_date_override():
    start = "2026-01-01T00:00:00+00:00"
    exp = sub.expiry_date(start, "100 Robux", default_days=7, override_days=10)
    assert exp == datetime.datetime(2026, 1, 11, tzinfo=datetime.timezone.utc)


# ── pending-grant CRUD + pencocokan ─────────────────────────────────────────────────
def test_add_list_pop_pending(db):
    rv = _rv()
    gid = rv.add_pending_warranty(111, 30, item="Netflix", note="vip", granted_by=999)
    assert gid > 0
    pend = rv.list_pending_warranty(111)
    assert len(pend) == 1
    assert pend[0]["days"] == 30 and pend[0]["item"] == "Netflix" and pend[0]["note"] == "vip"
    # pop dengan item cocok (substring 2 arah)
    g = rv.pop_pending_warranty(111, "NETFLIX PREMIUM 1 Bulan")
    assert g is not None and g["days"] == 30
    # sudah dipakai -> tak muncul lagi & tak bisa dipop ulang
    assert rv.list_pending_warranty(111) == []
    assert rv.pop_pending_warranty(111, "Netflix") is None


def test_pop_prefers_item_match_then_wildcard_fifo(db):
    rv = _rv()
    rv.add_pending_warranty(111, 7)                    # id1: wildcard (item kosong)
    rv.add_pending_warranty(111, 30, item="Spotify")   # id2: spesifik
    # transaksi Spotify -> ambil yang spesifik (30), bukan wildcard
    g = rv.pop_pending_warranty(111, "SPOTIFY 3 Bulan")
    assert g["days"] == 30
    # transaksi lain -> ambil wildcard (7)
    g2 = rv.pop_pending_warranty(111, "100 Robux")
    assert g2["days"] == 7
    assert rv.list_pending_warranty(111) == []


def test_pop_no_match_keeps_specific_grant(db):
    rv = _rv()
    rv.add_pending_warranty(111, 30, item="Netflix")
    # item beda & tak ada wildcard -> None, grant tetap tersimpan
    assert rv.pop_pending_warranty(111, "100 Robux") is None
    assert len(rv.list_pending_warranty(111)) == 1


def test_pop_isolated_per_user(db):
    rv = _rv()
    rv.add_pending_warranty(111, 30)
    # user lain tidak kebagian grant member 111
    assert rv.pop_pending_warranty(222, "apa saja") is None
    assert len(rv.list_pending_warranty(111)) == 1


def test_delete_pending(db):
    rv = _rv()
    gid = rv.add_pending_warranty(111, 30)
    assert rv.delete_pending_warranty(gid) is True
    assert rv.list_pending_warranty(111) == []
    # delete ulang -> False (sudah tidak ada)
    assert rv.delete_pending_warranty(gid) is False


# ── alur lengkap: grant -> reconcile poller -> rating -> sisa garansi ────────────────
def test_manual_warranty_end_to_end(db):
    rv = _rv()
    # 1) admin set pending-grant 30 hari (wildcard) saat tiket masih kebuka
    rv.add_pending_warranty(111, 30, item=None, granted_by=999)
    # 2) transaksi tercatat saat tiket di-close
    db.log_transaction(layanan="lainnya", nominal=50000, item="100 Robux", user_id=111)
    tx = rv.fetch_new_transactions(0)[0]
    rid = rv.create_pending(tx["id"], 111, "lainnya", "100 Robux", 50000)
    # 3) poller reconcile: pasang grant ke review
    grant = rv.pop_pending_warranty(111, tx["item"])
    assert grant is not None
    assert rv.set_review_warranty_days(rid, grant["days"]) is True
    # 4) sebelum rating -> belum bergaransi
    assert rv.has_valid_warranty(111) is False
    # 5) member rating -> garansi aktif, override ikut ter-join
    rv.submit_rating(rid, 5, "mantap")
    wt = rv.get_warranty_transactions(111)
    assert len(wt) == 1 and wt[0]["warranty_days"] == 30

    # 6) sisa garansi dihitung dari rated_at + override 30 hari
    rated_at = wt[0]["rated_at"]
    item = wt[0]["item"]
    # sekarang -> masih aktif
    assert sub.days_remaining(rated_at, item, default_days=7,
                              override_days=wt[0]["warranty_days"]) > 0
    # 20 hari ke depan: dengan override 30 masih aktif, tanpa override (default 7) habis
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=20)
    assert sub.days_remaining(rated_at, item, now=future, default_days=7,
                              override_days=30) > 0
    assert sub.days_remaining(rated_at, item, now=future, default_days=7) < 0
