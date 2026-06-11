"""Tema/kustomisasi Kartu Top Spender (leaderboard sebagai gambar).

Logika murni (tanpa PIL/discord) -> gampang diuji. Berbeda dari kartu
welcome/rating yang berbasis posisi elemen tunggal (drag-drop), leaderboard
adalah DAFTAR baris berulang, jadi tema di sini berbasis SETTING: warna, jumlah
baris, opacity panel, warna background, font, dan toggle aktif.

Teks judul/footer/benefit untuk versi EMBED tetap dari utils.top_spender_text;
kartu gambar memakai judul ringkas (nama bulan) + total otomatis.

Disimpan di bot_state key `topspender_card_theme`.
"""
from utils import card_theme_base as _base

THEME_KEY = "topspender_card_theme"

# Lebar kanvas tetap; tinggi dihitung saat render sesuai jumlah baris.
CARD_W = 1000

# Warna teks yang bisa dikustomisasi.
COLOR_KEYS = ("title", "subtitle", "rank", "name", "amount", "divider", "total")

_DEFAULT_COLORS = {
    "title": "#F0C04A",
    "subtitle": "#D8DCE6",
    "rank": "#AAB2C5",
    "name": "#FFFFFF",
    "amount": "#FFD24D",
    "divider": "#3A3F4B",
    "total": "#5FD18C",
}

# Batas jumlah baris yang ditampilkan di gambar.
ROWS_MIN = 3
ROWS_MAX = 20


def default_theme() -> dict:
    """Tema default kartu Top Spender (gambar)."""
    return {
        "enabled": False,            # False = tetap pakai embed teks klasik
        "panel_opacity": 165,        # 0-255, panel gelap di atas background
        "font_file": None,           # nama file font di data/ (None = font default)
        "rows": 10,                  # jumlah peringkat yang digambar
        "show_avatars": True,        # top-3 pakai foto profil + medali
        "bg_color1": "#1B1E27",      # gradien latar (atas) bila tanpa background
        "bg_color2": "#0E1015",      # gradien latar (bawah)
        "colors": dict(_DEFAULT_COLORS),
    }


def merge_theme(raw) -> dict:
    """Validasi & gabungkan tema mentah (dict/JSON/None) dengan default."""
    import json
    theme = default_theme()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = None
    if not isinstance(raw, dict):
        return theme

    theme["enabled"] = bool(raw.get("enabled", theme["enabled"]))
    theme["panel_opacity"] = _base.clampi(raw.get("panel_opacity"), 0, 255,
                                          theme["panel_opacity"])
    theme["rows"] = _base.clampi(raw.get("rows"), ROWS_MIN, ROWS_MAX, theme["rows"])
    theme["show_avatars"] = bool(raw.get("show_avatars", theme["show_avatars"]))
    ff = raw.get("font_file")
    theme["font_file"] = ff if (isinstance(ff, str) and ff.strip()) else None
    theme["bg_color1"] = _base.valid_hex(raw.get("bg_color1"), theme["bg_color1"])
    theme["bg_color2"] = _base.valid_hex(raw.get("bg_color2"), theme["bg_color2"])

    rc = raw.get("colors") if isinstance(raw.get("colors"), dict) else {}
    for k in COLOR_KEYS:
        theme["colors"][k] = _base.valid_hex(rc.get(k, theme["colors"][k]),
                                             theme["colors"][k])
    return theme


def load_theme() -> dict:
    """Baca tema tersimpan dari bot_state; fallback default."""
    return merge_theme(_base.read_state(THEME_KEY))


def save_theme(raw) -> dict:
    """Validasi lalu simpan tema ke bot_state. Kembalikan tema final."""
    theme = merge_theme(raw)
    _base.write_state(THEME_KEY, theme)
    return theme


hex_to_rgb = _base.hex_to_rgb
