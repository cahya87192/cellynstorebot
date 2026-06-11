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

# Ukuran kanvas per jenis (banner lebar; ukuran standar welcome-card).
CANVAS = {
    "welcome": (1024, 450),
    "boost": (1024, 450),
    "leave": (1024, 450),
}

# Ukuran kanvas LAMA (sebelum diperbesar). Koordinat default & tema tersimpan
# yang dibuat pada ukuran ini akan diskalakan proporsional ke CANVAS saat ini
# (lihat _build_default & migrasi di merge_theme), supaya layout tidak melenceng.
_LEGACY_CANVAS = (1000, 360)

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


def _scale_factors(raw, cw, ch):
    """Faktor skala (sx, sy) dari kanvas tema tersimpan ke kanvas (cw, ch) saat ini.

    Penanda `canvas` di tema dipakai untuk deteksi. Tema lama tanpa penanda
    dianggap dibuat pada `_LEGACY_CANVAS`. Kembalikan (1.0, 1.0) bila sama/tak perlu.
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


def _build_default(kind) -> dict:
    """Susun DEFAULT_THEME untuk `kind`.

    Koordinat & ukuran elemen ditulis relatif ke `_LEGACY_CANVAS` lalu diskalakan
    proporsional ke CANVAS[kind] saat ini, sehingga komposisi default identik
    walau ukuran kanvas berubah.
    """
    kind = _normalize_kind(kind)
    d = _KIND_DEFAULTS[kind]
    ring = RING_DEFAULTS[kind]
    theme = {
        "enabled": False,            # False = tetap pakai embed klasik (perilaku lama)
        "panel_opacity": 140,        # 0-255, panel gelap di atas background
        "font_file": None,           # nama file font di data/ (None = font default)
        "canvas": list(CANVAS[kind]),  # penanda ukuran kanvas tema ini dibuat
        "elements": {
            "avatar":      {"type": "avatar", "x": 70,  "y": 95,  "size": 170, "show": True, "ring_color": ring},
            "title":       {"type": "text",   "x": 290, "y": 78,  "size": 30, "color": d["title_color"],    "bold": True,  "show": True, "text": d["title"]},
            "name":        {"type": "text",   "x": 290, "y": 128, "size": 46, "color": d["name_color"],     "bold": True,  "show": True},
            "subtitle":    {"type": "text",   "x": 290, "y": 200, "size": 24, "color": d["subtitle_color"], "bold": False, "show": True, "text": d["subtitle"]},
            "membercount": {"type": "text",   "x": 290, "y": 248, "size": 22, "color": d["count_color"],    "bold": False, "show": True},
        },
    }
    cw, ch = CANVAS[kind]
    lw, lh = _LEGACY_CANVAS
    if (cw, ch) != (lw, lh):
        _base.rescale_elements(theme["elements"], cw / lw, ch / lh)
    return theme


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

    # Bila tema dibuat untuk kanvas berukuran lain, skalakan koordinat/ukuran
    # elemen yang masuk agar layout tetap proporsional di kanvas saat ini.
    sx, sy = _scale_factors(raw, cw, ch)

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
            base["x"] = _clampi(_smul(incoming["x"], sx), 0, cw, base["x"])
        if "y" in incoming:
            base["y"] = _clampi(_smul(incoming["y"], sy), 0, ch, base["y"])
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
