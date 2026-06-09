"""Logika murni teks pesan tiket order (cogs/orders.py).

Cog `cogs/orders.py` (perintah !done / !cancel untuk tiket order layanan
"lainnya") membaca teks lewat render_text()/load_text() di sini sehingga admin
bisa mengubah pesan dari panel TANPA edit kode. Bila belum dikustomisasi, dipakai
teks default (sama persis dengan perilaku sebelumnya).

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store} -> nama toko (STORE_NAME dari config)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_SUCCESS = "Pesanan berhasil diproses. Terima kasih telah berbelanja di {store}!"
DEFAULT_CANCEL_TITLE = "❌ Pesanan Dibatalkan"
DEFAULT_CANCEL_REASON = "Tidak ada alasan diberikan."

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
ORDER_SPECS = {
    "success": {
        "label": "Pesan selesai (!done)",
        "key": "order_success_text",
        "default": DEFAULT_SUCCESS,
        "placeholders": ("{store}",),
    },
    "cancel_title": {
        "label": "Judul pembatalan (!cancel)",
        "key": "order_cancel_title",
        "default": DEFAULT_CANCEL_TITLE,
        "placeholders": (),
    },
    "cancel_reason_default": {
        "label": "Alasan default bila admin tidak mengisi alasan",
        "key": "order_cancel_reason_default",
        "default": DEFAULT_CANCEL_REASON,
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
    """Ambil teks untuk `kind` (ORDER_SPECS) dari DB; fallback default."""
    spec = ORDER_SPECS[kind]
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
    spec = ORDER_SPECS[kind]
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
