"""Unit test monitor garansi (utils/warranty_monitor.py + reviews.get_all_warranty_transactions)."""
import datetime

from utils import reviews as rv
from utils import warranty_monitor as wm

NOW = datetime.datetime(2026, 6, 10, tzinfo=datetime.timezone.utc)


def _iso(days_ago):
    return (NOW - datetime.timedelta(days=days_ago)).isoformat()


def _add_rated(db, user_id, item, nominal=10000, rating=5, rated_days_ago=0,
               warranty_days=None, status=rv.STATUS_RATED):
    """Buat baris review berstatus rated/published langsung (tanpa poller)."""
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO reviews (user_id, layanan, item, nominal, rating, status, "
        "created_at, rated_at, warranty_days) VALUES (?,?,?,?,?,?,?,?,?)",
        (user_id, "ml", item, nominal, rating, status,
         _iso(rated_days_ago), _iso(rated_days_ago), warranty_days),
    )
    conn.commit()
    conn.close()


# ── classify (murni) ─────────────────────────────────────────────────────────

def test_classify():
    assert wm.classify(None) == "unlimited"
    assert wm.classify(0) == "expired"
    assert wm.classify(-5) == "expired"
    assert wm.classify(1) == "soon"
    assert wm.classify(7) == "soon"
    assert wm.classify(8) == "active"
    assert wm.classify(3, soon_days=2) == "active"


# ── get_all_warranty_transactions ────────────────────────────────────────────

def test_get_all_empty_when_no_table(db):
    # Tabel reviews belum dibuat -> best-effort kembalikan [].
    assert rv.get_all_warranty_transactions() == []


def test_get_all_only_rated_published(db):
    rv.init_reviews_db()
    _add_rated(db, 1, "Item A", status=rv.STATUS_RATED)
    _add_rated(db, 2, "Item B", status=rv.STATUS_PUBLISHED)
    _add_rated(db, 3, "Item C", status="pending")  # tidak bergaransi
    rows = rv.get_all_warranty_transactions()
    items = {r["item"] for r in rows}
    assert items == {"Item A", "Item B"}
    # user_id ikut terbawa
    assert {r["user_id"] for r in rows} == {1, 2}


# ── list_warranties: durasi & klasifikasi ─────────────────────────────────────

def test_list_warranties_subscription_duration(db):
    rv.init_reviews_db()
    # Item langganan "1 Bulan" (30 hari), dirating 25 hari lalu -> sisa ~5 -> soon.
    _add_rated(db, 1, "CANVA PRO 1 Bulan", rated_days_ago=25)
    # Item langganan "1 Bulan", dirating 2 hari lalu -> sisa ~28 -> active.
    _add_rated(db, 2, "SPOTIFY 1 Bulan", rated_days_ago=2)
    # Item langganan "1 Bulan", dirating 40 hari lalu -> habis.
    _add_rated(db, 3, "NETFLIX 1 Bulan", rated_days_ago=40)

    res = wm.list_warranties(now=NOW)
    by_user = {r["user_id"]: r for r in res}
    assert by_user[1]["status"] == "soon"
    assert by_user[2]["status"] == "active"
    assert by_user[3]["status"] == "expired"
    assert by_user[3]["remaining"] <= 0


def test_list_warranties_default_days_for_nonsub(db):
    rv.init_reviews_db()
    # Item non-langganan -> pakai default_days. default 5, dirating 1 hari lalu -> sisa 4 -> soon.
    _add_rated(db, 1, "100 Robux", rated_days_ago=1)
    res = wm.list_warranties(now=NOW, default_days=5, soon_days=7)
    assert res[0]["status"] == "soon"
    assert res[0]["remaining"] == 4


def test_list_warranties_manual_override(db):
    rv.init_reviews_db()
    # Override 90 hari mengalahkan durasi nama (1 Bulan), dirating 10 hari lalu -> 80 -> active.
    _add_rated(db, 1, "CANVA PRO 1 Bulan", rated_days_ago=10, warranty_days=90)
    res = wm.list_warranties(now=NOW)
    assert res[0]["manual"] is True
    assert res[0]["status"] == "active"
    assert res[0]["remaining"] == 80


def test_list_warranties_unlimited_when_no_duration(db):
    rv.init_reviews_db()
    # Non-langganan + tanpa default -> durasi tak terbaca -> unlimited.
    _add_rated(db, 1, "100 Robux", rated_days_ago=1)
    res = wm.list_warranties(now=NOW, default_days=None)
    assert res[0]["status"] == "unlimited"
    assert res[0]["remaining"] is None


def test_list_warranties_filter_status(db):
    rv.init_reviews_db()
    _add_rated(db, 1, "CANVA PRO 1 Bulan", rated_days_ago=2)    # active
    _add_rated(db, 2, "NETFLIX 1 Bulan", rated_days_ago=40)     # expired
    only_active = wm.list_warranties(now=NOW, status="active")
    assert [r["user_id"] for r in only_active] == [1]
    only_expired = wm.list_warranties(now=NOW, status="expired")
    assert [r["user_id"] for r in only_expired] == [2]


def test_list_warranties_sorted_soonest_first(db):
    rv.init_reviews_db()
    _add_rated(db, 1, "A 1 Bulan", rated_days_ago=2)    # active ~28
    _add_rated(db, 2, "B 1 Bulan", rated_days_ago=27)   # soon ~3
    _add_rated(db, 3, "C 1 Bulan", rated_days_ago=40)   # expired
    res = wm.list_warranties(now=NOW)
    # soon dulu, lalu active, lalu expired
    assert [r["user_id"] for r in res] == [2, 1, 3]


# ── summary ───────────────────────────────────────────────────────────────────

def test_summary(db):
    rv.init_reviews_db()
    _add_rated(db, 1, "A 1 Bulan", rated_days_ago=2)    # active
    _add_rated(db, 2, "B 1 Bulan", rated_days_ago=27)   # soon
    _add_rated(db, 3, "C 1 Bulan", rated_days_ago=40)   # expired
    s = wm.summary(now=NOW)
    assert s["total"] == 3
    assert s["active"] == 1
    assert s["soon"] == 1
    assert s["expired"] == 1
    assert s["unlimited"] == 0


def test_summary_empty(db):
    assert wm.summary(now=NOW) == {"total": 0, "active": 0, "soon": 0, "expired": 0, "unlimited": 0}
