"""Logika murni teks pembungkus embed /help (cogs/help_slash.py).

Daftar slash command di /help dibangun otomatis dari kode (MEMBER_COMMANDS /
ADMIN_COMMANDS). Modul ini hanya membuat PROSA pembungkusnya (judul, deskripsi,
footer) editable dari panel admin TANPA edit kode.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store}   -> nama toko (STORE_NAME)
  {seconds} -> detik sebelum pesan /help auto-hilang (AUTO_DELETE_SECONDS)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_TITLE = "📖 Panduan Slash Command"
DEFAULT_DESC = "Untuk command prefix (`!...`), admin bisa pakai `!cmd`."
DEFAULT_FOOTER = "{store} • pesan ini hilang dalam {seconds} detik"

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
HELP_SPECS = {
    "title": {
        "label": "Embed /help — judul",
        "key": "help_text_title",
        "default": DEFAULT_TITLE,
        "placeholders": (),
    },
    "description": {
        "label": "Embed /help — deskripsi",
        "key": "help_text_desc",
        "default": DEFAULT_DESC,
        "placeholders": (),
    },
    "footer": {
        "label": "Embed /help — footer",
        "key": "help_text_footer",
        "default": DEFAULT_FOOTER,
        "placeholders": ("{store}", "{seconds}"),
    },
}


def render_template(text, **values):
    """Substitusi placeholder secara aman (str.replace, bukan str.format)."""
    out = text if text is not None else ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def load_text(kind):
    """Ambil teks untuk `kind` (HELP_SPECS) dari DB; fallback default."""
    spec = HELP_SPECS[kind]
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
    spec = HELP_SPECS[kind]
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
