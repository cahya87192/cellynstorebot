"""Analitik penjualan dari transaction_log (untuk halaman Analitik panel admin).

Logika murni (SQLite via utils.db.get_conn) -> gampang diuji. Dipakai
admin_insights.py untuk halaman /analytics: ringkasan multi-periode, omzet per
layanan, dan item terlaris.

Window waktu memakai date('now', ...) SQLite (UTC), konsisten dgn closed_at yang
disimpan dalam ISO UTC.
"""

# Periode yang bisa dipilih di halaman Analitik: (key, days, label).
PERIODS = (("7", 7, "7 Hari"), ("30", 30, "30 Hari"), ("90", 90, "90 Hari"))
DEFAULT_PERIOD = "30"


def resolve_period(key):
    """Validasi `key` periode terhadap allowlist. Return (key, days, label).

    Key tak dikenal / kosong / None -> default (30 hari). Murni (tanpa Flask)
    supaya bisa diuji & dipakai bersama oleh halaman + endpoint export.
    """
    k = (key or "").strip()
    for kk, d, lab in PERIODS:
        if kk == k:
            return kk, d, lab
    for kk, d, lab in PERIODS:
        if kk == DEFAULT_PERIOD:
            return kk, d, lab
    return PERIODS[0]


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


def daily_omzet(days=30):
    """Tren omzet & transaksi harian untuk `days` hari terakhir.

    Mengembalikan deret KONTINU (hari tanpa transaksi tetap muncul dgn 0),
    urut menaik dari (days-1) hari lalu s/d hari ini. Berguna untuk grafik tren.

    Return list of dict {tgl, tx, omzet} dengan tgl = 'YYYY-MM-DD' (UTC).
    """
    import datetime
    from utils.db import get_conn
    n = max(1, int(days))
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT date(closed_at) AS tgl, COUNT(*) AS tx, "
            "COALESCE(SUM(nominal),0) AS omzet FROM transaction_log "
            "WHERE closed_at >= date('now', ?) GROUP BY date(closed_at)",
            [f"-{n - 1} days"],
        ).fetchall()
    finally:
        conn.close()
    by_day = {r["tgl"]: (r["tx"] or 0, r["omzet"] or 0) for r in rows}
    today = datetime.datetime.now(datetime.timezone.utc).date()
    out = []
    for i in range(n - 1, -1, -1):
        d = (today - datetime.timedelta(days=i)).isoformat()
        tx, omzet = by_day.get(d, (0, 0))
        out.append({"tgl": d, "tx": tx, "omzet": omzet})
    return out


def _pct_change(old, new):
    """Persentase perubahan dari `old` ke `new` (1 desimal).

    Return None bila tidak ada baseline (old == 0) -> caller menampilkan
    "baru"/"-" karena pertumbuhan tak terdefinisi.
    """
    if not old:
        return None
    return round((new - old) / old * 100, 1)


def period_comparison(days=30):
    """Bandingkan `days` hari terakhir dengan `days` hari sebelumnya.

    Window saat ini: N hari terakhir (termasuk hari ini).
    Window sebelumnya: N hari tepat sebelum window saat ini.

    Return dict {days, current, previous, omzet_delta, omzet_pct,
    tx_delta, tx_pct} dengan current/previous = {tx, omzet}.
    """
    from utils.db import get_conn
    n = int(days)
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT COUNT(*) AS tx, COALESCE(SUM(nominal),0) AS omzet "
            "FROM transaction_log WHERE closed_at >= date('now', ?)",
            [f"-{n - 1} days"],
        ).fetchone()
        prev = conn.execute(
            "SELECT COUNT(*) AS tx, COALESCE(SUM(nominal),0) AS omzet "
            "FROM transaction_log "
            "WHERE closed_at >= date('now', ?) AND closed_at < date('now', ?)",
            [f"-{2 * n - 1} days", f"-{n - 1} days"],
        ).fetchone()
    finally:
        conn.close()
    current = {"tx": cur["tx"] or 0, "omzet": cur["omzet"] or 0}
    previous = {"tx": prev["tx"] or 0, "omzet": prev["omzet"] or 0}
    return {
        "days": n,
        "current": current,
        "previous": previous,
        "omzet_delta": current["omzet"] - previous["omzet"],
        "omzet_pct": _pct_change(previous["omzet"], current["omzet"]),
        "tx_delta": current["tx"] - previous["tx"],
        "tx_pct": _pct_change(previous["tx"], current["tx"]),
    }


def top_customers(days=30, limit=10):
    """Pelanggan dengan belanja terbesar (urut omzet desc) untuk `days` terakhir.

    Return list of dict {user_id, orders, omzet}. Baris tanpa user_id diabaikan.
    """
    from utils.db import get_conn
    clause, params = _period_clause(days)
    # Hanya baris yang punya user_id.
    if clause:
        clause += " AND user_id IS NOT NULL"
    else:
        clause = " WHERE user_id IS NOT NULL"
    conn = get_conn()
    try:
        rows = conn.execute(
            f"SELECT user_id, COUNT(*) AS orders, COALESCE(SUM(nominal),0) AS omzet "
            f"FROM transaction_log{clause} GROUP BY user_id "
            f"ORDER BY omzet DESC, orders DESC LIMIT ?",
            params + [int(limit)],
        ).fetchall()
    finally:
        conn.close()
    return [
        {"user_id": r["user_id"], "orders": r["orders"] or 0, "omzet": r["omzet"] or 0}
        for r in rows
    ]


def peak_hours(days=30, limit=5):
    """Jam tersibuk berdasarkan jumlah transaksi untuk `days` terakhir.

    Mengelompokkan transaksi per jam (UTC, dari closed_at) lalu mengurutkan
    dari yang paling ramai. days=None -> all-time. Return list of dict
    {jam, tx, omzet} dengan jam = int 0..23 (urut tx desc, lalu jam asc).
    """
    from utils.db import get_conn
    clause, params = _period_clause(days)
    # strftime() pada NULL menghasilkan NULL -> buang baris tanpa closed_at.
    if clause:
        clause += " AND closed_at IS NOT NULL"
    else:
        clause = " WHERE closed_at IS NOT NULL"
    conn = get_conn()
    try:
        rows = conn.execute(
            f"SELECT CAST(strftime('%H', closed_at) AS INTEGER) AS jam, "
            f"COUNT(*) AS tx, COALESCE(SUM(nominal),0) AS omzet "
            f"FROM transaction_log{clause} "
            f"GROUP BY jam ORDER BY tx DESC, jam ASC LIMIT ?",
            params + [int(limit)],
        ).fetchall()
    finally:
        conn.close()
    return [
        {"jam": r["jam"], "tx": r["tx"] or 0, "omzet": r["omzet"] or 0}
        for r in rows if r["jam"] is not None
    ]


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
