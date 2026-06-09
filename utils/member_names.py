"""Cache nama tampilan member Discord (id -> nama) untuk admin panel.

Panel admin (Flask) tidak punya akses gateway Discord, jadi statistik yang
berhubungan dgn member/admin selama ini cuma menampilkan ID mentah. Modul ini
menyimpan pemetaan `user_id -> display_name` di SQLite (tabel `member_names`)
yang DIISI oleh bot (cogs/member_sync.py) dan DIBACA oleh panel untuk menampilkan
nama yang ramah.

Self-contained (hanya SQLite), gampang diuji tanpa discord. Semua operasi
best-effort: gagal baca/tulis cache tidak boleh menggagalkan apa pun.
"""
import datetime


def _ensure_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS member_names (
            user_id    TEXT PRIMARY KEY,
            name       TEXT,
            updated_at TEXT
        )
        """
    )


def set_name(user_id, name):
    """Simpan/update satu nama. Return True bila tersimpan."""
    if user_id is None or not name:
        return False
    try:
        from utils.db import get_conn
        conn = get_conn()
        _ensure_table(conn)
        conn.execute(
            "INSERT OR REPLACE INTO member_names (user_id, name, updated_at) VALUES (?,?,?)",
            (str(user_id), str(name),
             datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def bulk_set(mapping):
    """Simpan banyak nama sekaligus ({id: nama}). Return jumlah baris ditulis."""
    if not mapping:
        return 0
    try:
        from utils.db import get_conn
        conn = get_conn()
        _ensure_table(conn)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        n = 0
        for uid, name in mapping.items():
            if uid is None or not name:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO member_names (user_id, name, updated_at) VALUES (?,?,?)",
                (str(uid), str(name), now),
            )
            n += 1
        conn.commit()
        conn.close()
        return n
    except Exception:
        return 0


def get_name(user_id):
    """Nama untuk satu id, atau None bila belum ada di cache."""
    if user_id is None:
        return None
    try:
        from utils.db import get_conn
        conn = get_conn()
        _ensure_table(conn)
        row = conn.execute(
            "SELECT name FROM member_names WHERE user_id=?", (str(user_id),)
        ).fetchone()
        conn.close()
        return row["name"] if row else None
    except Exception:
        return None


def name_map(user_ids):
    """Pemetaan {str(id): nama} untuk id yang ada di cache (abaikan yg kosong)."""
    ids = {str(u) for u in user_ids if u is not None and str(u) != ""}
    out = {}
    if not ids:
        return out
    try:
        from utils.db import get_conn
        conn = get_conn()
        _ensure_table(conn)
        marks = ",".join("?" * len(ids))
        rows = conn.execute(
            f"SELECT user_id, name FROM member_names WHERE user_id IN ({marks})",
            tuple(ids),
        ).fetchall()
        for r in rows:
            out[r["user_id"]] = r["name"]
        conn.close()
    except Exception:
        pass
    return out


def display(user_id, default=None):
    """Nama bila ada; kalau tidak, `default` (atau str(id))."""
    if user_id is None:
        return default if default is not None else ""
    nm = get_name(user_id)
    if nm:
        return nm
    return default if default is not None else str(user_id)


def count():
    """Jumlah entri cache."""
    try:
        from utils.db import get_conn
        conn = get_conn()
        _ensure_table(conn)
        n = conn.execute("SELECT COUNT(*) AS n FROM member_names").fetchone()["n"]
        conn.close()
        return int(n)
    except Exception:
        return 0
