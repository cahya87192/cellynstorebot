"""Logika murni teks pesan Welcome (sambutan member baru di channel welcome).

Cog `cogs/welcome.py` membaca teks lewat `render_welcome()` sehingga admin bisa
mengubah judul & isi sambutan dari panel TANPA edit kode. Bila belum dikustomisasi,
dipakai teks default (sama persis dengan perilaku sebelumnya).

Placeholder yang didukung (akan diganti otomatis saat dikirim):
  {member} -> nama tampilan member
  {store}  -> nama toko
  {count}  -> nomor urut member (jumlah member non-bot)

Semua fungsi murni / hanya menyentuh SQLite (bot_state) -> gampang diuji, tanpa
butuh discord.
"""

WELCOME_TITLE_KEY = "welcome_title"
WELCOME_DESC_KEY = "welcome_desc"

DEFAULT_WELCOME_TITLE = "Halo {member}, selamat datang di {store}! "
DEFAULT_WELCOME_DESC = (
    "Makasih ya udah mampir dan gabung bareng kami\n"
    "Sekarang kamu jadi bagian ke-**{count}** dari keluarga kecil ini.\n\n"
    "Santai aja, anggap rumah sendiri. Kalau mau tanya-tanya produk atau "
    "butuh bantuan, jangan sungkan — kami siap bantu kapan pun. 🤝"
)

PLACEHOLDERS = ("{member}", "{store}", "{count}")


def render_template(text, *, member="", store="", count=""):
    """Substitusi placeholder secara aman.

    Memakai str.replace (bukan str.format) supaya kurung kurawal lain di teks
    tidak memicu error. None -> string kosong.
    """
    out = text if text is not None else ""
    out = out.replace("{member}", str(member))
    out = out.replace("{store}", str(store))
    out = out.replace("{count}", str(count))
    return out


def load_welcome_texts():
    """Ambil (title_template, desc_template) dari DB; fallback ke default.

    Nilai kosong / whitespace dianggap belum diisi -> pakai default.
    """
    from utils.db import get_conn
    title = desc = None
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT key, value FROM bot_state WHERE key IN (?,?)",
            (WELCOME_TITLE_KEY, WELCOME_DESC_KEY),
        ).fetchall()
        data = {r["key"]: r["value"] for r in rows}
        title = data.get(WELCOME_TITLE_KEY)
        desc = data.get(WELCOME_DESC_KEY)
    except Exception:
        pass
    conn.close()
    if not (title and title.strip()):
        title = DEFAULT_WELCOME_TITLE
    if not (desc and desc.strip()):
        desc = DEFAULT_WELCOME_DESC
    return title, desc


def save_welcome_texts(title=None, desc=None):
    """Simpan template title/desc ke DB.

    None -> field tidak diubah. String kosong/whitespace -> reset ke default
    (baris dihapus dari bot_state).
    """
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    for key, val in ((WELCOME_TITLE_KEY, title), (WELCOME_DESC_KEY, desc)):
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


def render_welcome(member, store, count):
    """Kembalikan (title, description) siap pakai untuk embed welcome join."""
    title, desc = load_welcome_texts()
    return (
        render_template(title, member=member, store=store, count=count),
        render_template(desc, member=member, store=store, count=count),
    )
