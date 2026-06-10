"""Unit test analitik penjualan (utils/analytics.py)."""
import datetime

from utils import analytics


def _ins(db, layanan, nominal, item=None, qty=1, days_ago=0):
    """Sisipkan satu baris transaction_log dengan closed_at `days_ago` hari lalu."""
    closed = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=days_ago)).isoformat()
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO transaction_log (layanan, nominal, item, qty, closed_at) "
        "VALUES (?,?,?,?,?)",
        (layanan, nominal, item, qty, closed),
    )
    conn.commit()
    conn.close()


def test_period_summary_empty(db):
    s = analytics.period_summary()
    assert set(s) == {"today", "d7", "d30", "all"}
    for v in s.values():
        assert v == {"tx": 0, "omzet": 0}


def test_period_summary_windows(db):
    _ins(db, "ml", 10000, "ML 100", days_ago=0)      # hari ini
    _ins(db, "robux", 20000, "Robux", days_ago=3)    # dalam 7 & 30 hari
    _ins(db, "gp", 50000, "GP", days_ago=20)         # dalam 30 hari saja
    _ins(db, "vilog", 99000, "Vilog", days_ago=100)  # all-time saja

    s = analytics.period_summary()
    assert s["today"] == {"tx": 1, "omzet": 10000}
    assert s["d7"] == {"tx": 2, "omzet": 30000}
    assert s["d30"] == {"tx": 3, "omzet": 80000}
    assert s["all"] == {"tx": 4, "omzet": 179000}


def test_omzet_by_layanan_sorted(db):
    _ins(db, "ml", 5000, "a", days_ago=1)
    _ins(db, "ml", 5000, "b", days_ago=2)
    _ins(db, "robux", 50000, "c", days_ago=1)
    res = analytics.omzet_by_layanan(days=30)
    assert res[0]["layanan"] == "robux" and res[0]["omzet"] == 50000
    ml = next(r for r in res if r["layanan"] == "ml")
    assert ml["tx"] == 2 and ml["omzet"] == 10000


def test_omzet_by_layanan_excludes_old(db):
    _ins(db, "ml", 5000, "a", days_ago=1)
    _ins(db, "gp", 9000, "old", days_ago=60)
    res = analytics.omzet_by_layanan(days=30)
    labels = {r["layanan"] for r in res}
    assert "ml" in labels and "gp" not in labels
    # all-time mencakup gp
    res_all = analytics.omzet_by_layanan(days=None)
    assert "gp" in {r["layanan"] for r in res_all}


def test_top_items(db):
    _ins(db, "ml", 10000, "Diamond 100", qty=2, days_ago=0)
    _ins(db, "ml", 10000, "Diamond 100", qty=3, days_ago=1)
    _ins(db, "robux", 20000, "Robux 1000", qty=1, days_ago=2)
    res = analytics.top_items(days=30, limit=10)
    top = res[0]
    assert top["item"] == "Diamond 100"
    assert top["orders"] == 2 and top["qty"] == 5 and top["omzet"] == 20000


def test_top_items_ignores_null_item(db):
    _ins(db, "ml", 10000, None, days_ago=0)
    _ins(db, "ml", 10000, "", days_ago=0)
    _ins(db, "ml", 10000, "Real", days_ago=0)
    res = analytics.top_items(days=30)
    items = [r["item"] for r in res]
    assert items == ["Real"]


def test_top_items_limit(db):
    for i in range(8):
        _ins(db, "ml", 1000, f"item{i}", days_ago=0)
    assert len(analytics.top_items(days=30, limit=3)) == 3



def _ins_user(db, layanan, nominal, user_id, days_ago=0):
    """Sisipkan transaction_log dgn user_id, closed_at `days_ago` hari lalu."""
    closed = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=days_ago)).isoformat()
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO transaction_log (layanan, nominal, user_id, closed_at) "
        "VALUES (?,?,?,?)",
        (layanan, nominal, user_id, closed),
    )
    conn.commit()
    conn.close()


def test_pct_change():
    assert analytics._pct_change(0, 0) is None
    assert analytics._pct_change(0, 100) is None  # tanpa baseline
    assert analytics._pct_change(100, 150) == 50.0
    assert analytics._pct_change(100, 50) == -50.0
    assert analytics._pct_change(100, 100) == 0.0


def test_period_comparison_empty(db):
    c = analytics.period_comparison(days=30)
    assert c["days"] == 30
    assert c["current"] == {"tx": 0, "omzet": 0}
    assert c["previous"] == {"tx": 0, "omzet": 0}
    assert c["omzet_pct"] is None and c["tx_pct"] is None
    assert c["omzet_delta"] == 0 and c["tx_delta"] == 0


def test_period_comparison_windows(db):
    # Window saat ini (0..29 hari lalu)
    _ins(db, "ml", 100000, "a", days_ago=1)
    _ins(db, "ml", 50000, "b", days_ago=10)
    # Window sebelumnya (30..59 hari lalu)
    _ins(db, "robux", 60000, "c", days_ago=35)
    # Lebih tua dari kedua window -> diabaikan
    _ins(db, "gp", 999999, "old", days_ago=120)

    c = analytics.period_comparison(days=30)
    assert c["current"] == {"tx": 2, "omzet": 150000}
    assert c["previous"] == {"tx": 1, "omzet": 60000}
    assert c["omzet_delta"] == 90000
    assert c["omzet_pct"] == 150.0
    assert c["tx_delta"] == 1
    assert c["tx_pct"] == 100.0


def test_top_customers_sorted(db):
    _ins_user(db, "ml", 50000, 111, days_ago=1)
    _ins_user(db, "ml", 30000, 111, days_ago=2)   # user 111 total 80000, 2 order
    _ins_user(db, "robux", 100000, 222, days_ago=1)  # user 222 total 100000, 1 order
    res = analytics.top_customers(days=30, limit=10)
    assert res[0]["user_id"] == 222 and res[0]["omzet"] == 100000
    u111 = next(r for r in res if r["user_id"] == 111)
    assert u111["orders"] == 2 and u111["omzet"] == 80000


def test_top_customers_excludes_old_and_limit(db):
    _ins_user(db, "ml", 10000, 1, days_ago=1)
    _ins_user(db, "ml", 20000, 2, days_ago=2)
    _ins_user(db, "ml", 30000, 3, days_ago=3)
    _ins_user(db, "gp", 99000, 9, days_ago=60)  # di luar 30 hari
    res = analytics.top_customers(days=30, limit=2)
    assert len(res) == 2
    ids = {r["user_id"] for r in res}
    assert 9 not in ids
    # all-time mencakup user lama
    res_all = analytics.top_customers(days=None, limit=10)
    assert 9 in {r["user_id"] for r in res_all}


def test_top_customers_ignores_null_user(db):
    _ins(db, "ml", 10000, "no-user", days_ago=0)  # user_id NULL
    _ins_user(db, "ml", 20000, 42, days_ago=0)
    res = analytics.top_customers(days=30)
    assert [r["user_id"] for r in res] == [42]



def test_daily_omzet_length_and_order(db):
    res = analytics.daily_omzet(days=7)
    assert len(res) == 7
    tgls = [r["tgl"] for r in res]
    assert tgls == sorted(tgls)  # menaik
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    assert res[-1]["tgl"] == today  # elemen terakhir = hari ini


def test_daily_omzet_fills_zero_days(db):
    # Transaksi hanya di hari ini dan 3 hari lalu; sisanya harus 0 (kontinu).
    _ins(db, "ml", 10000, days_ago=0)
    _ins(db, "ml", 5000, days_ago=0)
    _ins(db, "robux", 20000, days_ago=3)
    res = analytics.daily_omzet(days=7)
    by_day = {r["tgl"]: r for r in res}
    assert len(res) == 7
    # total omzet keseluruhan deret
    assert sum(r["omzet"] for r in res) == 35000
    assert sum(r["tx"] for r in res) == 3
    today = datetime.datetime.now(datetime.timezone.utc).date()
    t0 = today.isoformat()
    t3 = (today - datetime.timedelta(days=3)).isoformat()
    t1 = (today - datetime.timedelta(days=1)).isoformat()
    assert by_day[t0] == {"tgl": t0, "tx": 2, "omzet": 15000}
    assert by_day[t3] == {"tgl": t3, "tx": 1, "omzet": 20000}
    assert by_day[t1] == {"tgl": t1, "tx": 0, "omzet": 0}  # hari kosong terisi 0


def test_daily_omzet_excludes_outside_window(db):
    _ins(db, "gp", 99000, days_ago=10)  # di luar 7 hari
    res = analytics.daily_omzet(days=7)
    assert len(res) == 7
    assert sum(r["omzet"] for r in res) == 0
