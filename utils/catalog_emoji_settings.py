"""Override emoji katalog "lainnya" yang bisa diatur admin (logika murni).

Owner bisa mengganti emoji per GRUP & per KATEGORI lewat admin panel tanpa
mengubah kode. Override disimpan sebagai JSON di tabel `bot_state`
(key `lainnya_emoji_overrides`), dibagikan antara bot & panel.

Alur resolusi emoji (lihat cogs/lainnya.py):
  override DB  ->  map statis (cogs/lainnya_catalog.py)  ->  fallback unicode
                   + flag LAINNYA_USE_CUSTOM_EMOJI (utils/catalog_emoji.py)

Override yang valid berupa:
  - custom emoji Discord  `<:nama:id>` / `<a:nama:id>`, atau
  - emoji unicode (tanpa huruf ASCII / spasi, pendek).

Fungsi inti murni (tanpa I/O) agar mudah diuji.
"""
import json
import re

from utils.db import get_conn

OVERRIDE_KEY = "lainnya_emoji_overrides"

# Bentuk custom emoji Discord.
_CUSTOM_RE = re.compile(r"^<a?:[A-Za-z0-9_]+:\d+>$")
# Huruf ASCII (untuk menolak teks biasa yang bukan emoji).
_ASCII_LETTER_RE = re.compile(r"[A-Za-z]")

MAX_EMOJI_LEN = 64
MAX_UNICODE_LEN = 16


def clean_emoji(value):
    """Kembalikan emoji bersih (string) bila valid, selain itu None.

    Menerima custom emoji Discord atau emoji unicode pendek; menolak string
    kosong, terlalu panjang, mengandung huruf ASCII (teks biasa), atau spasi.
    """
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not v or len(v) > MAX_EMOJI_LEN:
        return None
    if _CUSTOM_RE.match(v):
        return v
    # Anggap emoji unicode: tolak bila ada huruf ASCII / spasi, batasi panjang.
    if _ASCII_LETTER_RE.search(v) or any(c.isspace() for c in v):
        return None
    if len(v) > MAX_UNICODE_LEN:
        return None
    return v


def merge_overrides(raw) -> dict:
    """Normalisasi data tersimpan -> {'groups': {...}, 'categories': {...}}.

    Toleran input None/rusak/sebagian. Hanya nama (key) string non-kosong &
    emoji valid yang dipertahankan. Selalu mengembalikan struktur lengkap.
    """
    out = {"groups": {}, "categories": {}}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = None
    if not isinstance(raw, dict):
        return out
    for section in ("groups", "categories"):
        src = raw.get(section)
        if not isinstance(src, dict):
            continue
        for name, emoji in src.items():
            if not isinstance(name, str) or not name.strip():
                continue
            cleaned = clean_emoji(emoji)
            if cleaned:
                out[section][name.strip()] = cleaned
    return out


def effective_map(static_map, override_map) -> dict:
    """Gabungkan map statis dgn override (override menang). Murni."""
    merged = dict(static_map or {})
    if isinstance(override_map, dict):
        for k, v in override_map.items():
            if v:
                merged[k] = v
    return merged


def load_overrides() -> dict:
    """Baca override dari bot_state (atau struktur kosong)."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM bot_state WHERE key=?", (OVERRIDE_KEY,)
        ).fetchone()
    except Exception:
        row = None
    conn.close()
    return merge_overrides(row["value"] if row else None)


def save_overrides(raw) -> dict:
    """Validasi + simpan override ke bot_state. Mengembalikan struktur final."""
    data = merge_overrides(raw)
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
        (OVERRIDE_KEY, json.dumps(data)),
    )
    conn.commit()
    conn.close()
    return data
