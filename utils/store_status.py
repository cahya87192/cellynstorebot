"""Logika murni label status toko (cogs/store_status.py).

Cog `cogs/store_status.py` mengubah nama voice channel sesuai jam buka/tutup.
Modul ini membuat label tersebut bisa diatur dari panel admin TANPA edit kode.
Bila belum dikustomisasi, dipakai label default (sama persis dengan perilaku
sebelumnya).

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default label (sama persis dgn versi hardcoded sebelumnya) ───────────────────
DEFAULT_OPEN_LABEL = "🟢 STATUS : OPEN"
DEFAULT_CLOSE_LABEL = "🔴 STATUS : CLOSE"

OPEN_LABEL_KEY = "store_status_open_label"
CLOSE_LABEL_KEY = "store_status_close_label"


def _load(key, default):
    """Ambil satu label dari bot_state; fallback default bila kosong/whitespace."""
    from utils.db import get_conn
    value = None
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM bot_state WHERE key=?", (key,)
        ).fetchone()
        value = row["value"] if row else None
    except Exception:
        pass
    conn.close()
    if not (value and value.strip()):
        value = default
    return value


def _save(key, value=None):
    """Simpan satu label. None -> tidak diubah. Kosong/whitespace -> reset (hapus)."""
    if value is None:
        return
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    if value.strip() == "":
        c.execute("DELETE FROM bot_state WHERE key=?", (key,))
    else:
        c.execute(
            "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
            (key, value),
        )
    conn.commit()
    conn.close()


def get_open_label():
    """Label nama channel saat toko buka."""
    return _load(OPEN_LABEL_KEY, DEFAULT_OPEN_LABEL)


def get_close_label():
    """Label nama channel saat toko tutup."""
    return _load(CLOSE_LABEL_KEY, DEFAULT_CLOSE_LABEL)


def set_open_label(value=None):
    """Simpan label buka. Kosong -> reset ke default."""
    _save(OPEN_LABEL_KEY, value)


def set_close_label(value=None):
    """Simpan label tutup. Kosong -> reset ke default."""
    _save(CLOSE_LABEL_KEY, value)


def get_label(store_open):
    """Kembalikan label sesuai status toko (True = buka)."""
    return get_open_label() if store_open else get_close_label()
