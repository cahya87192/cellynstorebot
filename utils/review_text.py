"""Logika murni teks sistem rating & ulasan (cogs/reviews.py).

Cog `cogs/reviews.py` membaca teks lewat render_text()/load_text() di sini
sehingga admin bisa mengubah pesan dari panel TANPA edit kode. Bila belum
dikustomisasi, dipakai teks default (sama persis dengan perilaku sebelumnya).

Yang dibuat editable hanya PROSA (judul, deskripsi, footer, ucapan terima kasih).
Struktur embed (field Item/Nominal/Layanan, tombol bintang, timestamp deadline)
tetap dikelola cog dan tidak diubah.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store}  -> nama toko (STORE_NAME)
  {hours}  -> batas waktu rating dalam jam (rv.RATING_DEADLINE_HOURS)
  {rating} -> angka rating yang diberi member (1-5)
  {stars}  -> bintang rating (mis. ⭐⭐⭐⭐⭐)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_PROMPT_TITLE = "⭐ Beri Rating Transaksimu"
DEFAULT_PROMPT_DESC = (
    "Terima kasih sudah berbelanja di **{store}**!\n\n"
    "Beri rating untuk transaksi ini dengan menekan tombol bintang di bawah.\n\n"
    "⚠️ **PENTING: Rating = Garansi.**\n"
    "Kamu wajib memberi rating dalam **{hours} jam**. "
    "**Tanpa rating sebelum batas waktu, transaksimu TIDAK mendapat garansi.** "
    "Mohon beri rating sesegera mungkin ya! 💛"
)
DEFAULT_EXPIRED_TITLE = "⌛ Waktu Rating Habis — Garansi Hangus"
DEFAULT_EXPIRED_DESC = (
    "Batas waktu **{hours} jam** untuk memberi rating sudah lewat, "
    "sehingga transaksi ini **tidak mendapat garansi**.\n\n"
    "Lain kali jangan lupa beri rating segera setelah transaksi ya, agar garansimu aktif. 🙏"
)
DEFAULT_PUBLISHED_TITLE = "⟡ ULASAN PELANGGAN"
DEFAULT_REMINDER_TITLE = "⏰ Jangan Lupa Beri Rating!"
DEFAULT_REMINDER_DESC = (
    "Transaksimu di **{store}** belum kamu beri rating.\n"
    "**Rating = Garansi.** Beri rating sekarang agar garansimu aktif "
    "sebelum batas waktu habis. 💛"
)
DEFAULT_FOOTER_WARNING = "{store} • Tanpa rating = tanpa garansi"
DEFAULT_THANKYOU_5STAR = (
    "🎉✨ WAH, RATING SEMPURNA {stars}! ✨🎉\n"
    "Makasih banyak udah kasih **5/5** — kamu the best! 💛\n"
    "Garansi transaksimu **aktif**, dan ditunggu next order-nya di {store}! 🛍️"
)
DEFAULT_THANKYOU_NORMAL = (
    "Makasih banyak! Rating **{rating}/5** {stars} kamu sudah tercatat "
    "dan jadi garansi transaksimu. 💛"
)

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
REVIEW_SPECS = {
    "prompt_title": {
        "label": "Prompt rating — judul",
        "key": "review_prompt_title",
        "default": DEFAULT_PROMPT_TITLE,
        "placeholders": (),
    },
    "prompt_desc": {
        "label": "Prompt rating — deskripsi (timestamp deadline ditambah otomatis)",
        "key": "review_prompt_desc",
        "default": DEFAULT_PROMPT_DESC,
        "placeholders": ("{store}", "{hours}"),
    },
    "expired_title": {
        "label": "Rating kedaluwarsa — judul",
        "key": "review_expired_title",
        "default": DEFAULT_EXPIRED_TITLE,
        "placeholders": (),
    },
    "expired_desc": {
        "label": "Rating kedaluwarsa — deskripsi",
        "key": "review_expired_desc",
        "default": DEFAULT_EXPIRED_DESC,
        "placeholders": ("{store}", "{hours}"),
    },
    "published_title": {
        "label": "Ulasan dipublikasikan — judul",
        "key": "review_published_title",
        "default": DEFAULT_PUBLISHED_TITLE,
        "placeholders": (),
    },
    "reminder_title": {
        "label": "Pengingat rating — judul",
        "key": "review_reminder_title",
        "default": DEFAULT_REMINDER_TITLE,
        "placeholders": (),
    },
    "reminder_desc": {
        "label": "Pengingat rating — deskripsi (sisa waktu ditambah otomatis)",
        "key": "review_reminder_desc",
        "default": DEFAULT_REMINDER_DESC,
        "placeholders": ("{store}",),
    },
    "footer_warning": {
        "label": "Footer peringatan garansi (prompt, kedaluwarsa, pengingat)",
        "key": "review_footer_warning",
        "default": DEFAULT_FOOTER_WARNING,
        "placeholders": ("{store}",),
    },
    "thankyou_5star": {
        "label": "Ucapan terima kasih — rating 5/5",
        "key": "review_thankyou_5star",
        "default": DEFAULT_THANKYOU_5STAR,
        "placeholders": ("{store}", "{stars}"),
    },
    "thankyou_normal": {
        "label": "Ucapan terima kasih — rating 1-4",
        "key": "review_thankyou_normal",
        "default": DEFAULT_THANKYOU_NORMAL,
        "placeholders": ("{rating}", "{stars}"),
    },
}


def render_template(text, **values):
    """Substitusi placeholder secara aman (str.replace, bukan str.format)."""
    out = text if text is not None else ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def load_text(kind):
    """Ambil teks untuk `kind` (REVIEW_SPECS) dari DB; fallback default."""
    spec = REVIEW_SPECS[kind]
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
    spec = REVIEW_SPECS[kind]
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
