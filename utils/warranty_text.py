"""Logika murni teks sistem klaim garansi (cogs/warranty.py).

Cog `cogs/warranty.py` membaca teks lewat render_text()/load_text() di sini
sehingga admin bisa mengubah pesan dari panel TANPA edit kode. Bila belum
dikustomisasi, dipakai teks default (sama persis dengan perilaku sebelumnya).

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store} -> nama toko (STORE_NAME dari config)

Modul ini self-contained (tidak berbagi state dengan editor lain) dan hanya
menyentuh SQLite (bot_state) -> gampang diuji, tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_PANEL_TITLE = "Klaim Garansi"
DEFAULT_PANEL_DESC = (
    "Punya kendala dengan pesananmu di {store}?\n"
    "Klik tombol di bawah untuk membuka tiket klaim garansi.\n\n"
    "**Syarat garansi:** kamu sudah memberi **rating** untuk transaksi "
    "tersebut (dalam batas 24 jam setelah transaksi).\n"
    "Tanpa rating, garansi tidak berlaku."
)
DEFAULT_REJECT_UNRATED = (
    "Maaf, kamu belum memenuhi syarat garansi.\n"
    "Garansi hanya berlaku untuk transaksi yang **sudah kamu beri rating** "
    "dalam batas **24 jam** setelah transaksi. 🙏"
)
DEFAULT_REJECT_EXPIRED = (
    "Maaf, masa garansi transaksimu sudah **habis**. 🙏\n"
    "Tiket klaim hanya bisa dibuka selama garansi masih berlaku."
)
DEFAULT_TICKET_DESC = (
    "Garansi terverifikasi (kamu sudah memberi rating). ✅\n"
    "Jelaskan kendala pesananmu di bawah ini. Admin akan segera membantu."
)

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
WARRANTY_SPECS = {
    "panel_title": {
        "label": "Judul panel garansi",
        "key": "warranty_panel_title",
        "default": DEFAULT_PANEL_TITLE,
        "placeholders": (),
    },
    "panel_desc": {
        "label": "Deskripsi panel garansi",
        "key": "warranty_panel_desc",
        "default": DEFAULT_PANEL_DESC,
        "placeholders": ("{store}",),
    },
    "reject_unrated": {
        "label": "Tolak klaim — belum memberi rating",
        "key": "warranty_reject_unrated",
        "default": DEFAULT_REJECT_UNRATED,
        "placeholders": (),
    },
    "reject_expired": {
        "label": "Tolak klaim — masa garansi habis",
        "key": "warranty_reject_expired",
        "default": DEFAULT_REJECT_EXPIRED,
        "placeholders": (),
    },
    "ticket_desc": {
        "label": "Deskripsi embed tiket klaim",
        "key": "warranty_ticket_desc",
        "default": DEFAULT_TICKET_DESC,
        "placeholders": (),
    },
}


def render_template(text, **values):
    """Substitusi placeholder secara aman (str.replace, bukan str.format).

    Kurung kurawal lain di teks tidak memicu error. None -> string kosong. Hanya
    placeholder yang diberikan yang diganti; sisanya dibiarkan apa adanya.
    """
    out = text if text is not None else ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def load_text(kind):
    """Ambil teks untuk `kind` (WARRANTY_SPECS) dari DB; fallback default.

    Nilai kosong / whitespace dianggap belum diisi -> pakai default.
    """
    spec = WARRANTY_SPECS[kind]
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
    """Simpan teks untuk `kind`.

    None -> tidak diubah. String kosong/whitespace -> reset ke default (dihapus).
    """
    spec = WARRANTY_SPECS[kind]
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
