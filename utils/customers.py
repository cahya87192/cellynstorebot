"""Direktori pelanggan (CRM ringan) untuk admin panel.

Agregasi per-member dari `transaction_log` (jumlah order, total belanja, order
pertama & terakhir) digabung dengan cache nama (`member_names`) supaya bisa
dicari & ditampilkan dengan nama yang ramah, bukan ID mentah.

Berbeda dengan:
  - `utils.customer_insight` -> ringkasan SATU member saat tiket dibuka (bot).
  - `utils.analytics.top_customers` -> hanya Top-N untuk halaman Analitik.

Halaman /customers (admin_insights.py) butuh daftar LENGKAP yang bisa dicari,
diurutkan, dan dipaginasi. Logika murni di sini (SQLite via utils.db.get_conn)
supaya gampang diuji tanpa Flask/Discord.
"""

# Opsi urutan: key -> (klausa ORDER BY, label tampilan).
SORTS = {
    "omzet": ("omzet DESC, orders DESC", "Belanja tertinggi"),
    "orders": ("orders DESC, omzet DESC", "Order terbanyak"),
    "recent": ("last_at DESC", "Order terbaru"),
    "oldest": ("first_at ASC", "Pelanggan terlama"),
    "name": ("name IS NULL, name COLLATE NOCASE ASC", "Nama (A-Z)"),
}
DEFAULT_SORT = "omzet"


def resolve_sort(key):
    """Validasi `key` urutan terhadap allowlist. Return (key, order_sql, label).

    Key tak dikenal/kosong/None -> default (omzet). Murni & testable; mencegah
    nilai liar masuk ke klausa ORDER BY (anti SQL-injection).
    """
    k = (key or "").strip()
    if k in SORTS:
        order, label = SORTS[k]
        return k, order, label
    order, label = SORTS[DEFAULT_SORT]
    return DEFAULT_SORT, order, label


def _ensure_names_table(conn):
    """Pastikan tabel member_names ada (LEFT JOIN gagal bila belum dibuat)."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS member_names "
        "(user_id TEXT PRIMARY KEY, name TEXT, updated_at TEXT)"
    )


def _search_clause(search):
    """(extra_where, params) untuk pencarian by nama atau ID. Kosong -> ('', [])."""
    s = (search or "").strip()
    if not s:
        return "", []
    like = f"%{s}%"
    return " AND (m.name LIKE ? OR CAST(t.user_id AS TEXT) LIKE ?)", [like, like]


def count_customers(search=""):
    """Jumlah pelanggan unik (punya user_id) yang cocok dengan `search`."""
    from utils.db import get_conn
    extra, params = _search_clause(search)
    conn = get_conn()
    try:
        _ensure_names_table(conn)
        row = conn.execute(
            f"SELECT COUNT(*) AS n FROM ("
            f"  SELECT t.user_id FROM transaction_log t "
            f"  LEFT JOIN member_names m ON m.user_id = CAST(t.user_id AS TEXT) "
            f"  WHERE t.user_id IS NOT NULL{extra} GROUP BY t.user_id"
            f")",
            params,
        ).fetchone()
    finally:
        conn.close()
    return int(row["n"] or 0)


def list_customers(search="", sort=DEFAULT_SORT, limit=20, offset=0):
    """Daftar pelanggan teragregasi (dengan nama bila ter-cache).

    Return list of dict {user_id, name, orders, omzet, first_at, last_at}.
    `name` = None bila belum ter-cache. Diurutkan sesuai `sort` (allowlist),
    dipaginasi via limit/offset.
    """
    from utils.db import get_conn
    _key, order, _label = resolve_sort(sort)
    extra, params = _search_clause(search)
    conn = get_conn()
    try:
        _ensure_names_table(conn)
        rows = conn.execute(
            f"SELECT t.user_id AS user_id, MAX(m.name) AS name, "
            f"  COUNT(*) AS orders, COALESCE(SUM(t.nominal),0) AS omzet, "
            f"  MIN(t.closed_at) AS first_at, MAX(t.closed_at) AS last_at "
            f"FROM transaction_log t "
            f"LEFT JOIN member_names m ON m.user_id = CAST(t.user_id AS TEXT) "
            f"WHERE t.user_id IS NOT NULL{extra} "
            f"GROUP BY t.user_id ORDER BY {order} LIMIT ? OFFSET ?",
            params + [int(limit), int(offset)],
        ).fetchall()
    finally:
        conn.close()
    return [
        {"user_id": r["user_id"], "name": r["name"], "orders": r["orders"] or 0,
         "omzet": r["omzet"] or 0, "first_at": r["first_at"], "last_at": r["last_at"]}
        for r in rows
    ]


def stats():
    """Ringkasan direktori: {total, repeat, single, omzet}.

    - total  : pelanggan unik
    - repeat : pelanggan dengan >= 2 order (pelanggan berulang)
    - single : pelanggan dengan tepat 1 order
    - omzet  : total belanja semua pelanggan (yg punya user_id)
    """
    from utils.db import get_conn
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS total, "
            "  COALESCE(SUM(CASE WHEN n >= 2 THEN 1 ELSE 0 END),0) AS repeat_, "
            "  COALESCE(SUM(CASE WHEN n = 1 THEN 1 ELSE 0 END),0) AS single, "
            "  COALESCE(SUM(omzet),0) AS omzet FROM ("
            "  SELECT user_id, COUNT(*) AS n, SUM(nominal) AS omzet "
            "  FROM transaction_log WHERE user_id IS NOT NULL GROUP BY user_id"
            ")"
        ).fetchone()
    finally:
        conn.close()
    return {
        "total": int(row["total"] or 0),
        "repeat": int(row["repeat_"] or 0),
        "single": int(row["single"] or 0),
        "omzet": int(row["omzet"] or 0),
    }
