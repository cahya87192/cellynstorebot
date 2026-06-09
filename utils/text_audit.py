"""Audit log perubahan teks bot (kapan & apa yang diubah dari panel admin).

Mencatat tiap aksi simpan/reset teks editor + import/reset-massal backup, supaya
admin punya jejak histori. Panel admin pakai 1 password bersama (tanpa identitas
per-user), jadi yang dicatat fokus ke *kapan* + *apa* (bukan *siapa*).

Modul ini self-contained, hanya menyentuh SQLite -> gampang diuji. Semua tulis
dibungkus aman: kegagalan mencatat TIDAK boleh menggagalkan aksi simpan.
"""
import datetime

MAX_DETAIL = 120


def _ensure_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS text_audit_log (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            ts     TEXT,
            action TEXT,
            key    TEXT,
            kind   TEXT,
            label  TEXT,
            detail TEXT
        )
        """
    )


def record(action, *, key=None, kind=None, label=None, detail=None):
    """Catat satu entri audit. Aman: error apa pun ditelan (return False)."""
    try:
        from utils.db import get_conn
        conn = get_conn()
        _ensure_table(conn)
        if detail is not None:
            detail = str(detail)
            if len(detail) > MAX_DETAIL:
                detail = detail[:MAX_DETAIL] + "…"
        conn.execute(
            "INSERT INTO text_audit_log (ts, action, key, kind, label, detail) "
            "VALUES (?,?,?,?,?,?)",
            (
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
                str(action), key, kind, label, detail,
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def recent(limit=200):
    """Ambil entri terbaru (urut terbaru dulu)."""
    rows_out = []
    try:
        from utils.db import get_conn
        conn = get_conn()
        _ensure_table(conn)
        rows = conn.execute(
            "SELECT id, ts, action, key, kind, label, detail "
            "FROM text_audit_log ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        for r in rows:
            rows_out.append({
                "id": r["id"], "ts": r["ts"], "action": r["action"],
                "key": r["key"], "kind": r["kind"], "label": r["label"],
                "detail": r["detail"],
            })
        conn.close()
    except Exception:
        pass
    return rows_out


def count():
    """Jumlah entri audit."""
    try:
        from utils.db import get_conn
        conn = get_conn()
        _ensure_table(conn)
        n = conn.execute("SELECT COUNT(*) AS n FROM text_audit_log").fetchone()["n"]
        conn.close()
        return int(n)
    except Exception:
        return 0


def clear():
    """Hapus seluruh log audit. Return jumlah yang dihapus."""
    try:
        from utils.db import get_conn
        conn = get_conn()
        _ensure_table(conn)
        cur = conn.execute("DELETE FROM text_audit_log")
        removed = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        conn.commit()
        conn.close()
        return removed
    except Exception:
        return 0
