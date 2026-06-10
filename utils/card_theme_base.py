"""Helper bersama untuk semua modul tema kartu (logika murni, tanpa PIL/discord).

Modul tema kartu — welcome_theme (welcome/boost/leave), rating_theme,
profile_theme, achievement_theme — sebelumnya menyalin fungsi util yang sama
persis (clamp integer, validasi hex, konversi hex->rgb, validasi warna ring
otomatis, serta boilerplate baca/tulis bot_state). Duplikasi itu dipusatkan di
sini agar perbaikan/validasi konsisten di seluruh sistem kartu.

Tiap modul tema tetap memegang DEFAULT_THEME, skema elemen, dan logika
merge-nya sendiri (karena berbeda antar kartu), namun memanggil helper umum
dari sini. Untuk kompatibilitas, modul mempertahankan alias lokal (mis.
`_valid_hex`, `hex_to_rgb`) yang menunjuk ke fungsi di modul ini.
"""

import json

from utils.db import get_conn


def clampi(v, lo, hi, default):
    """Paksa `v` jadi integer dalam rentang [lo, hi]; fallback `default`."""
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def valid_hex(c, default):
    """Validasi warna hex '#RGB'/'#RRGGBB' -> '#RRGGBB' uppercase, else default."""
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
    s = valid_hex(c, "#FFFFFF")[1:]
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def ring_color_auto(c, default):
    """Validasi warna bingkai (ring) avatar yang mendukung mode "otomatis".

    None/""/invalid -> None artinya "otomatis" (render memakai warna aksen
    tier). String hex valid -> '#RRGGBB' (uppercase) untuk override warna ring.
    Dipakai kartu Profil & Badge (warna ring default mengikuti tier).
    """
    if c is None:
        return None
    if isinstance(c, str) and not c.strip():
        return None
    return valid_hex(c, default)


def read_state(key):
    """Baca nilai mentah (string JSON) dari bot_state untuk `key`, atau None."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
    except Exception:
        row = None
    conn.close()
    return row["value"] if row else None


def write_state(key, theme):
    """Simpan dict `theme` sebagai JSON ke bot_state untuk `key`."""
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
        (key, json.dumps(theme)),
    )
    conn.commit()
    conn.close()
