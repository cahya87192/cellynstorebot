"""Tema/kustomisasi Kartu Notifikasi member (welcome / boost / leave).

Logika murni (tanpa PIL/discord). Satu modul melayani TIGA jenis kartu yang
strukturnya sama persis tapi default teks/warna berbeda:

  - welcome : sambutan member baru (key DB `welcome_card_theme`)
  - boost   : ucapan terima kasih member nge-boost (key `boost_card_theme`)
  - leave   : pamitan member keluar (key `leave_card_theme`)

Tiap kartu menyimpan & memvalidasi konfigurasi tampilan yang bisa diatur admin
lewat panel: posisi tiap elemen (drag-and-drop), ukuran & warna font,
visibilitas elemen, teks judul & subjudul, warna bingkai (ring) avatar, opacity
panel, nama file font kustom, dan flag `enabled` (pakai kartu gambar atau embed
teks klasik).

Tema disimpan sebagai JSON di tabel `bot_state` (satu key per jenis), sehingga
admin panel (Flask) & bot (discord) berbagi sumber yang sama.

API berbasis `kind` dengan default "welcome" agar pemanggil lama tetap jalan
tanpa perubahan: `load_theme()`, `merge_theme(raw)`, `save_theme(raw)`,
`default_theme()` tanpa argumen kind = welcome (backward compatible).

Kanvas tiap kartu berukuran CANVAS[kind] = (W, H). Semua koordinat relatif ke
kanvas. Untuk kompatibilitas, WELCOME_W/WELCOME_H = kanvas welcome.
"""

import json

from utils import card_theme_base as _base

# Jenis kartu yang didukung.
KINDS = ("welcome", "boost", "leave")

# Key bot_state per jenis (welcome dipertahankan agar data lama kompatibel).
THEME_KEYS = {
    "welcome": "welcome_card_theme",
    "boost": "boost_card_theme",
    "leave": "leave_card_theme",
}

# Ukuran kanvas per jenis (semua banner lebar yang sama saat ini).
CANVAS = {
    "welcome": (1000, 360),
    "boost": (1000, 360),
    "leave": (1000, 360),
}

# Kompatibilitas: alias kanvas welcome + key welcome.
WELCOME_W, WELCOME_H = CANVAS["welcome"]
THEME_KEY = THEME_KEYS["welcome"]

MAX_TEXT_LEN = 60

# Warna bingkai (ring) avatar default per jenis (hex).
RING_DEFAULTS = {
    "welcome": "#8B9BE0",   # periwinkle kalem
    "boost": "#FF73FA",     # pink boost
    "leave": "#9AA3B2",     # abu kalem
}

# Teks & warna default per jenis. Skema elemen identik antar jenis:
# avatar, title, name, subtitle, membercount.
#   - title/subtitle : teks statis (editable)
#   - name           : dinamis (nama member)
#   - membercount    : dinamis (mis. "Member #12" / "3x boost" / "Tersisa 40 member")
_KIND_DEFAULTS = {
    "welcome": {
        "title": "SELAMAT DATANG",
        "subtitle": "Selamat bergabung di server!",
        "name_color": "#8B9BE0",
        "title_color": "#FFFFFF",
        "subtitle_color": "#D8DCE6",
        "count_color": "#A6B1C6",
    },
    "boost": {
        "title": "TERIMA KASIH BOOST!",
        "subtitle": "Dukunganmu bikin server makin keren 🚀",
        "name_color": "#FF8BFB",
        "title_color": "#FFFFFF",
        "subtitle_color": "#F0D8EE",
        "count_color": "#E0A6D6",
    },
    "leave": {
        "title": "SAMPAI JUMPA",
        "subtitle": "Terima kasih atas kebersamaannya 🤍",
        "name_color": "#C7CDD8",
        "title_color": "#FFFFFF",
        "subtitle_color": "#CDD2DC",
        "count_color": "#9AA3B2",
    },
}

# Urutan & label ramah untuk ditampilkan di editor (sama untuk semua jenis).
ELEMENT_ORDER = ["avatar", "title", "name", "subtitle", "membercount"]
ELEMENT_LABELS_MAP = {
    "avatar": "Foto Profil",
    "title": "Judul",
    "name": "Nama Member",
    "subtitle": "Subjudul / Pesan",
    "membercount": "Info Tambahan",
}

# Kompatibilitas: list (key,label) versi welcome.
ELEMENT_LABELS = [(k, ELEMENT_LABELS_MAP[k]) for k in ELEMENT_ORDER]


def element_labels(kind="welcome"):
    """Daftar (key, label) elemen untuk `kind` (urutan ELEMENT_ORDER)."""
    return [(k, ELEMENT_LABELS_MAP[k]) for k in ELEMENT_ORDER]


def _normalize_kind(kind):
    return kind if kind in KINDS else "welcome"


# Helper umum dipusatkan di utils/card_theme_base.py. Alias lokal dipertahankan
# untuk kompatibilitas (kode lain & test yang mengaksesnya langsung).
_clampi = _base.clampi
_valid_hex = _base.valid_hex
hex_to_rgb = _base.hex_to_rgb


def _build_default(kind) -> dict:
    """Susun DEFAULT_THEME untuk `kind`."""
    kind = _normalize_kind(kind)
    d = _KIND_DEFAULTS[kind]
    ring = RING_DEFAULTS[kind]
    return {
        "enabled": False,            # False = tetap pakai embed klasik (perilaku lama)
        "panel_opacity": 140,        # 0-255, panel gelap di atas background
        "font_file": None,           # nama file font di data/ (None = font default)
        "elements": {
            "avatar":      {"type": "avatar", "x": 70,  "y": 95,  "size": 170, "show": True, "ring_color": ring},
            "title":       {"type": "text",   "x": 290, "y": 78,  "size": 30, "color": d["title_color"],    "bold": True,  "show": True, "text": d["title"]},
            "name":        {"type": "text",   "x": 290, "y": 128, "size": 46, "color": d["name_color"],     "bold": True,  "show": True},
            "subtitle":    {"type": "text",   "x": 290, "y": 200, "size": 24, "color": d["subtitle_color"], "bold": False, "show": True, "text": d["subtitle"]},
            "membercount": {"type": "text",   "x": 290, "y": 248, "size": 22, "color": d["count_color"],    "bold": False, "show": True},
        },
    }


# DEFAULT_THEME welcome dipertahankan sebagai konstanta (kompatibilitas).
DEFAULT_THEME = _build_default("welcome")


def default_theme(kind="welcome") -> dict:
    """Salinan dalam dari default untuk `kind` (aman dimodifikasi pemanggil)."""
    return json.loads(json.dumps(_build_default(kind)))


def merge_theme(raw, kind="welcome") -> dict:
    """Gabungkan tema tersimpan dengan default `kind` + validasi nilai.

    Toleran: input None/rusak/sebagian -> dilengkapi default. Elemen/atribut
    asing diabaikan. Selalu mengembalikan tema lengkap & valid.
    """
    kind = _normalize_kind(kind)
    cw, ch = CANVAS[kind]
    theme = default_theme(kind)
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
        base["x"] = _clampi(incoming.get("x", base["x"]), 0, cw, base["x"])
        base["y"] = _clampi(incoming.get("y", base["y"]), 0, ch, base["y"])
        base["show"] = bool(incoming.get("show", base["show"]))
        if base["type"] == "text":
            base["size"] = _clampi(incoming.get("size", base["size"]), 8, 120, base["size"])
            base["color"] = _valid_hex(incoming.get("color", base["color"]), base["color"])
            base["bold"] = bool(incoming.get("bold", base["bold"]))
        elif base["type"] == "avatar":
            base["size"] = _clampi(incoming.get("size", base["size"]), 32, 320, base["size"])
            base["ring_color"] = _valid_hex(incoming.get("ring_color", base["ring_color"]),
                                            base["ring_color"])
        # Elemen yang punya teks bisa diganti (string non-kosong, dipangkas).
        if "text" in base:
            t = incoming.get("text", base["text"])
            if isinstance(t, str) and t.strip():
                base["text"] = t.strip()[:MAX_TEXT_LEN]
    return theme


def load_theme(kind="welcome") -> dict:
    """Baca tema `kind` dari bot_state (atau default bila belum ada)."""
    kind = _normalize_kind(kind)
    return merge_theme(_base.read_state(THEME_KEYS[kind]), kind)


def save_theme(raw, kind="welcome") -> dict:
    """Validasi + simpan tema `kind` ke bot_state. Mengembalikan tema final."""
    kind = _normalize_kind(kind)
    theme = merge_theme(raw, kind)
    _base.write_state(THEME_KEYS[kind], theme)
    return theme
