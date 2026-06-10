"""Tema/kustomisasi Kartu Profil Member (logika murni, tanpa PIL/discord).

Menyimpan & memvalidasi konfigurasi tampilan kartu profil yang bisa diatur admin
lewat admin panel: posisi tiap elemen (drag-and-drop), ukuran & warna font,
visibilitas elemen, opacity panel, dan nama file font kustom.

Tema disimpan sebagai JSON di tabel `bot_state` (key `profile_card_theme`),
sehingga admin panel (Flask) & bot (discord) berbagi sumber yang sama.

Kanvas kartu berukuran CARD_W x CARD_H. Semua koordinat elemen relatif ke kanvas.
"""

import json

from utils.db import get_conn

THEME_KEY = "profile_card_theme"

CARD_W = 900
CARD_H = 360

# Elemen yang bisa dikustomisasi + default-nya.
# Tipe "text": punya size, color, bold, show, x, y.
# Tipe "avatar": punya size, show, x, y, ring_color (None = warna tier otomatis).
# Tipe "bar": punya w, h, color, show, x, y (+ teks XP terpisah: xptext).
DEFAULT_THEME = {
    "panel_opacity": 120,          # 0-255, panel gelap di atas background
    "font_file": None,             # nama file font di data/ (None = font default)
    "elements": {
        "avatar": {"type": "avatar", "x": 60,  "y": 70,  "size": 150, "show": True, "ring_color": None},
        "name":   {"type": "text",   "x": 256, "y": 60,  "size": 46, "color": "#FFFFFF", "bold": True,  "show": True},
        "tier":   {"type": "text",   "x": 256, "y": 116, "size": 26, "color": "#F0C85A", "bold": True,  "show": True},
        "since":  {"type": "text",   "x": 256, "y": 152, "size": 20, "color": "#DCDCE6", "bold": False, "show": True},
        "xpbar":  {"type": "bar",    "x": 256, "y": 196, "w": 584, "h": 26, "color": "#F0C85A", "show": True},
        "xptext": {"type": "text",   "x": 256, "y": 230, "size": 18, "color": "#E1E1EB", "bold": False, "show": True},
        "stats":  {"type": "text",   "x": 60,  "y": 286, "size": 28, "color": "#FFFFFF", "bold": True,  "show": True},
        "badges": {"type": "text",   "x": 60,  "y": 326, "size": 18, "color": "#F0C85A", "bold": True,  "show": True},
    },
}

# Urutan & label ramah untuk ditampilkan di editor.
ELEMENT_LABELS = [
    ("avatar", "Foto Profil"),
    ("name", "Nama Member"),
    ("tier", "Tier & Level"),
    ("since", "Member Sejak"),
    ("xpbar", "Bar XP"),
    ("xptext", "Teks XP"),
    ("stats", "Statistik"),
    ("badges", "Badge"),
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
        base["x"] = _clampi(incoming.get("x", base["x"]), 0, CARD_W, base["x"])
        base["y"] = _clampi(incoming.get("y", base["y"]), 0, CARD_H, base["y"])
        base["show"] = bool(incoming.get("show", base["show"]))
        if base["type"] == "text":
            base["size"] = _clampi(incoming.get("size", base["size"]), 8, 120, base["size"])
            base["color"] = _valid_hex(incoming.get("color", base["color"]), base["color"])
            base["bold"] = bool(incoming.get("bold", base["bold"]))
        elif base["type"] == "avatar":
            base["size"] = _clampi(incoming.get("size", base["size"]), 32, 300, base["size"])
            base["ring_color"] = _ring_color(incoming.get("ring_color", base.get("ring_color")),
                                             base.get("ring_color"))
        elif base["type"] == "bar":
            base["w"] = _clampi(incoming.get("w", base["w"]), 50, CARD_W, base["w"])
            base["h"] = _clampi(incoming.get("h", base["h"]), 6, 80, base["h"])
            base["color"] = _valid_hex(incoming.get("color", base["color"]), base["color"])
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
