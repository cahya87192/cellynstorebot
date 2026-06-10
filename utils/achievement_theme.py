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

from utils import card_theme_base as _base

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


# Helper umum dipusatkan di utils/card_theme_base.py. Alias lokal dipertahankan
# untuk kompatibilitas (kode lain & test yang mengaksesnya langsung).
_clampi = _base.clampi
_valid_hex = _base.valid_hex
hex_to_rgb = _base.hex_to_rgb
_ring_color = _base.ring_color_auto


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
    return merge_theme(_base.read_state(THEME_KEY))


def save_theme(raw) -> dict:
    """Validasi + simpan tema ke bot_state. Mengembalikan tema final."""
    theme = merge_theme(raw)
    _base.write_state(THEME_KEY, theme)
    return theme
