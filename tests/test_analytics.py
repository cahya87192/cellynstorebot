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
