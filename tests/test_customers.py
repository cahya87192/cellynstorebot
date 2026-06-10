"""Unit test direktori pelanggan (utils/customers.py)."""
import datetime

from utils import customers, member_names


def _ins(db, nominal, user_id, days_ago=0):
    """Sisipkan transaction_log dgn user_id & closed_at `days_ago` hari lalu."""
    closed = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=days_ago)).isoformat()
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO transaction_log (layanan, nominal, user_id, closed_at) "
        "VALUES (?,?,?,?)",
        ("ml", nominal, user_id, closed),
    )
    conn.commit()
    conn.close()


# ── resolve_sort (murni) ────────────────────────────────────────────────────

def test_resolve_sort_valid():
    for key in customers.SORTS:
        k, order, label = customers.resolve_sort(key)
        assert k == key
        assert order == customers.SORTS[key][0]
        assert label == customers.SORTS[key][1]


def test_resolve_sort_defaults():
    for bad in (None, "", "  ", "bogus", "DROP TABLE", "123"):
        k, order, _ = customers.resolve_sort(bad)
        assert k == customers.DEFAULT_SORT
        assert order == customers.SORTS[customers.DEFAULT_SORT][0]


# ── agregasi ────────────────────────────────────────────────────────────────

def test_list_customers_empty(db):
    assert customers.list_customers() == []
    assert customers.count_customers() == 0


def test_list_aggregates_and_sorts_by_omzet(db):
    _ins(db, 50000, 111, days_ago=1)
    _ins(db, 30000, 111, days_ago=2)   # user 111: 2 order, 80000
    _ins(db, 100000, 222, days_ago=1)  # user 222: 1 order, 100000
    res = customers.list_customers(sort="omzet")
    assert [r["user_id"] for r in res] == [222, 111]
    u111 = next(r for r in res if r["user_id"] == 111)
    assert u111["orders"] == 2 and u111["omzet"] == 80000
    assert customers.count_customers() == 2


def test_sort_by_orders_and_recent(db):
    _ins(db, 10000, 1, days_ago=10)
    _ins(db, 10000, 1, days_ago=9)
    _ins(db, 10000, 1, days_ago=8)    # user 1: 3 order, terakhir 8 hari lalu
    _ins(db, 90000, 2, days_ago=0)    # user 2: 1 order, terakhir hari ini
    by_orders = customers.list_customers(sort="orders")
    assert by_orders[0]["user_id"] == 1
    by_recent = customers.list_customers(sort="recent")
    assert by_recent[0]["user_id"] == 2


def test_ignores_null_user(db):
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO transaction_log (layanan, nominal, user_id, closed_at) "
        "VALUES ('ml', 5000, NULL, ?)",
        (datetime.datetime.now(datetime.timezone.utc).isoformat(),),
    )
    conn.commit()
    conn.close()
    _ins(db, 7000, 42, days_ago=0)
    res = customers.list_customers()
    assert [r["user_id"] for r in res] == [42]


def test_pagination(db):
    for uid in range(1, 6):
        _ins(db, uid * 1000, uid, days_ago=0)
    assert customers.count_customers() == 5
    p1 = customers.list_customers(sort="omzet", limit=2, offset=0)
    p2 = customers.list_customers(sort="omzet", limit=2, offset=2)
    assert len(p1) == 2 and len(p2) == 2
    # tidak ada tumpang tindih
    assert {r["user_id"] for r in p1}.isdisjoint({r["user_id"] for r in p2})


# ── join nama + pencarian ─────────────────────────────────────────────────────

def test_name_join_and_search(db):
    _ins(db, 50000, 111, days_ago=1)
    _ins(db, 20000, 222, days_ago=1)
    member_names.set_name(111, "Budi Santoso")
    member_names.set_name(222, "Caca")

    res = customers.list_customers()
    names = {r["user_id"]: r["name"] for r in res}
    assert names[111] == "Budi Santoso"
    assert names[222] == "Caca"

    # cari berdasarkan nama
    by_name = customers.list_customers(search="budi")
    assert [r["user_id"] for r in by_name] == [111]
    assert customers.count_customers(search="budi") == 1

    # cari berdasarkan ID
    by_id = customers.list_customers(search="222")
    assert [r["user_id"] for r in by_id] == [222]


def test_name_none_when_not_cached(db):
    _ins(db, 1000, 999, days_ago=0)
    res = customers.list_customers()
    assert res[0]["name"] is None


# ── stats ───────────────────────────────────────────────────────────────────

def test_stats(db):
    _ins(db, 50000, 1, days_ago=1)
    _ins(db, 30000, 1, days_ago=2)   # repeat
    _ins(db, 20000, 2, days_ago=1)   # single
    _ins(db, 10000, 3, days_ago=1)   # single
    s = customers.stats()
    assert s["total"] == 3
    assert s["repeat"] == 1
    assert s["single"] == 2
    assert s["omzet"] == 110000


def test_stats_empty(db):
    assert customers.stats() == {"total": 0, "repeat": 0, "single": 0, "omzet": 0}
