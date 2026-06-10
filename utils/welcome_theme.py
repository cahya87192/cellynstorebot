"""Tema/kustomisasi Kartu Welcome (logika murni, tanpa PIL/discord).

Kembaran dari utils/achievement_theme.py, tapi untuk kartu sambutan member baru
(render_welcome_card di cogs/profile.py). Menyimpan & memvalidasi konfigurasi
tampilan kartu yang bisa diatur admin lewat admin panel: posisi tiap elemen
(drag-and-drop), ukuran & warna font, visibilitas elemen, teks judul & subjudul,
opacity panel, nama file font kustom, dan flag `enabled` (pakai kartu gambar
atau embed teks klasik).

Tema disimpan sebagai JSON di tabel `bot_state` (key `welcome_card_theme`),
sehingga admin panel (Flask) & bot (discord) berbagi sumber yang sama.

Kanvas kartu berukuran WELCOME_W x WELCOME_H. Semua koordinat relatif ke kanvas.
"""

import json

from utils.db import get_conn

THEME_KEY = "welcome_card_theme"

# Ukuran kanvas kartu sambutan (banner lebar).
WELCOME_W = 1000
WELCOME_H = 360

# Teks default (bisa diganti admin lewat panel).
DEFAULT_TITLE = "SELAMAT DATANG"
DEFAULT_SUBTITLE = "Selamat bergabung di server!"
MAX_TEXT_LEN = 60

# Elemen yang bisa dikustomisasi + default-nya.
# Tipe "text": punya size, color, bold, show, x, y (+ "text" bila bisa diedit).
# Tipe "avatar": punya size, show, x, y.
DEFAULT_THEME = {
    "enabled": False,              # False = tetap pakai embed klasik (perilaku lama)
    "panel_opacity": 140,          # 0-255, panel gelap di atas background
    "font_file": None,             # nama file font di data/ (None = font default)
    "elements": {
        "avatar":     {"type": "avatar", "x": 70,  "y": 95,  "size": 170, "show": True},
        "title":      {"type": "text",   "x": 290, "y": 78,  "size": 30, "color": "#FFFFFF", "bold": True,  "show": True, "text": DEFAULT_TITLE},
        "name":       {"type": "text",   "x": 290, "y": 128, "size": 46, "color": "#8B9BE0", "bold": True,  "show": True},
        "subtitle":   {"type": "text",   "x": 290, "y": 200, "size": 24, "color": "#D8DCE6", "bold": False, "show": True, "text": DEFAULT_SUBTITLE},
        "membercount":{"type": "text",   "x": 290, "y": 248, "size": 22, "color": "#A6B1C6", "bold": False, "show": True},
    },
}

# Urutan & label ramah untuk ditampilkan di editor.
ELEMENT_LABELS = [
    ("avatar", "Foto Profil"),
    ("title", "Judul"),
    ("name", "Nama Member"),
    ("subtitle", "Subjudul / Pesan"),
    ("membercount", "Jumlah Member"),
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

    theme["enabled"] = bool(raw.get("enabled", theme["enabled"]))
    theme["panel_opacity"] = _clampi(raw.get("panel_opacity"), 0, 255,
                                     theme["panel_opacity"])
    ff = raw.get("font_file")
    theme["font_file"] = ff if (isinstance(ff, str) and ff.strip()) else None

    raw_elems = raw.get("elements") if isinstance(raw.get("elements"), dict) else {}
    for key, base in theme["elements"].items():
        incoming = raw_elems.get(key)
        if not isinstance(incoming, dict):
            continue
        base["x"] = _clampi(incoming.get("x", base["x"]), 0, WELCOME_W, base["x"])
        base["y"] = _clampi(incoming.get("y", base["y"]), 0, WELCOME_H, base["y"])
        base["show"] = bool(incoming.get("show", base["show"]))
        if base["type"] == "text":
            base["size"] = _clampi(incoming.get("size", base["size"]), 8, 120, base["size"])
            base["color"] = _valid_hex(incoming.get("color", base["color"]), base["color"])
            base["bold"] = bool(incoming.get("bold", base["bold"]))
        elif base["type"] == "avatar":
            base["size"] = _clampi(incoming.get("size", base["size"]), 32, 320, base["size"])
        # Elemen yang punya teks bisa diganti (string non-kosong, dipangkas).
        if "text" in base:
            t = incoming.get("text", base["text"])
            if isinstance(t, str) and t.strip():
                base["text"] = t.strip()[:MAX_TEXT_LEN]
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
