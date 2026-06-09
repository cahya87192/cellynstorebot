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
import json

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



# ── DM sambutan member baru (embed multi-field + thumbnail + banner) ─────────────
# DM dikirim sebagai DUA embed dalam satu pesan supaya banner bisa di ATAS teks:
#   embeds = [banner_embed (hanya gambar), text_embed (judul/isi/field/thumbnail)]
# Discord menumpuk beberapa embed -> banner tampil di atas. Bila banner kosong,
# hanya text_embed yang dikirim (perilaku lama). Placeholder: {member}, {store}.

DEFAULT_DM_THUMBNAIL = "https://i.imgur.com/4lpmtpL.png"
DEFAULT_DM_TITLE = "🤍 Selamat Datang di {store}!"
DEFAULT_DM_DESC = (
    "Hai **{member}**! 👋\n"
    "Makasih banyak udah gabung ke **{store}** — tempat jual-beli "
    "& top-up digital yang aman dan terpercaya. Biar kamu makin nyaman "
    "belanja, baca info singkat di bawah ini ya 🙏"
)
DEFAULT_DM_FOOTER = "{store} • Selamat berbelanja & semoga betah! 🤍"
DEFAULT_DM_FIELDS = [
    {
        "name": "🏪 Tentang Kami",
        "value": (
            "{store} melayani kebutuhan game & akunmu dengan proses "
            "**cepat**, harga **bersahabat**, dan admin yang **ramah**. "
            "Setiap transaksi memakai sistem **tiket** + **garansi** supaya aman."
        ),
    },
    {
        "name": "🛍️ Layanan Kami",
        "value": (
            "• Top-up Mobile Legends & Free Fire\n"
            "• Robux (Store, Via Login, Gamepass)\n"
            "• Middleman Trade & Jual Beli\n"
            "• Cloud Phone & Discord Nitro\n"
            "• dan layanan lainnya!"
        ),
    },
    {
        "name": "📜 Peraturan Singkat",
        "value": (
            "**1.** Hormati semua member & admin — no toxic/SARA.\n"
            "**2.** Dilarang spam & promosi toko lain tanpa izin.\n"
            "**3.** Transaksi **WAJIB** lewat tiket & admin resmi — "
            "waspada admin palsu/penipu!\n"
            "**4.** Selalu simpan bukti pembayaranmu.\n"
            "**5.** Jangan lupa beri **rating** tiap selesai order — "
            "rating = garansimu aktif."
        ),
    },
    {
        "name": "💬 Siap Order?",
        "value": (
            "Buka tiket di channel layanan yang sesuai, admin kami siap bantu. "
            "Kalau ada pertanyaan, tanya aja langsung di server ya!"
        ),
    },
]

DM_TITLE_KEY = "dm_title"
DM_DESC_KEY = "dm_desc"
DM_FOOTER_KEY = "dm_footer"
DM_THUMBNAIL_KEY = "dm_thumbnail"
DM_BANNER_KEY = "dm_banner"
DM_FIELDS_KEY = "dm_fields"
DM_KEYS = (DM_TITLE_KEY, DM_DESC_KEY, DM_FOOTER_KEY,
           DM_THUMBNAIL_KEY, DM_BANNER_KEY, DM_FIELDS_KEY)


def parse_dm_fields(raw):
    """Parse JSON array field -> list[{name, value}]. Toleran rusak -> None.

    Field dengan name & value kosong keduanya dibuang. None dipakai sebagai
    sinyal 'belum diatur' (pakai default).
    """
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, list):
        return None
    out = []
    for it in data:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name", "") or "").strip()
        value = str(it.get("value", "") or "").strip()
        if name or value:
            out.append({"name": name, "value": value})
    return out


def load_dm_config():
    """Ambil konfigurasi DM sambutan (gabungan custom + default).

    Return dict: {title, desc, footer, thumbnail, banner, fields}.
    `banner` default kosong (= tanpa banner). `thumbnail` default = bawaan.
    """
    from utils.db import get_conn
    data = {}
    conn = get_conn()
    try:
        placeholders = ",".join(["?"] * len(DM_KEYS))
        rows = conn.execute(
            "SELECT key, value FROM bot_state WHERE key IN (%s)" % placeholders,
            DM_KEYS,
        ).fetchall()
        data = {r["key"]: r["value"] for r in rows}
    except Exception:
        pass
    conn.close()

    def _t(key, default):
        v = data.get(key)
        return v if (v and v.strip()) else default

    fields = parse_dm_fields(data.get(DM_FIELDS_KEY))
    if fields is None:
        fields = [dict(f) for f in DEFAULT_DM_FIELDS]
    return {
        "title": _t(DM_TITLE_KEY, DEFAULT_DM_TITLE),
        "desc": _t(DM_DESC_KEY, DEFAULT_DM_DESC),
        "footer": _t(DM_FOOTER_KEY, DEFAULT_DM_FOOTER),
        "thumbnail": _t(DM_THUMBNAIL_KEY, DEFAULT_DM_THUMBNAIL),
        "banner": (data.get(DM_BANNER_KEY) or "").strip(),
        "fields": fields,
    }


def save_dm_config(title=None, desc=None, footer=None, thumbnail=None,
                   banner=None, fields=None):
    """Simpan konfigurasi DM. None -> tidak diubah. String kosong -> reset field
    teks itu ke default (baris dihapus). `fields` (list) selalu ditulis bila
    diberikan (list kosong tetap disimpan sebagai []).
    """
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    text_items = (
        (DM_TITLE_KEY, title), (DM_DESC_KEY, desc), (DM_FOOTER_KEY, footer),
        (DM_THUMBNAIL_KEY, thumbnail), (DM_BANNER_KEY, banner),
    )
    for key, val in text_items:
        if val is None:
            continue
        if val.strip() == "":
            c.execute("DELETE FROM bot_state WHERE key=?", (key,))
        else:
            c.execute(
                "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
                (key, val.strip()),
            )
    if fields is not None:
        cleaned = parse_dm_fields(json.dumps(fields)) or []
        c.execute(
            "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
            (DM_FIELDS_KEY, json.dumps(cleaned, ensure_ascii=False)),
        )
    conn.commit()
    conn.close()


def reset_dm_config():
    """Hapus semua kustomisasi DM -> kembali ke default."""
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    for key in DM_KEYS:
        c.execute("DELETE FROM bot_state WHERE key=?", (key,))
    conn.commit()
    conn.close()


def render_dm(member, store):
    """Konfigurasi DM siap pakai dengan placeholder tersubstitusi.

    Return dict {title, desc, footer, thumbnail|None, banner|None, fields}.
    """
    cfg = load_dm_config()

    def r(text):
        return render_template(text, member=member, store=store)

    return {
        "title": r(cfg["title"]),
        "desc": r(cfg["desc"]),
        "footer": r(cfg["footer"]),
        "thumbnail": cfg["thumbnail"] or None,
        "banner": cfg["banner"] or None,
        "fields": [
            {"name": r(f.get("name", "")), "value": r(f.get("value", ""))}
            for f in cfg["fields"]
        ],
    }
