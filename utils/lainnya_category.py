"""Logika murni CRUD info kategori Layanan Lainnya (deskripsi & S&K).

Cog `cogs/lainnya.py` menyimpan deskripsi + Syarat & Ketentuan per kategori di
tabel `lainnya_category_info` (di-seed dari cogs/lainnya_catalog.CATEGORY_INFO).
Modul ini menyediakan helper untuk panel admin agar bisa LIST / EDIT / RESET info
tiap kategori TANPA edit kode.

Konsistensi dengan cog:
  - `load_info()` mengembalikan nilai DB bila ada (deskripsi/terms terisi), kalau
    tidak fallback ke default statis (sama seperti cogs.lainnya.load_category_info).
  - `reset_info()` menghapus baris DB sehingga cog kembali memakai default statis.

Modul ini hanya menyentuh SQLite + data statis murni (lainnya_catalog tidak
meng-import discord) -> gampang diuji tanpa discord.
"""

from cogs import lainnya_catalog


def _ensure_table(conn):
    """Pastikan tabel ada (schema sama dgn cogs/lainnya.py). Idempotent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lainnya_category_info (
            category    TEXT PRIMARY KEY,
            description TEXT,
            terms       TEXT
        )
        """
    )


def default_info(category):
    """Default statis {'description','terms'} dari lainnya_catalog."""
    return lainnya_catalog.get_category_info(category)


def list_categories():
    """Semua nama kategori (gabungan data statis + tabel DB), urut alfabet, unik."""
    cats = set(lainnya_catalog.CATEGORY_INFO.keys())
    from utils.db import get_conn
    conn = get_conn()
    try:
        _ensure_table(conn)
        for r in conn.execute("SELECT category FROM lainnya_category_info"):
            cats.add(r["category"])
        for r in conn.execute("SELECT DISTINCT category FROM lainnya_products"):
            cats.add(r["category"])
    except Exception:
        pass
    conn.close()
    return sorted(cats)


def load_info(category):
    """Info kategori: nilai DB bila terisi, kalau tidak default statis.

    Mengikuti perilaku cogs.lainnya.load_category_info.
    """
    from utils.db import get_conn
    row = None
    conn = get_conn()
    try:
        _ensure_table(conn)
        cur = conn.execute(
            "SELECT description, terms FROM lainnya_category_info WHERE category=?",
            (category,),
        )
        row = cur.fetchone()
    except Exception:
        pass
    conn.close()
    if row and (row["description"] or row["terms"]):
        return {"description": row["description"] or "", "terms": row["terms"] or ""}
    return default_info(category)


def save_info(category, description=None, terms=None):
    """Simpan deskripsi & S&K kategori (upsert). None -> string kosong."""
    from utils.db import get_conn
    conn = get_conn()
    _ensure_table(conn)
    conn.execute(
        "INSERT OR REPLACE INTO lainnya_category_info (category, description, terms) VALUES (?,?,?)",
        (category, description or "", terms or ""),
    )
    conn.commit()
    conn.close()


def reset_info(category):
    """Hapus baris DB -> cog kembali memakai default statis. Kembalikan default."""
    from utils.db import get_conn
    conn = get_conn()
    try:
        _ensure_table(conn)
        conn.execute("DELETE FROM lainnya_category_info WHERE category=?", (category,))
        conn.commit()
    except Exception:
        pass
    conn.close()
    return default_info(category)
