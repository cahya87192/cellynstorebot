"""Logika murni teks pembungkus FAQ / Auto-CS / Saran (cogs/faq.py).

Knowledge base FAQ (pertanyaan & jawaban) sudah editable lewat utils.faq +
admin_faq.py. Modul ini menangani PROSA DI SEKITARNYA: judul/deskripsi/footer
embed FAQ, footer balasan Auto-CS, serta pesan-pesan perintah /saran — agar admin
bisa mengubahnya dari panel TANPA edit kode.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store}    -> nama toko (STORE_NAME)
  {question} -> pertanyaan yang cocok (judul balasan Auto-CS)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_FAQ_TITLE = "❓ FAQ — {store}"
DEFAULT_FAQ_TITLE_CONT = "❓ FAQ — {store} (lanjutan)"
DEFAULT_FAQ_DESC = (
    "Pertanyaan umum seputar {store}. Masih bingung? Tanya di channel "
    "bantuan atau kirim **/saran**."
)
DEFAULT_FAQ_FOOTER = "{store} • diperbarui otomatis"
DEFAULT_AUTOCS_TITLE = "💬 {question}"
DEFAULT_AUTOCS_FOOTER = "{store} • jawaban otomatis • ketik /saran bila perlu bantuan admin"
DEFAULT_SARAN_TITLE = "📨 Saran / Masukan Baru"
DEFAULT_SARAN_FOOTER = "{store}"
DEFAULT_SARAN_SUCCESS = "✅ Terima kasih! Saran/masukanmu sudah dikirim ke admin. 🙏"
DEFAULT_SARAN_NO_CHANNEL = "⚠️ Channel saran belum dikonfigurasi. Hubungi admin."
DEFAULT_SARAN_FAIL = "❌ Gagal mengirim. Coba lagi nanti."

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
FAQ_TEXT_SPECS = {
    "faq_title": {
        "label": "Embed FAQ — judul",
        "key": "faq_text_title",
        "default": DEFAULT_FAQ_TITLE,
        "placeholders": ("{store}",),
    },
    "faq_title_cont": {
        "label": "Embed FAQ — judul lanjutan (bila FAQ panjang)",
        "key": "faq_text_title_cont",
        "default": DEFAULT_FAQ_TITLE_CONT,
        "placeholders": ("{store}",),
    },
    "faq_desc": {
        "label": "Embed FAQ — deskripsi",
        "key": "faq_text_desc",
        "default": DEFAULT_FAQ_DESC,
        "placeholders": ("{store}",),
    },
    "faq_footer": {
        "label": "Embed FAQ — footer",
        "key": "faq_text_footer",
        "default": DEFAULT_FAQ_FOOTER,
        "placeholders": ("{store}",),
    },
    "autocs_title": {
        "label": "Auto-CS — judul balasan",
        "key": "faq_text_autocs_title",
        "default": DEFAULT_AUTOCS_TITLE,
        "placeholders": ("{question}",),
    },
    "autocs_footer": {
        "label": "Auto-CS — footer balasan",
        "key": "faq_text_autocs_footer",
        "default": DEFAULT_AUTOCS_FOOTER,
        "placeholders": ("{store}",),
    },
    "saran_title": {
        "label": "Saran — judul embed (ke admin)",
        "key": "faq_text_saran_title",
        "default": DEFAULT_SARAN_TITLE,
        "placeholders": (),
    },
    "saran_footer": {
        "label": "Saran — footer embed (ke admin)",
        "key": "faq_text_saran_footer",
        "default": DEFAULT_SARAN_FOOTER,
        "placeholders": ("{store}",),
    },
    "saran_success": {
        "label": "Saran — balasan sukses ke member",
        "key": "faq_text_saran_success",
        "default": DEFAULT_SARAN_SUCCESS,
        "placeholders": (),
    },
    "saran_no_channel": {
        "label": "Saran — channel belum dikonfigurasi",
        "key": "faq_text_saran_no_channel",
        "default": DEFAULT_SARAN_NO_CHANNEL,
        "placeholders": (),
    },
    "saran_fail": {
        "label": "Saran — gagal mengirim",
        "key": "faq_text_saran_fail",
        "default": DEFAULT_SARAN_FAIL,
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
    """Ambil teks untuk `kind` (FAQ_TEXT_SPECS) dari DB; fallback default."""
    spec = FAQ_TEXT_SPECS[kind]
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
    spec = FAQ_TEXT_SPECS[kind]
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
