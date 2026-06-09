"""Logika murni teks katalog & tiket ML/Topup Diamond (cogs/ml.py).

Cog `cogs/ml.py` membaca teks lewat render_text()/load_text() di sini sehingga
admin bisa mengubah pesan dari panel TANPA edit kode. Bila belum dikustomisasi,
dipakai teks default (sama persis dengan perilaku sebelumnya).

Hanya PROSA yang dibuat editable: judul/deskripsi/footer panel katalog, pesan
selesai, dan judul pembatalan. Daftar game disisipkan otomatis via placeholder.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store} -> nama toko (STORE_NAME)
  {games} -> daftar game aktif (multi-baris)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_CATALOG_TITLE = "TOPUP DIAMOND GAME"
DEFAULT_CATALOG_DESC = (
    "Sekarang tersedia di **{store}**\n"
    "Topup diamond dengan harga terjangkau, proses cepat, amanah dan transparan!\n\n"
    "**Game tersedia:**\n{games}\n\n"
    "Pilih game di dropdown di bawah untuk melihat produk dan melakukan pemesanan.\n\n"
    "Metode Pembayaran: **QRIS**"
)
DEFAULT_CATALOG_FOOTER = "{store}"
DEFAULT_DONE_SUCCESS = "Topup berhasil diproses. Terima kasih telah berbelanja di {store}!"
DEFAULT_CANCEL_TITLE = "❌ Topup Dibatalkan"

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
ML_SPECS = {
    "catalog_title": {
        "label": "Katalog ML — judul",
        "key": "ml_text_catalog_title",
        "default": DEFAULT_CATALOG_TITLE,
        "placeholders": (),
    },
    "catalog_desc": {
        "label": "Katalog ML — deskripsi",
        "key": "ml_text_catalog_desc",
        "default": DEFAULT_CATALOG_DESC,
        "placeholders": ("{store}", "{games}"),
    },
    "catalog_footer": {
        "label": "Katalog ML — footer",
        "key": "ml_text_catalog_footer",
        "default": DEFAULT_CATALOG_FOOTER,
        "placeholders": ("{store}",),
    },
    "done_success": {
        "label": "Konfirmasi selesai (!mlselesai)",
        "key": "ml_text_done_success",
        "default": DEFAULT_DONE_SUCCESS,
        "placeholders": ("{store}",),
    },
    "cancel_title": {
        "label": "Judul pembatalan (!mlbatal)",
        "key": "ml_text_cancel_title",
        "default": DEFAULT_CANCEL_TITLE,
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
    """Ambil teks untuk `kind` (ML_SPECS) dari DB; fallback default."""
    spec = ML_SPECS[kind]
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
    spec = ML_SPECS[kind]
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
