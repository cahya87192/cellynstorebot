"""Tema/kustomisasi Kartu "Achievement Unlocked" (logika murni, tanpa PIL/discord).

Kembaran dari utils/profile_theme.py, tapi untuk kartu notifikasi badge baru
(render_achievement_card di cogs/profile.py). Menyimpan & memvalidasi konfigurasi
tampilan kartu yang bisa diatur admin lewat admin panel: posisi tiap elemen
(drag-and-drop), ukuran & warna font, visibilitas elemen, teks judul, opacity
panel, dan nama file font kustom.

Tema disimpan sebagai JSON di tabel `bot_state` (key `achievement_card_theme`),
sehingga admin panel (Flask) & bot (discord) berbagi sumber yang sama.

Kanvas kartu berukuran ACH_W x ACH_H. Semua koordinat elemen relatif ke kanvas.
"""

import json

from utils.db import get_conn

THEME_KEY = "achievement_card_theme"

# Ukuran kanvas kartu notifikasi achievement (banner pendek).
ACH_W = 880
ACH_H = 300

# Teks judul default (bisa diganti admin lewat panel).
DEFAULT_TITLE = "ACHIEVEMENT UNLOCKED"
MAX_TITLE_LEN = 40

# Elemen yang bisa dikustomisasi + default-nya.
# Tipe "text": punya size, color, bold, show, x, y.
# Tipe "avatar": punya size, show, x, y, ring_color (None = warna tier otomatis).
# Elemen "title" punya atribut tambahan "text" (judul yang bisa diganti).
DEFAULT_THEME = {
    "panel_opacity": 150,          # 0-255, panel gelap di atas background
    "font_file": None,             # nama file font di data/ (None = font default)
    "elements": {
        "avatar": {"type": "avatar", "x": 56,  "y": 75,  "size": 150, "show": True, "ring_color": None},
        "title":  {"type": "text",   "x": 246, "y": 52,  "size": 26, "color": "#F0C85A", "bold": True,  "show": True, "text": DEFAULT_TITLE},
        "name":   {"type": "text",   "x": 246, "y": 92,  "size": 34, "color": "#FFFFFF", "bold": True,  "show": True},
        "badges": {"type": "text",   "x": 246, "y": 150, "size": 22, "color": "#FFFFFF", "bold": True,  "show": True},
        # Ikon/thumbnail dekoratif di sisi KANAN kartu (di-upload via panel:
        # data/badge_icon.<ext>). show=True tapi hanya tampil bila gambar ada,
        # jadi kartu lama tidak berubah sampai owner meng-upload ikon.
        "icon":   {"type": "image",  "x": 690, "y": 80,  "size": 140, "show": True},
    },
}

# Urutan & label ramah untuk ditampilkan di editor.
ELEMENT_LABELS = [
    ("avatar", "Foto Profil"),
    ("title", "Judul"),
    ("name", "Nama Member"),
    ("badges", "Daftar Badge"),
    ("icon", "Ikon/Thumbnail (kanan)"),
]


def _clampi(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def _valid_hex(c, default):
    if not isinstance(c, str):
        return default
    s = c.strip()
    if not s.startswith("#"):
        s = "#" + s
    body = s[1:]
    if len(body) in (3, 6) and all(ch in "0123456789abcdefABCDEF" for ch in body):
        return "#" + body.upper()
    return default


def hex_to_rgb(c) -> tuple:
    """'#RRGGBB' / '#RGB' -> (r,g,b). Fallback putih bila invalid."""
    s = _valid_hex(c, "#FFFFFF")[1:]
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def _ring_color(c, default):
    """Validasi warna bingkai (ring) avatar.

    None/""/invalid -> None artinya "otomatis" (render memakai warna aksen
    tier). String hex valid -> '#RRGGBB' (uppercase) untuk override warna ring.
    """
    if c is None:
        return None
    if isinstance(c, str) and not c.strip():
        return None
    return _valid_hex(c, default)


def default_theme() -> dict:
    """Salinan dalam dari DEFAULT_THEME (aman dimodifikasi pemanggil)."""
    return json.loads(json.dumps(DEFAULT_THEME))


def merge_theme(raw) -> dict:
    """Gabungkan tema tersimpan dengan default + validasi nilai.

    Toleran: input None/rusak/sebagian -> dilengkapi default. Elemen/atribut
    asing diabaikan. Selalu mengembalikan tema lengkap & valid.
    """
    theme = default_theme()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = None
    if not isinstance(raw, dict):
        return theme

    theme["panel_opacity"] = _clampi(raw.get("panel_opacity"), 0, 255,
                                     theme["panel_opacity"])
    ff = raw.get("font_file")
    theme["font_file"] = ff if (isinstance(ff, str) and ff.strip()) else None

    raw_elems = raw.get("elements") if isinstance(raw.get("elements"), dict) else {}
    for key, base in theme["elements"].items():
        incoming = raw_elems.get(key)
        if not isinstance(incoming, dict):
            continue
        base["x"] = _clampi(incoming.get("x", base["x"]), 0, ACH_W, base["x"])
        base["y"] = _clampi(incoming.get("y", base["y"]), 0, ACH_H, base["y"])
        base["show"] = bool(incoming.get("show", base["show"]))
        if base["type"] == "text":
            base["size"] = _clampi(incoming.get("size", base["size"]), 8, 120, base["size"])
            base["color"] = _valid_hex(incoming.get("color", base["color"]), base["color"])
            base["bold"] = bool(incoming.get("bold", base["bold"]))
        elif base["type"] == "avatar":
            base["size"] = _clampi(incoming.get("size", base["size"]), 32, 300, base["size"])
            base["ring_color"] = _ring_color(incoming.get("ring_color", base.get("ring_color")),
                                             base.get("ring_color"))
        elif base["type"] == "image":
            base["size"] = _clampi(incoming.get("size", base["size"]), 32, 300, base["size"])
        # Judul: teks bisa diganti (string non-kosong, dipangkas panjangnya).
        if "text" in base:
            t = incoming.get("text", base["text"])
            if isinstance(t, str) and t.strip():
                base["text"] = t.strip()[:MAX_TITLE_LEN]
            else:
                base["text"] = base["text"]
    return theme


def load_theme() -> dict:
    """Baca tema dari bot_state (atau default bila belum ada)."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT value FROM bot_state WHERE key=?", (THEME_KEY,)).fetchone()
    except Exception:
        row = None
    conn.close()
    return merge_theme(row["value"] if row else None)


def save_theme(raw) -> dict:
    """Validasi + simpan tema ke bot_state. Mengembalikan tema final."""
    theme = merge_theme(raw)
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
        (THEME_KEY, json.dumps(theme)),
    )
    conn.commit()
    conn.close()
    return theme
