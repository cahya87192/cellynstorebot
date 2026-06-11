"""Render identitas member/admin (avatar template + nama) untuk panel admin.

Panel admin (Flask) tidak punya akses gateway Discord, jadi TIDAK ada URL foto
profil asli — yang tersedia hanya cache nama (utils.member_names). Karena itu
avatar di sini berupa "template":

  - lingkaran inisial berwarna (warna deterministik dari id/nama) bila nama
    diketahui, atau
  - ikon siluet generik bila nama belum ada di cache.

Identitas ditampilkan sebagai avatar + nama saja (tanpa embel-embel id). Bila
nama belum diketahui, id mentah dipakai sebagai fallback karena itu satu-satunya
pengenal yang ada.

Murni (tanpa Flask/DB) -> gampang diuji.
"""
import html

# Palet warna kalem untuk latar avatar inisial (dipilih deterministik per id).
AVATAR_COLORS = (
    "#5a6dc4", "#5fa886", "#c46d6d", "#c4a85a", "#7c5cbf",
    "#4da3bb", "#bb6db0", "#6d9bc4", "#b08a4d", "#5cb37c",
)

# SVG siluet untuk member tanpa nama (foto profil template default).
_SILHOUETTE = (
    "<svg viewBox='0 0 24 24' fill='currentColor' aria-hidden='true' "
    "style='width:100%;height:100%;'>"
    "<circle cx='12' cy='8' r='4'/>"
    "<path d='M4 21v-1c0-3.3 3.6-5 8-5s8 1.7 8 5v1z'/></svg>"
)


def initial(name):
    """Huruf pertama nama (uppercase). Fallback '?' bila kosong."""
    s = (name or "").strip()
    return s[0].upper() if s else "?"


def color_for(seed):
    """Warna latar avatar yang deterministik dari `seed` (id/nama).

    Hash sederhana & stabil supaya member yang sama selalu dapat warna sama.
    """
    s = str(seed if seed is not None else "")
    if not s:
        return AVATAR_COLORS[0]
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return AVATAR_COLORS[h % len(AVATAR_COLORS)]


def avatar_html(name=None, uid=None, size=26):
    """HTML avatar template berbentuk lingkaran.

    - Ada `name` -> inisial di atas latar berwarna (deterministik dari uid/nama).
    - Tanpa `name` -> ikon siluet generik di atas latar netral.

    `size` dalam piksel.
    """
    px = int(size)
    base = (
        f"display:inline-flex;align-items:center;justify-content:center;"
        f"width:{px}px;height:{px}px;border-radius:50%;flex:0 0 auto;"
        f"font-weight:700;color:#fff;overflow:hidden;line-height:1;"
        f"font-size:{max(10, px // 2)}px;"
    )
    if name:
        color = color_for(uid if uid is not None else name)
        return (
            f"<span class='av' style='{base}background:{color};' "
            f"title='{html.escape(str(name))}'>{html.escape(initial(name))}</span>"
        )
    inner = int(px * 0.6)
    return (
        f"<span class='av av-empty' style='{base}background:var(--surface2);"
        f"color:var(--muted);'>"
        f"<span style='width:{inner}px;height:{inner}px;display:inline-flex;'>"
        f"{_SILHOUETTE}</span></span>"
    )


def identity_html(uid, name=None, size=26):
    """Sel identitas untuk tabel panel: avatar template + nama (TANPA id).

    - `name` ada    -> avatar inisial + nama.
    - tanpa `name`  -> avatar siluet + id mentah (satu-satunya pengenal).
    - uid & name kosong -> '-'.
    """
    if not uid and not name:
        return "-"
    av = avatar_html(name=name, uid=uid, size=size)
    if name:
        label = html.escape(str(name))
    else:
        label = f"<code>{html.escape(str(uid))}</code>"
    return (
        f"<span class='idcell' style='display:inline-flex;align-items:center;"
        f"gap:.5rem;'>{av}<span>{label}</span></span>"
    )
