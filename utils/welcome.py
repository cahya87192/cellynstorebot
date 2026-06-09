"""Logika murni teks pesan event member (welcome / boost / leave).

Cog `cogs/welcome.py` membaca teks lewat fungsi render_* di sini sehingga admin
bisa mengubah judul & isi dari panel TANPA edit kode. Bila belum dikustomisasi,
dipakai teks default (sama persis dengan perilaku sebelumnya).

Placeholder yang didukung (diganti otomatis saat dikirim):
  {member} -> nama / mention member
  {store}  -> nama toko
  {count}  -> nomor urut member (khusus welcome)
  {durasi} -> lama keanggotaan (khusus leave)

Semua fungsi murni / hanya menyentuh SQLite (bot_state) -> gampang diuji, tanpa
butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_WELCOME_TITLE = "Halo {member}, selamat datang di {store}! "
DEFAULT_WELCOME_DESC = (
    "Makasih ya udah mampir dan gabung bareng kami\n"
    "Sekarang kamu jadi bagian ke-**{count}** dari keluarga kecil ini.\n\n"
    "Santai aja, anggap rumah sendiri. Kalau mau tanya-tanya produk atau "
    "butuh bantuan, jangan sungkan — kami siap bantu kapan pun. 🤝"
)

DEFAULT_BOOST_TITLE = "Ada yang baik hati nih!"
DEFAULT_BOOST_DESC = (
    "{member} baru aja boost server 🚀 Makasih banyak ya, kamu keren! 🙏\n"
    "Dukungan kecilmu bikin {store} makin hidup. Sehat & sukses selalu! 🤍"
)

DEFAULT_LEAVE_TITLE = "{member} pamit dulu 🥺"
DEFAULT_LEAVE_DESC = (
    "Terima kasih atas kebersamaannya selama **{durasi}**. "
    "Semoga kita ketemu lagi ya — take care! "
)

# Registry tiap jenis pesan: kunci DB + default + placeholder yang relevan.
MSG_SPECS = {
    "welcome": {
        "label": "Welcome (sambutan join)",
        "title_key": "welcome_title",
        "desc_key": "welcome_desc",
        "default_title": DEFAULT_WELCOME_TITLE,
        "default_desc": DEFAULT_WELCOME_DESC,
        "placeholders": ("{member}", "{store}", "{count}"),
    },
    "boost": {
        "label": "Boost (member nge-boost server)",
        "title_key": "boost_title",
        "desc_key": "boost_desc",
        "default_title": DEFAULT_BOOST_TITLE,
        "default_desc": DEFAULT_BOOST_DESC,
        "placeholders": ("{member}", "{store}"),
    },
    "leave": {
        "label": "Leave (member keluar server)",
        "title_key": "leave_title",
        "desc_key": "leave_desc",
        "default_title": DEFAULT_LEAVE_TITLE,
        "default_desc": DEFAULT_LEAVE_DESC,
        "placeholders": ("{member}", "{store}", "{durasi}"),
    },
}

# Placeholder welcome dipertahankan utk kompatibilitas import lama.
PLACEHOLDERS = MSG_SPECS["welcome"]["placeholders"]


def render_template(text, **values):
    """Substitusi placeholder secara aman.

    Memakai str.replace (bukan str.format) supaya kurung kurawal lain di teks
    tidak memicu error. None -> string kosong. Hanya placeholder yang diberikan
    yang diganti; sisanya dibiarkan apa adanya.
    """
    out = text if text is not None else ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def load_texts(kind):
    """Ambil (title_template, desc_template) untuk `kind` dari DB; fallback default.

    Nilai kosong / whitespace dianggap belum diisi -> pakai default.
    """
    spec = MSG_SPECS[kind]
    from utils.db import get_conn
    title = desc = None
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT key, value FROM bot_state WHERE key IN (?,?)",
            (spec["title_key"], spec["desc_key"]),
        ).fetchall()
        data = {r["key"]: r["value"] for r in rows}
        title = data.get(spec["title_key"])
        desc = data.get(spec["desc_key"])
    except Exception:
        pass
    conn.close()
    if not (title and title.strip()):
        title = spec["default_title"]
    if not (desc and desc.strip()):
        desc = spec["default_desc"]
    return title, desc


def save_texts(kind, title=None, desc=None):
    """Simpan template title/desc untuk `kind`.

    None -> field tidak diubah. String kosong/whitespace -> reset ke default
    (baris dihapus dari bot_state).
    """
    spec = MSG_SPECS[kind]
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    for key, val in ((spec["title_key"], title), (spec["desc_key"], desc)):
        if val is None:
            continue
        if val.strip() == "":
            c.execute("DELETE FROM bot_state WHERE key=?", (key,))
        else:
            c.execute(
                "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
                (key, val),
            )
    conn.commit()
    conn.close()


def render_pair(kind, **values):
    """Kembalikan (title, description) untuk `kind` dengan placeholder tersubstitusi."""
    title, desc = load_texts(kind)
    return render_template(title, **values), render_template(desc, **values)


# ── Wrapper khusus tiap jenis (dipakai cog) ─────────────────────────────────────

def load_welcome_texts():
    return load_texts("welcome")


def save_welcome_texts(title=None, desc=None):
    save_texts("welcome", title=title, desc=desc)


def render_welcome(member, store, count):
    """(title, description) untuk embed welcome join."""
    return render_pair("welcome", member=member, store=store, count=count)


def render_boost(member, store):
    """(title, description) untuk embed boost server."""
    return render_pair("boost", member=member, store=store)


def render_leave(member, store, durasi):
    """(title, description) untuk embed member keluar."""
    return render_pair("leave", member=member, store=store, durasi=durasi)
