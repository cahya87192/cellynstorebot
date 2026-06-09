"""Analitik penjualan dari transaction_log (untuk halaman Analitik panel admin).

Logika murni (SQLite via utils.db.get_conn) -> gampang diuji. Dipakai
admin_insights.py untuk halaman /analytics: ringkasan multi-periode, omzet per
layanan, dan item terlaris.

Window waktu memakai date('now', ...) SQLite (UTC), konsisten dgn closed_at yang
disimpan dalam ISO UTC.
"""


def _period_clause(days):
    """Kembalikan (sql_clause, params) untuk filter `days` terakhir.

    days=None -> tanpa filter (all-time). days=1 -> hanya hari ini.
    """
    if days is None:
        return "", []
    # N hari terakhir termasuk hari ini -> mulai dari (N-1) hari lalu.
    return " WHERE closed_at >= date('now', ?)", [f"-{int(days) - 1} days"]


def _one_period(conn, days):
    clause, params = _period_clause(days)
    row = conn.execute(
        f"SELECT COUNT(*) AS tx, COALESCE(SUM(nominal),0) AS omzet "
        f"FROM transaction_log{clause}",
        params,
    ).fetchone()
    return {"tx": row["tx"] or 0, "omzet": row["omzet"] or 0}


def period_summary():
    """Ringkasan {today,d7,d30,all} -> masing-masing {tx, omzet}."""
    from utils.db import get_conn
    conn = get_conn()
    try:
        out = {
            "today": _one_period(conn, 1),
            "d7": _one_period(conn, 7),
            "d30": _one_period(conn, 30),
            "all": _one_period(conn, None),
        }
    finally:
        conn.close()
    return out


def omzet_by_layanan(days=30):
    """List omzet per layanan (urut omzet desc) untuk `days` terakhir.

    Return list of dict {layanan, tx, omzet}.
    """
    from utils.db import get_conn
    clause, params = _period_clause(days)
    conn = get_conn()
    try:
        rows = conn.execute(
            f"SELECT COALESCE(layanan,'-') AS layanan, COUNT(*) AS tx, "
            f"COALESCE(SUM(nominal),0) AS omzet FROM transaction_log{clause} "
            f"GROUP BY layanan ORDER BY omzet DESC",
            params,
        ).fetchall()
    finally:
        conn.close()
    return [{"layanan": r["layanan"], "tx": r["tx"] or 0, "omzet": r["omzet"] or 0} for r in rows]


def top_items(days=30, limit=10):
    """Item paling laku (urut jumlah order desc) untuk `days` terakhir.

    Return list of dict {item, orders, qty, omzet}.
    """
    from utils.db import get_conn
    clause, params = _period_clause(days)
    # Hanya baris yang punya item.
    if clause:
        clause += " AND item IS NOT NULL AND item <> ''"
    else:
        clause = " WHERE item IS NOT NULL AND item <> ''"
    conn = get_conn()
    try:
        rows = conn.execute(
            f"SELECT item, COUNT(*) AS orders, COALESCE(SUM(qty),0) AS qty, "
            f"COALESCE(SUM(nominal),0) AS omzet FROM transaction_log{clause} "
            f"GROUP BY item ORDER BY orders DESC, omzet DESC LIMIT ?",
            params + [int(limit)],
        ).fetchall()
    finally:
        conn.close()
    return [
        {"item": r["item"], "orders": r["orders"] or 0,
         "qty": r["qty"] or 0, "omzet": r["omzet"] or 0}
        for r in rows
    ]
