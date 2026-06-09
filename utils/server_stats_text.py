"""Logika murni format nama channel statistik member (cogs/server_stats.py).

Cog `cogs/server_stats.py` mengganti nama voice channel jadi jumlah member aktif.
Modul ini membuat format nama tersebut editable dari panel admin TANPA edit kode.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {count} -> jumlah member (non-bot)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_MEMBERS_FORMAT = "🌐 Members: {count}"

SERVER_STATS_SPECS = {
    "members_format": {
        "label": "Format nama channel statistik member",
        "key": "server_stats_members_format",
        "default": DEFAULT_MEMBERS_FORMAT,
        "placeholders": ("{count}",),
    },
}


def render_template(text, **values):
    """Substitusi placeholder secara aman (str.replace, bukan str.format)."""
    out = text if text is not None else ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def load_text(kind):
    """Ambil teks untuk `kind` (SERVER_STATS_SPECS) dari DB; fallback default."""
    spec = SERVER_STATS_SPECS[kind]
    from utils.db import get_conn
    value = None
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM bot_state WHERE key=?", (spec["key"],)
        ).fetchone()
        value = row["value"] if row else None
    except Exception:
        pass
    conn.close()
    if not (value and value.strip()):
        value = spec["default"]
    return value


def save_text(kind, text=None):
    """Simpan teks untuk `kind`. None -> tak diubah; kosong -> reset default."""
    spec = SERVER_STATS_SPECS[kind]
    if text is None:
        return
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    if text.strip() == "":
        c.execute("DELETE FROM bot_state WHERE key=?", (spec["key"],))
    else:
        c.execute(
            "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
            (spec["key"], text),
        )
    conn.commit()
    conn.close()


def render_text(kind, **values):
    """Teks `kind` dengan placeholder tersubstitusi."""
    return render_template(load_text(kind), **values)


def members_name(count):
    """Nama channel statistik untuk `count` member."""
    return render_text("members_format", count=count)
