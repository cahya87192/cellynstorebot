"""Logika murni teks antrian yang dilihat customer (cogs/queue.py).

Cog `cogs/queue.py` membaca teks lewat render_text()/load_text() di sini sehingga
admin bisa mengubah pesan dari panel TANPA edit kode. Bila belum dikustomisasi,
dipakai teks default (sama persis dengan perilaku sebelumnya).

Yang bisa diedit hanya teks yang DILIHAT MEMBER (papan publik & kartu posisi),
bukan papan admin internal.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {admin}    -> mention admin yang memproses tiket (kartu "sedang diproses")
  {position} -> nomor posisi antrean member (kartu menunggu)
  {ahead}    -> jumlah tiket di depan member (kartu menunggu)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_PUBLIC_INFO = (
    "Papan ini menampilkan antrean tiket secara **real-time** agar kamu tahu "
    "posisi & estimasi giliranmu. Admin memproses tiket **berurutan dari yang "
    "paling lama menunggu** (pesanan Top Spender diprioritaskan). Mohon "
    "ditunggu dengan sabar ya — setiap tiket pasti dilayani."
)
DEFAULT_PUBLIC_EMPTY = (
    "Tidak ada antrean saat ini. Toko siap melayani — silakan buka tiket! 🎉"
)
DEFAULT_CARD_HANDLING = "🟢 Sedang diproses oleh {admin}. Mohon tunggu sebentar ya"
DEFAULT_CARD_FIRST = (
    "🟡 **Posisi Antrean: 1** — kamu berada di antrean terdepan. "
    "Admin akan segera memproses pesananmu"
)
DEFAULT_CARD_WAITING = (
    "🔄 **Posisi Antrean: {position}** "
    "({ahead} tiket di depanmu). Mohon ditunggu ya!"
)

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
QUEUE_SPECS = {
    "public_info": {
        "label": "Papan publik — keterangan 'Tentang Papan Ini'",
        "key": "queue_text_public_info",
        "default": DEFAULT_PUBLIC_INFO,
        "placeholders": (),
    },
    "public_empty": {
        "label": "Papan publik — saat tidak ada antrean",
        "key": "queue_text_public_empty",
        "default": DEFAULT_PUBLIC_EMPTY,
        "placeholders": (),
    },
    "card_handling": {
        "label": "Kartu tiket — sedang diproses",
        "key": "queue_text_card_handling",
        "default": DEFAULT_CARD_HANDLING,
        "placeholders": ("{admin}",),
    },
    "card_first": {
        "label": "Kartu tiket — posisi terdepan (antrean #1)",
        "key": "queue_text_card_first",
        "default": DEFAULT_CARD_FIRST,
        "placeholders": (),
    },
    "card_waiting": {
        "label": "Kartu tiket — menunggu (posisi 2+)",
        "key": "queue_text_card_waiting",
        "default": DEFAULT_CARD_WAITING,
        "placeholders": ("{position}", "{ahead}"),
    },
}


def render_template(text, **values):
    """Substitusi placeholder secara aman (str.replace, bukan str.format)."""
    out = text if text is not None else ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def load_text(kind):
    """Ambil teks untuk `kind` (QUEUE_SPECS) dari DB; fallback default."""
    spec = QUEUE_SPECS[kind]
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
    spec = QUEUE_SPECS[kind]
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
