"""Logika murni teks pesan sistem AFK (cogs/afk.py).

Cog `cogs/afk.py` membaca teks lewat fungsi render_text() di sini sehingga admin
bisa mengubah pesan dari panel TANPA edit kode. Bila belum dikustomisasi, dipakai
teks default (sama persis dengan perilaku sebelumnya).

Placeholder yang didukung (diganti otomatis saat dikirim):
  {member} -> mention member (set AFK / back / sudah AFK)
  {reason} -> alasan AFK
  {name}   -> nama tampilan member yang di-mention (notif AFK)
  {durasi} -> lama AFK (notif AFK)

Modul ini self-contained (tidak berbagi state dengan editor lain) dan hanya
menyentuh SQLite (bot_state) -> gampang diuji, tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_SET = "{member} sekarang AFK: **{reason}**"
DEFAULT_BACK = "Selamat datang kembali {member}, kamu sudah tidak AFK."
DEFAULT_MENTION = "**{name}** sedang AFK: {reason} • {durasi}"
DEFAULT_ALREADY = "{member} kamu sudah AFK."

# Registry tiap jenis pesan: kunci DB + default + placeholder yang relevan.
AFK_SPECS = {
    "set": {
        "label": "Set AFK (saat member jalankan !afk)",
        "key": "afk_set_text",
        "default": DEFAULT_SET,
        "placeholders": ("{member}", "{reason}"),
    },
    "back": {
        "label": "Kembali (member tidak lagi AFK)",
        "key": "afk_back_text",
        "default": DEFAULT_BACK,
        "placeholders": ("{member}",),
    },
    "mention": {
        "label": "Notif mention (ada yang mention member AFK)",
        "key": "afk_mention_text",
        "default": DEFAULT_MENTION,
        "placeholders": ("{name}", "{reason}", "{durasi}"),
    },
    "already": {
        "label": "Sudah AFK (member jalankan !afk padahal sudah AFK)",
        "key": "afk_already_text",
        "default": DEFAULT_ALREADY,
        "placeholders": ("{member}",),
    },
}


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


def load_text(kind):
    """Ambil teks untuk `kind` (AFK_SPECS) dari DB; fallback default.

    Nilai kosong / whitespace dianggap belum diisi -> pakai default.
    """
    spec = AFK_SPECS[kind]
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
    spec = AFK_SPECS[kind]
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
