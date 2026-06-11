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

# Ukuran kanvas kartu testimoni (banner lebar; ukuran standar welcome-card).
RATING_W = 1024
RATING_H = 450

# Ukuran kanvas LAMA (sebelum diperbesar). Default & tema tersimpan yang dibuat
# pada ukuran ini diskalakan proporsional ke RATING_W x RATING_H saat ini.
_LEGACY_CANVAS = (900, 340)

MAX_TEXT_LEN = 60

# Warna bingkai (ring) avatar default (emas, senada tema rating).
RING_DEFAULT = "#FFC107"

DEFAULT_TITLE = "ULASAN PELANGGAN"

# Elemen yang bisa dikustomisasi + default-nya. Koordinat/ukuran ditulis relatif
# ke `_LEGACY_CANVAS`, lalu diskalakan ke kanvas saat ini di _build_default().
#   - title : teks statis (editable)
#   - name  : dinamis (nama member)
#   - stars : dinamis (mis. "★★★★★")
#   - review: dinamis (teks ulasan, sudah dipangkas; dibungkus multi-baris)
_LEGACY_DEFAULT = {
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


def _build_default() -> dict:
    """DEFAULT_THEME pada kanvas saat ini (koordinat legacy diskalakan + penanda)."""
    theme = json.loads(json.dumps(_LEGACY_DEFAULT))
    theme["canvas"] = [RATING_W, RATING_H]
    lw, lh = _LEGACY_CANVAS
    if (RATING_W, RATING_H) != (lw, lh):
        _base.rescale_elements(theme["elements"], RATING_W / lw, RATING_H / lh)
    return theme


DEFAULT_THEME = _build_default()

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


def _scale_factors(raw, cw, ch):
    """Faktor skala (sx, sy) dari kanvas tema tersimpan ke (cw, ch) saat ini.

    Pakai penanda `canvas`; tema lama tanpa penanda dianggap `_LEGACY_CANVAS`.
    """
    rc = raw.get("canvas") if isinstance(raw, dict) else None
    if isinstance(rc, (list, tuple)) and len(rc) == 2:
        try:
            ocw, och = int(rc[0]), int(rc[1])
        except (TypeError, ValueError):
            ocw, och = _LEGACY_CANVAS
    else:
        ocw, och = _LEGACY_CANVAS
    if ocw <= 0 or och <= 0 or (ocw, och) == (cw, ch):
        return 1.0, 1.0
    return cw / ocw, ch / och


def _smul(v, s):
    """Kalikan nilai numerik dengan faktor `s` (bulatkan). Non-numerik dibiarkan."""
    if s == 1.0:
        return v
    try:
        return int(round(float(v) * s))
    except (TypeError, ValueError):
        return v


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

    # Skalakan koordinat/ukuran bila tema dibuat untuk kanvas berukuran lain.
    sx, sy = _scale_factors(raw, RATING_W, RATING_H)

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
        if "x" in incoming:
            base["x"] = _clampi(_smul(incoming["x"], sx), 0, RATING_W, base["x"])
        if "y" in incoming:
            base["y"] = _clampi(_smul(incoming["y"], sy), 0, RATING_H, base["y"])
        base["show"] = bool(incoming.get("show", base["show"]))
        if base["type"] == "text":
            if "size" in incoming:
                base["size"] = _clampi(_smul(incoming["size"], sy), 8, 120, base["size"])
            base["color"] = _valid_hex(incoming.get("color", base["color"]), base["color"])
            base["bold"] = bool(incoming.get("bold", base["bold"]))
        elif base["type"] == "avatar":
            if "size" in incoming:
                base["size"] = _clampi(_smul(incoming["size"], sy), 32, 320, base["size"])
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
