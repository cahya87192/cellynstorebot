"""Logika murni teks katalog Robux Store (cogs/robux.py).

Cog `cogs/robux.py` membaca teks lewat render_text()/load_text() di sini sehingga
admin bisa mengubah pesan dari panel TANPA edit kode. Bila belum dikustomisasi,
dipakai teks default (sama persis dengan perilaku sebelumnya).

Hanya PROSA panel katalog ROBUX STORE yang dibuat editable. Rate, stok, daftar
kategori, dan tombol tetap dikelola cog dan disisipkan via placeholder.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {emoji}      -> emoji Robux (ROBUX_EMOJI_SAFE) — judul
  {store}      -> nama toko (STORE_NAME)
  {rate}       -> rate Robux terformat (mis. "Rp 100/Robux" / "Belum diset")
  {categories} -> daftar kategori aktif (multi-baris)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_CATALOG_TITLE = "{emoji} ROBUX STORE — {store}"
DEFAULT_CATALOG_DESC = (
    "Harga dihitung otomatis berdasarkan rate Robux terkini.\n"
    "Rate: **{rate}**\n\n"
    "**Kategori tersedia:**\n{categories}\n\n"
    "Klik tombol kategori di bawah untuk lihat item & order."
)
DEFAULT_CATALOG_FOOTER = "{store} • Harga dapat berubah sewaktu-waktu"

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
ROBUX_SPECS = {
    "catalog_title": {
        "label": "Katalog Robux — judul",
        "key": "robux_text_catalog_title",
        "default": DEFAULT_CATALOG_TITLE,
        "placeholders": ("{emoji}", "{store}"),
    },
    "catalog_desc": {
        "label": "Katalog Robux — deskripsi",
        "key": "robux_text_catalog_desc",
        "default": DEFAULT_CATALOG_DESC,
        "placeholders": ("{rate}", "{categories}"),
    },
    "catalog_footer": {
        "label": "Katalog Robux — footer",
        "key": "robux_text_catalog_footer",
        "default": DEFAULT_CATALOG_FOOTER,
        "placeholders": ("{store}",),
    },
}


def render_template(text, **values):
    """Substitusi placeholder secara aman (str.replace, bukan str.format)."""
    out = text if text is not None else ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def load_text(kind):
    """Ambil teks untuk `kind` (ROBUX_SPECS) dari DB; fallback default."""
    spec = ROBUX_SPECS[kind]
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
    spec = ROBUX_SPECS[kind]
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
