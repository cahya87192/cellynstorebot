"""Logika murni teks katalog & tiket GP (cogs/gp.py).

Cog `cogs/gp.py` (Topup Robux via Gamepass) membaca teks lewat render_text()/
load_text() di sini sehingga admin bisa mengubah pesan dari panel TANPA edit kode.
Bila belum dikustomisasi, dipakai teks default (sama persis dengan perilaku
sebelumnya).

Hanya PROSA yang dibuat editable: judul/deskripsi/cara order/catatan/footer panel
katalog dan pesan selesai. Rate, stok, dan field dinamis tetap dikelola cog.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store} -> nama toko (STORE_NAME)
  {min}   -> minimal order robux (MIN_ROBUX)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_CATALOG_TITLE = "TOPUP ROBUX VIA GAMEPASS — {store}"
DEFAULT_CATALOG_DESC = (
    "Topup Robux aman tanpa perlu kasih password akun!\n"
    "Robux masuk dalam **3-7 hari kerja** setelah admin beli gamepass kamu.\n\n"
    "Minimal order: **{min} Robux**\n\n"
    "Klik tombol di bawah untuk mulai order."
)
DEFAULT_CATALOG_HOWTO = (
    "1. Klik **Order Sekarang**\n"
    "2. Input jumlah Robux yang diinginkan\n"
    "3. Bot hitung harga gamepass + total bayar\n"
    "4. Konfirmasi → tiket terbuka\n"
    "5. Bayar tagihan ke admin\n"
    "6. Buat gamepass sesuai harga yang ditentukan, kirim link ke tiket\n"
    "7. Admin beli gamepass kamu\n"
    "8. Tunggu Robux masuk 3-7 hari 🎉"
)
DEFAULT_CATALOG_NOTE = (
    "• Robux yang kamu terima adalah **after tax** (sudah dipotong 30% Roblox)\n"
    "• Jangan hapus gamepass sebelum Robux masuk\n"
    "• Harga gamepass dihitung otomatis oleh bot"
)
DEFAULT_CATALOG_FOOTER = "{store} • Rate dapat berubah sewaktu-waktu"
DEFAULT_DONE_SUCCESS = (
    "Gamepass sudah dibeli! Robux kamu akan masuk dalam 3-7 hari kerja.\n"
    "Terima kasih telah berbelanja di {store}!"
)

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
GP_SPECS = {
    "catalog_title": {
        "label": "Katalog GP — judul",
        "key": "gp_text_catalog_title",
        "default": DEFAULT_CATALOG_TITLE,
        "placeholders": ("{store}",),
    },
    "catalog_desc": {
        "label": "Katalog GP — deskripsi",
        "key": "gp_text_catalog_desc",
        "default": DEFAULT_CATALOG_DESC,
        "placeholders": ("{min}",),
    },
    "catalog_howto": {
        "label": "Katalog GP — cara order",
        "key": "gp_text_catalog_howto",
        "default": DEFAULT_CATALOG_HOWTO,
        "placeholders": (),
    },
    "catalog_note": {
        "label": "Katalog GP — catatan",
        "key": "gp_text_catalog_note",
        "default": DEFAULT_CATALOG_NOTE,
        "placeholders": (),
    },
    "catalog_footer": {
        "label": "Katalog GP — footer",
        "key": "gp_text_catalog_footer",
        "default": DEFAULT_CATALOG_FOOTER,
        "placeholders": ("{store}",),
    },
    "done_success": {
        "label": "Konfirmasi selesai (!gpdone)",
        "key": "gp_text_done_success",
        "default": DEFAULT_DONE_SUCCESS,
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
    """Ambil teks untuk `kind` (GP_SPECS) dari DB; fallback default."""
    spec = GP_SPECS[kind]
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
    spec = GP_SPECS[kind]
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
