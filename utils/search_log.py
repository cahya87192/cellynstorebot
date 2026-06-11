"""Log pencarian produk yang TIDAK menemukan hasil (demand insight).

Channel pencarian (cogs/product_search.py) memanggil :func:`log_miss` tiap kali
member mengetik query yang dianggap pencarian produk tapi tidak menghasilkan
kecocokan kuat. Data diagregasi per-query (key ternormalisasi) supaya panel
admin bisa menampilkan "paling sering dicari tapi belum ada" — petunjuk
permintaan yang belum tersedia di katalog.

Tabel: search_misses
    query_key      TEXT PRIMARY KEY  -- bentuk ternormalisasi+alias (kunci agregasi)
    last_query     TEXT              -- query asli terakhir (apa adanya, dipangkas)
    count          INTEGER           -- berapa kali dicari
    had_suggestion INTEGER           -- 1 bila pernah ada saran "mirip" (produk dekat)
    first_at       TEXT              -- ISO8601 UTC pertama kali
    last_at        TEXT              -- ISO8601 UTC terakhir
    last_user      INTEGER           -- user id terakhir yang mencari
"""

import datetime

from utils.db import get_conn


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _ensure(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS search_misses (
            query_key      TEXT PRIMARY KEY,
            last_query     TEXT NOT NULL,
            count          INTEGER NOT NULL DEFAULT 0,
            had_suggestion INTEGER NOT NULL DEFAULT 0,
            first_at       TEXT NOT NULL,
            last_at        TEXT NOT NULL,
            last_user      INTEGER
        )"""
    )


def log_miss(query_key, last_query=None, user_id=None, had_suggestion=False):
    """Catat 1 kejadian pencarian nihil (upsert + increment count).

    query_key  : kunci agregasi (ternormalisasi). Wajib non-kosong.
    last_query : query asli yang diketik member (buat ditampilkan). Default = key.
    """
    key = (query_key or "").strip()
    if not key:
        return
    shown = ((last_query if last_query is not None else key) or "").strip()[:200] or key
    now = _now()
    sug = 1 if had_suggestion else 0
    conn = get_conn()
    try:
        _ensure(conn)
        c = conn.cursor()
        c.execute("SELECT 1 FROM search_misses WHERE query_key=?", (key,))
        if c.fetchone():
            c.execute(
                """UPDATE search_misses
                   SET count = count + 1,
                       last_query = ?,
                       last_at = ?,
                       last_user = ?,
                       had_suggestion = MAX(had_suggestion, ?)
                   WHERE query_key = ?""",
                (shown, now, user_id, sug, key),
            )
        else:
            c.execute(
                """INSERT INTO search_misses
                   (query_key, last_query, count, had_suggestion, first_at, last_at, last_user)
                   VALUES (?,?,?,?,?,?,?)""",
                (key, shown, 1, sug, now, now, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def top_misses(limit=300):
    """Daftar pencarian nihil, terurut paling sering & terbaru."""
    conn = get_conn()
    try:
        _ensure(conn)
        c = conn.cursor()
        c.execute(
            """SELECT query_key, last_query, count, had_suggestion, first_at, last_at, last_user
               FROM search_misses
               ORDER BY count DESC, last_at DESC
               LIMIT ?""",
            (int(limit),),
        )
        return [dict(r) for r in c.fetchall()]
    finally:
        conn.close()


def stats():
    """Kembalikan (total_kejadian, jumlah_query_unik)."""
    conn = get_conn()
    try:
        _ensure(conn)
        c = conn.cursor()
        c.execute("SELECT COALESCE(SUM(count), 0), COUNT(*) FROM search_misses")
        row = c.fetchone()
        return (int(row[0] or 0), int(row[1] or 0))
    finally:
        conn.close()


def delete_miss(query_key):
    """Hapus satu entri. Return True bila ada baris terhapus."""
    conn = get_conn()
    try:
        _ensure(conn)
        c = conn.cursor()
        c.execute("DELETE FROM search_misses WHERE query_key=?", ((query_key or "").strip(),))
        changed = c.rowcount
        conn.commit()
        return changed > 0
    finally:
        conn.close()


def clear_all():
    """Hapus semua entri. Return jumlah baris terhapus."""
    conn = get_conn()
    try:
        _ensure(conn)
        c = conn.cursor()
        c.execute("DELETE FROM search_misses")
        n = c.rowcount
        conn.commit()
        return n
    finally:
        conn.close()
