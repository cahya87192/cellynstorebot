"""Logika murni teks katalog & auto-reply Layanan Lainnya (cogs/lainnya.py).

Cog `cogs/lainnya.py` membaca teks lewat render_text()/load_text() di sini
sehingga admin bisa mengubah pesan dari panel TANPA edit kode. Bila belum
dikustomisasi, dipakai teks default (sama persis dengan perilaku sebelumnya).

Hanya PROSA panel katalog & balasan auto-reply yang dibuat editable. Daftar grup,
daftar produk, deskripsi/S&K per kategori (punya tabel sendiri) tetap dikelola cog
dan disisipkan via placeholder.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store}    -> nama toko (STORE_NAME)
  {groups}   -> daftar grup layanan aktif (multi-baris) — katalog
  {category} -> nama kategori — judul auto-reply kategori

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_CATALOG_TITLE = "🛒 LAYANAN — {store}"
DEFAULT_CATALOG_DESC = (
    "Pilih **grup layanan** di bawah, lalu pilih kategori & produk.\n"
    "Atau klik **Custom Order** untuk pesanan khusus.\n\n"
    "**Grup tersedia:**\n{groups}\n\n"
    "💳 Pembayaran: QRIS • DANA • Bank Transfer"
)
DEFAULT_CATALOG_FOOTER = "{store}"
DEFAULT_AUTOREPLY_CAT_TITLE = "📦 {category} — {store}"
DEFAULT_AUTOREPLY_CAT_FOOTER = (
    "Ketik nama kategori/produk lain untuk info • atau buka tiket di katalog"
)
DEFAULT_AUTOREPLY_SEARCH_TITLE = "🔎 Hasil pencarian — {store}"
DEFAULT_AUTOREPLY_SEARCH_FOOTER = (
    "Ketik nama kategori spesifik untuk lihat deskripsi & S&K lengkap"
)

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
LAINNYA_SPECS = {
    "catalog_title": {
        "label": "Katalog Lainnya — judul",
        "key": "lainnya_text_catalog_title",
        "default": DEFAULT_CATALOG_TITLE,
        "placeholders": ("{store}",),
    },
    "catalog_desc": {
        "label": "Katalog Lainnya — deskripsi",
        "key": "lainnya_text_catalog_desc",
        "default": DEFAULT_CATALOG_DESC,
        "placeholders": ("{groups}",),
    },
    "catalog_footer": {
        "label": "Katalog Lainnya — footer",
        "key": "lainnya_text_catalog_footer",
        "default": DEFAULT_CATALOG_FOOTER,
        "placeholders": ("{store}",),
    },
    "autoreply_cat_title": {
        "label": "Auto-reply kategori — judul",
        "key": "lainnya_text_ar_cat_title",
        "default": DEFAULT_AUTOREPLY_CAT_TITLE,
        "placeholders": ("{category}", "{store}"),
    },
    "autoreply_cat_footer": {
        "label": "Auto-reply kategori — footer",
        "key": "lainnya_text_ar_cat_footer",
        "default": DEFAULT_AUTOREPLY_CAT_FOOTER,
        "placeholders": (),
    },
    "autoreply_search_title": {
        "label": "Auto-reply pencarian — judul",
        "key": "lainnya_text_ar_search_title",
        "default": DEFAULT_AUTOREPLY_SEARCH_TITLE,
        "placeholders": ("{store}",),
    },
    "autoreply_search_footer": {
        "label": "Auto-reply pencarian — footer",
        "key": "lainnya_text_ar_search_footer",
        "default": DEFAULT_AUTOREPLY_SEARCH_FOOTER,
        "placeholders": (),
    },
}


def render_template(text, **values):
    """Substitusi placeholder secara aman (str.replace, bukan str.format)."""
    out = text if text is not None else ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def load_text(kind):
    """Ambil teks untuk `kind` (LAINNYA_SPECS) dari DB; fallback default."""
    spec = LAINNYA_SPECS[kind]
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
    spec = LAINNYA_SPECS[kind]
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
