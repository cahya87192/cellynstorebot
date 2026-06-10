"""Tema/kustomisasi Kartu Testimoni/Rating (logika murni, tanpa PIL/discord).

Kembaran dari utils/achievement_theme.py & utils/welcome_theme.py, tapi untuk
kartu ulasan pelanggan yang diposting ke channel testimoni saat member memberi
rating (render_rating_card di cogs/profile.py).

Elemen kartu sengaja ringkas (sesuai permintaan): hanya judul, foto profil,
jumlah bintang, dan teks ulasan — TANPA nama layanan agar tidak penuh.

Menyimpan & memvalidasi konfigurasi tampilan yang bisa diatur admin lewat panel:
posisi tiap elemen (drag-and-drop), ukuran & warna font, visibilitas, teks judul,
warna bingkai (ring) avatar, opacity panel, nama file font kustom, dan flag
`enabled` (pakai kartu gambar atau tetap embed teks klasik).

Tema disimpan sebagai JSON di tabel `bot_state` (key `rating_card_theme`),
sehingga admin panel (Flask) & bot (discord) berbagi sumber yang sama.

Kanvas kartu berukuran RATING_W x RATING_H. Semua koordinat relatif ke kanvas.
"""

import json

from utils import card_theme_base as _base

THEME_KEY = "rating_card_theme"

# Ukuran kanvas kartu testimoni (banner lebar).
RATING_W = 900
RATING_H = 340

MAX_TEXT_LEN = 60

# Warna bingkai (ring) avatar default (emas, senada tema rating).
RING_DEFAULT = "#FFC107"

DEFAULT_TITLE = "ULASAN PELANGGAN"

# Elemen yang bisa dikustomisasi + default-nya.
#   - title : teks statis (editable)
#   - name  : dinamis (nama member)
#   - stars : dinamis (mis. "★★★★★")
#   - review: dinamis (teks ulasan, sudah dipangkas; dibungkus multi-baris)
DEFAULT_THEME = {
    "enabled": False,              # False = tetap pakai embed testimoni klasik
    "panel_opacity": 150,          # 0-255, panel gelap di atas background
    "font_file": None,             # nama file font di data/ (None = font default)
    "elements": {
        "avatar": {"type": "avatar", "x": 60,  "y": 90,  "size": 160, "show": True, "ring_color": RING_DEFAULT},
        "title":  {"type": "text",   "x": 268, "y": 56,  "size": 28, "color": "#FFC107", "bold": True,  "show": True, "text": DEFAULT_TITLE},
        "name":   {"type": "text",   "x": 268, "y": 104, "size": 38, "color": "#FFFFFF", "bold": True,  "show": True},
        "stars":  {"type": "text",   "x": 268, "y": 162, "size": 34, "color": "#FFD24D", "bold": True,  "show": True},
        "review": {"type": "text",   "x": 268, "y": 224, "size": 24, "color": "#E2E4EC", "bold": False, "show": True},
    },
}

# Urutan & label ramah untuk ditampilkan di editor.
ELEMENT_LABELS = [
    ("avatar", "Foto Profil"),
    ("title", "Judul"),
    ("name", "Nama Pelanggan"),
    ("stars", "Bintang Rating"),
    ("review", "Teks Ulasan"),
]


# Helper umum dipusatkan di utils/card_theme_base.py. Alias lokal dipertahankan
# untuk kompatibilitas (kode lain & test yang mengaksesnya langsung).
_clampi = _base.clampi
_valid_hex = _base.valid_hex
hex_to_rgb = _base.hex_to_rgb


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
        base["x"] = _clampi(incoming.get("x", base["x"]), 0, RATING_W, base["x"])
        base["y"] = _clampi(incoming.get("y", base["y"]), 0, RATING_H, base["y"])
        base["show"] = bool(incoming.get("show", base["show"]))
        if base["type"] == "text":
            base["size"] = _clampi(incoming.get("size", base["size"]), 8, 120, base["size"])
            base["color"] = _valid_hex(incoming.get("color", base["color"]), base["color"])
            base["bold"] = bool(incoming.get("bold", base["bold"]))
        elif base["type"] == "avatar":
            base["size"] = _clampi(incoming.get("size", base["size"]), 32, 320, base["size"])
            base["ring_color"] = _valid_hex(incoming.get("ring_color", base["ring_color"]),
                                            base["ring_color"])
        if "text" in base:
            t = incoming.get("text", base["text"])
            if isinstance(t, str) and t.strip():
                base["text"] = t.strip()[:MAX_TEXT_LEN]
    return theme


def load_theme() -> dict:
    """Baca tema dari bot_state (atau default bila belum ada)."""
    return merge_theme(_base.read_state(THEME_KEY))


def save_theme(raw) -> dict:
    """Validasi + simpan tema ke bot_state. Mengembalikan tema final."""
    theme = merge_theme(raw)
    _base.write_state(THEME_KEY, theme)
    return theme
