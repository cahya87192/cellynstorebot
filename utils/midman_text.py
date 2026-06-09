"""Logika murni teks panel & konfirmasi Midman Trade (cogs/midman.py).

Cog `cogs/midman.py` membaca teks lewat render_text()/load_text() di sini
sehingga admin bisa mengubah pesan dari panel TANPA edit kode. Bila belum
dikustomisasi, dipakai teks default (sama persis dengan perilaku sebelumnya).

Hanya PROSA yang dibuat editable: judul & deskripsi panel katalog Midman (perintah
!open) serta pesan konfirmasi trade selesai (!acc). Tabel fee, tombol, dan field
dinamis tetap dikelola cog.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store} -> nama toko (STORE_NAME dari config)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_CATALOG_TITLE = "MIDMAN TRADE — {store}"
DEFAULT_CATALOG_DESC = (
    "Jasa perantara transaksi item game dengan aman bersama {store}.\n\n"
    "⚔️ **Midman Trade** — Tukar item/akun antar dua pihak\n"
    "Cara pakai: Klik tombol **Midman Trade** → isi form → tunggu admin bergabung\n\n"
    "🛒 **Midman Jual Beli** — Jual/beli item dengan admin sebagai perantara dana\n"
    "Cara pakai: Klik tombol **Midman Jual Beli** → isi form → tunggu admin setup"
)
DEFAULT_ACC_SUCCESS = (
    "Admin telah mengkonfirmasi trade selesai & kedua pihak menerima item masing-masing."
)

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
MIDMAN_SPECS = {
    "catalog_title": {
        "label": "Panel Midman — judul",
        "key": "midman_text_catalog_title",
        "default": DEFAULT_CATALOG_TITLE,
        "placeholders": ("{store}",),
    },
    "catalog_desc": {
        "label": "Panel Midman — deskripsi",
        "key": "midman_text_catalog_desc",
        "default": DEFAULT_CATALOG_DESC,
        "placeholders": ("{store}",),
    },
    "acc_success": {
        "label": "Konfirmasi trade selesai (!acc)",
        "key": "midman_text_acc_success",
        "default": DEFAULT_ACC_SUCCESS,
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
    """Ambil teks untuk `kind` (MIDMAN_SPECS) dari DB; fallback default."""
    spec = MIDMAN_SPECS[kind]
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
    spec = MIDMAN_SPECS[kind]
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
