"""Pengaturan katalog (thumbnail per katalog) — logika murni, tanpa discord/PIL.

Menyimpan URL thumbnail/gambar kecil untuk tiap embed katalog produk
(robux, ml, gp, vilog, lainnya) sehingga bisa diatur admin lewat panel.
Data disimpan sebagai JSON di tabel `bot_state` (key `catalog_thumbnails`),
dibagikan antara bot (discord) & admin panel (Flask).

Catatan: katalog "ml" adalah embed gabungan "Topup Diamond Game" yang juga
mencakup Free Fire (FF) & WDP — ketiganya satu embed, jadi memakai key "ml".

Fungsi inti dibuat murni (tanpa I/O) agar mudah diuji: is_valid_url,
clean_url, merge_settings, resolve_thumbnail. load/save menyentuh DB.
"""
import json

from utils.db import get_conn

THUMB_KEY = "catalog_thumbnails"

# Thumbnail default (logo toko de-facto yang dipakai berulang di repo).
DEFAULT_THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"

# Registry katalog yang punya embed & bisa diatur thumbnailnya.
# (code, label tampilan di panel)
CATALOGS = [
    ("robux",   "Robux Store"),
    ("ml",      "Topup Diamond Game (ML / FF / WDP)"),
    ("gp",      "Robux via Gamepass"),
    ("vilog",   "Robux via Login (Vilog)"),
    ("lainnya", "Layanan Lainnya"),
]
CATALOG_CODES = {code for code, _ in CATALOGS}

MAX_URL_LEN = 500


def is_valid_url(u) -> bool:
    """True bila string terlihat seperti URL http(s) yang wajar."""
    if not isinstance(u, str):
        return False
    s = u.strip()
    return (
        len(s) <= MAX_URL_LEN
        and (s.startswith("http://") or s.startswith("https://"))
        and " " not in s
        and len(s) > len("https://")
    )


def clean_url(u):
    """Kembalikan URL bersih (string) bila valid, selain itu None."""
    if not isinstance(u, str):
        return None
    s = u.strip()
    return s if is_valid_url(s) else None


def merge_settings(raw) -> dict:
    """Normalisasi data tersimpan -> {code: url}.

    Toleran input None/rusak/sebagian. Hanya code yang dikenal & URL valid
    yang dipertahankan. Selalu mengembalikan dict bersih.
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = None
    out = {}
    if not isinstance(raw, dict):
        return out
    # Dukung bentuk {code:url} maupun {"thumbnails": {code:url}}.
    src = raw.get("thumbnails") if isinstance(raw.get("thumbnails"), dict) else raw
    if not isinstance(src, dict):
        return out
    for code in CATALOG_CODES:
        url = clean_url(src.get(code))
        if url:
            out[code] = url
    return out


def resolve_thumbnail(settings, code) -> str:
    """Ambil URL thumbnail untuk `code` dari dict settings, fallback default."""
    if isinstance(settings, dict):
        url = settings.get(code)
        if isinstance(url, str) and url.strip():
            return url.strip()
    return DEFAULT_THUMBNAIL


def load_settings() -> dict:
    """Baca {code: url} dari bot_state (atau dict kosong)."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT value FROM bot_state WHERE key=?", (THUMB_KEY,)).fetchone()
    except Exception:
        row = None
    conn.close()
    return merge_settings(row["value"] if row else None)


def save_settings(raw) -> dict:
    """Validasi + simpan {code: url} ke bot_state. Mengembalikan dict final."""
    settings = merge_settings(raw)
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
        (THUMB_KEY, json.dumps(settings)),
    )
    conn.commit()
    conn.close()
    return settings


def get_thumbnail(code) -> str:
    """Helper untuk cog: URL thumbnail katalog `code` (fallback default)."""
    return resolve_thumbnail(load_settings(), code)
