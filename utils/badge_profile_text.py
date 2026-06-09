"""Logika murni teks embed Badge (/badges) & fallback Profil (/profil).

Cog `cogs/achievements.py` (embed badge) & `cogs/profile.py` (embed fallback bila
render gambar gagal) memakai beberapa teks prosa kecil. Modul ini membuatnya
editable dari panel admin TANPA edit kode.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {name}  -> nama tampilan member
  {store} -> nama toko (STORE_NAME)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_BADGE_TITLE = "🏅 Badge — {name}"
DEFAULT_BADGE_EMPTY = "_Belum ada badge. Yuk mulai dari transaksi pertamamu!_"
DEFAULT_BADGE_FOOTER = "{store}"
DEFAULT_PROFILE_TITLE = "Profil {name}"
DEFAULT_PROFILE_FOOTER = "{store}"

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
BADGE_PROFILE_SPECS = {
    "badge_title": {
        "label": "Badge (/badges) — judul",
        "key": "badge_text_title",
        "default": DEFAULT_BADGE_TITLE,
        "placeholders": ("{name}",),
    },
    "badge_empty": {
        "label": "Badge (/badges) — saat belum ada badge",
        "key": "badge_text_empty",
        "default": DEFAULT_BADGE_EMPTY,
        "placeholders": (),
    },
    "badge_footer": {
        "label": "Badge (/badges) — footer",
        "key": "badge_text_footer",
        "default": DEFAULT_BADGE_FOOTER,
        "placeholders": ("{store}",),
    },
    "profile_title": {
        "label": "Profil (/profil) — judul fallback",
        "key": "profile_text_title",
        "default": DEFAULT_PROFILE_TITLE,
        "placeholders": ("{name}",),
    },
    "profile_footer": {
        "label": "Profil (/profil) — footer fallback",
        "key": "profile_text_footer",
        "default": DEFAULT_PROFILE_FOOTER,
        "placeholders": ("{store}",),
    },
}


def render_template(text, **values):
    """Substitusi placeholder secara aman (str.replace, bukan str.format)."""
    out = text if text is not None else ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def load_text(kind):
    """Ambil teks untuk `kind` (BADGE_PROFILE_SPECS) dari DB; fallback default."""
    spec = BADGE_PROFILE_SPECS[kind]
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
    spec = BADGE_PROFILE_SPECS[kind]
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
