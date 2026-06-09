"""Logika murni teks katalog & tiket Vilog (cogs/vilog.py).

Cog `cogs/vilog.py` (Topup Robux via Login) membaca teks lewat render_text()/
load_text() di sini sehingga admin bisa mengubah pesan dari panel TANPA edit kode.
Bila belum dikustomisasi, dipakai teks default (sama persis dengan perilaku
sebelumnya).

Hanya PROSA yang dibuat editable: judul/deskripsi/catatan/footer panel katalog,
pesan selesai, dan judul pembatalan. Tabel harga, stok, dan field dinamis tetap
dikelola cog.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store} -> nama toko (STORE_NAME)
  {step}  -> kelipatan robux (STEP_ROBUX)
  {max}   -> maksimal robux per order (MAX_ROBUX)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_CATALOG_TITLE = "TOPUP ROBUX VIA LOGIN (VILOG) — {store}"
DEFAULT_CATALOG_DESC = (
    "Topup Robux via login akun Roblox.\n"
    "Order tersedia dalam kelipatan **{step} Robux**"
)
DEFAULT_CATALOG_NOTE = (
    "- Premium hanya bisa 1x per bulan\n"
    "- Proses 15–30 menit (maks. 3 jam tergantung antrian)\n"
    "- Wajib menyertakan kode backup terbaru (min. 3)\n"
    "- Pastikan email & password benar agar proses lancar\n"
    "- Akun roblox wajib memiliki email aktif"
)
DEFAULT_CATALOG_FOOTER = "{store} • Support kelipatan {step} (max {max})"
DEFAULT_DONE_SUCCESS = "Topup Vilog selesai diproses. Terima kasih telah berbelanja di {store}!"
DEFAULT_CANCEL_TITLE = "❌ Tiket Vilog Dibatalkan"

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
VILOG_SPECS = {
    "catalog_title": {
        "label": "Katalog Vilog — judul",
        "key": "vilog_text_catalog_title",
        "default": DEFAULT_CATALOG_TITLE,
        "placeholders": ("{store}",),
    },
    "catalog_desc": {
        "label": "Katalog Vilog — deskripsi",
        "key": "vilog_text_catalog_desc",
        "default": DEFAULT_CATALOG_DESC,
        "placeholders": ("{step}",),
    },
    "catalog_note": {
        "label": "Katalog Vilog — catatan",
        "key": "vilog_text_catalog_note",
        "default": DEFAULT_CATALOG_NOTE,
        "placeholders": (),
    },
    "catalog_footer": {
        "label": "Katalog Vilog — footer",
        "key": "vilog_text_catalog_footer",
        "default": DEFAULT_CATALOG_FOOTER,
        "placeholders": ("{store}", "{step}", "{max}"),
    },
    "done_success": {
        "label": "Konfirmasi selesai (!vilogdone)",
        "key": "vilog_text_done_success",
        "default": DEFAULT_DONE_SUCCESS,
        "placeholders": ("{store}",),
    },
    "cancel_title": {
        "label": "Judul pembatalan (!vilogbatal)",
        "key": "vilog_text_cancel_title",
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
    """Ambil teks untuk `kind` (VILOG_SPECS) dari DB; fallback default."""
    spec = VILOG_SPECS[kind]
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
    spec = VILOG_SPECS[kind]
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
