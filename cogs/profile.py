"""Kartu Profil Member (gambar PNG) — /profil.

Render kartu estetik (gradien + avatar bulat + progress bar XP + tier + badge)
pakai Pillow. Logika data & XP murni ada di utils/profile.py (teruji terpisah).

Command:
  - /profil            : lihat kartu profil sendiri
  - /profil member:@x  : (admin) lihat kartu profil member lain
"""

import io
import os
import datetime

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from PIL import Image, ImageDraw, ImageFont

from utils.config import ADMIN_ROLE_ID, STORE_NAME
from utils import profile as profilelib
from utils import profile_theme as themelib
from utils import achievement_theme as achthemelib
from utils import achievements as achlib
from utils import badge_profile_text as bptext

# Background kustom per tier (di-upload admin via /setprofilbg). Disimpan di
# data/profilebg_<tier>.<ext>, mirip gambar welcome/boost.
# Path ABSOLUT ke <repo>/data agar font/background yang di-upload lewat admin
# panel (yang memakai path absolut) SELALU ditemukan bot, terlepas dari working
# directory tempat bot dijalankan (samakan dengan utils/db.py).
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PROFILE_BG_BASE = "profilebg"
# Background kustom kartu badge "Achievement Unlocked" (di-upload admin via
# /setbadgebg). Disimpan di data/badgebg_<tier>.<ext>.
BADGE_BG_BASE = "badgebg"
ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
VALID_TIERS = ["Bronze", "Silver", "Gold", "Diamond"]


def _bg_path_for(tier: str):
    """Path background kustom untuk tier (atau None bila belum di-set)."""
    base = f"{PROFILE_BG_BASE}_{(tier or '').lower()}"
    for ext in ALLOWED_IMAGE_EXTS:
        path = os.path.join(DATA_DIR, base + ext)
        if os.path.exists(path):
            return path
    return None

try:
    from cogs.top_spender import get_top_spenders, TOP_SPENDER_TOP_N
except Exception:  # pragma: no cover
    get_top_spenders = None
    TOP_SPENDER_TOP_N = 10

# Ukuran kartu.
W, H = 900, 360

# Palet per tier (warna gradien latar).
TIER_THEME = {
    "Bronze":  ((58, 38, 24), (120, 78, 40), (214, 154, 92)),
    "Silver":  ((40, 46, 58), (96, 110, 130), (200, 214, 232)),
    "Gold":    ((58, 47, 18), (140, 108, 30), (240, 200, 90)),
    "Diamond": ((24, 48, 58), (38, 110, 132), (130, 224, 240)),
}


def _rupiah(n) -> str:
    try:
        return "Rp " + f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp 0"


# Font yang DIBUNDEL bersama repo (selalu ada di host mana pun, termasuk Termux/
# Android yang tak punya font sistem). Inilah perbaikan utama "teks jadi kotak".
BUNDLED_FONT = os.path.join(DATA_DIR, "_card_font.ttf")


def _font(size, bold=False, font_file=None):
    """Font untuk kartu. Prioritas:
      1) font kustom upload admin (data/<font_file>),
      2) font bawaan repo (data/_card_font.ttf) — selalu tersedia,
      3) font sistem umum (Debian/Termux),
      4) default Pillow (last resort).
    """
    if font_file:
        custom = os.path.join(DATA_DIR, font_file)
        if os.path.exists(custom):
            try:
                return ImageFont.truetype(custom, size)
            except Exception:
                pass
    candidates = [
        BUNDLED_FONT,
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans%s.ttf" % ("Bold" if bold else ""),
        "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf",
        # Termux / Android umum:
        "/system/fonts/Roboto-Regular.ttf",
        "/system/fonts/DroidSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _lerp(a, b, t):
    return int(a + (b - a) * t)


def _gradient(c1, c2):
    """Buat latar gradien diagonal halus W×H."""
    base = Image.new("RGB", (W, H), c1)
    top = Image.new("RGB", (W, H), c2)
    mask = Image.new("L", (W, H))
    md = mask.load()
    for y in range(H):
        for x in range(0, W, 4):  # langkah 4px biar cepat
            t = (x / W * 0.6 + y / H * 0.4)
            v = int(max(0, min(255, t * 255)))
            for dx in range(4):
                if x + dx < W:
                    md[x + dx, y] = v
    base.paste(top, (0, 0), mask)
    return base


def _circle_avatar(img: Image.Image, size: int) -> Image.Image:
    img = img.convert("RGBA").resize((size, size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def _rounded(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def render_profile_card(name: str, avatar_bytes, data: dict, *,
                        rank=None, badges=None, bg_path=None, theme=None) -> io.BytesIO:
    """Render kartu profil -> PNG BytesIO. Murni Pillow (dipanggil di executor).

    `bg_path`: background kustom per tier (cover-fit 900×360); bila None pakai
    gradien tema tier. `theme`: dict tema (utils.profile_theme) untuk posisi,
    warna, ukuran font, visibilitas, opacity panel, & font kustom.
    """
    tier = data.get("tier", "Bronze")
    dark, mid, accent = TIER_THEME.get(tier, TIER_THEME["Bronze"])
    theme = themelib.merge_theme(theme)
    el = theme["elements"]
    font_file = theme.get("font_file")

    def fnt(size, bold=False):
        return _font(size, bold=bold, font_file=font_file)

    bg = None
    if bg_path:
        try:
            src = Image.open(bg_path).convert("RGBA")
            sw, sh = src.size
            scale = max(W / sw, H / sh)
            nw, nh = int(sw * scale), int(sh * scale)
            src = src.resize((nw, nh))
            left, top = (nw - W) // 2, (nh - H) // 2
            bg = src.crop((left, top, left + W, top + H))
        except Exception:
            bg = None
    if bg is None:
        bg = _gradient(dark, mid).convert("RGBA")
    card = bg

    # Panel kaca semi-transparan (opacity bisa diatur tema).
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    _rounded(pd, (24, 24, W - 24, H - 24), 28, (0, 0, 0, int(theme["panel_opacity"])))
    card = Image.alpha_composite(card, panel)
    d = ImageDraw.Draw(card)

    def rgb(key, fallback):
        try:
            return themelib.hex_to_rgb(el[key]["color"])
        except Exception:
            return fallback

    # Avatar bulat + ring aksen.
    av = el["avatar"]
    if av.get("show", True):
        av_size = int(av["size"])
        ax, ay = int(av["x"]), int(av["y"])
        d.ellipse((ax - 6, ay - 6, ax + av_size + 6, ay + av_size + 6), fill=accent + (255,))
        if avatar_bytes:
            try:
                im = Image.open(io.BytesIO(avatar_bytes))
                circ = _circle_avatar(im, av_size)
                card.paste(circ, (ax, ay), circ)
            except Exception:
                d.ellipse((ax, ay, ax + av_size, ay + av_size), fill=(60, 60, 70, 255))
        else:
            d.ellipse((ax, ay, ax + av_size, ay + av_size), fill=(60, 60, 70, 255))

    # Nama.
    if el["name"].get("show", True):
        e = el["name"]
        d.text((e["x"], e["y"]), name[:22], font=fnt(e["size"], e.get("bold", True)),
               fill=rgb("name", (255, 255, 255)))

    # Tier & level.
    if el["tier"].get("show", True):
        e = el["tier"]
        d.text((e["x"], e["y"]), f"{tier.upper()} · Level {data['level']}",
               font=fnt(e["size"], e.get("bold", True)), fill=rgb("tier", accent))

    # Member sejak (+ peringkat).
    if el["since"].get("show", True):
        e = el["since"]
        since = "-"
        if data.get("first_order"):
            try:
                since = datetime.datetime.fromisoformat(str(data["first_order"])).strftime("%b %Y")
            except Exception:
                since = "-"
        rank_txt = f"  ·  Peringkat #{rank} bulan ini" if rank else ""
        d.text((e["x"], e["y"]), f"Member sejak {since}{rank_txt}",
               font=fnt(e["size"], e.get("bold", False)), fill=rgb("since", (220, 220, 230)))

    # Progress bar XP.
    if el["xpbar"].get("show", True):
        e = el["xpbar"]
        bx, by, bw, bh = int(e["x"]), int(e["y"]), int(e["w"]), int(e["h"])
        _rounded(d, (bx, by, bx + bw, by + bh), bh // 2, (255, 255, 255, 55))
        into = data.get("xp_into_level", 0)
        need = max(1, data.get("xp_for_next", 1))
        frac = max(0.0, min(1.0, into / need))
        fillw = int(bw * frac)
        if fillw > bh:
            _rounded(d, (bx, by, bx + fillw, by + bh), bh // 2, rgb("xpbar", accent) + (255,))

    # Teks XP.
    if el["xptext"].get("show", True):
        e = el["xptext"]
        into = data.get("xp_into_level", 0)
        need = max(1, data.get("xp_for_next", 1))
        d.text((e["x"], e["y"]),
               f"XP {into}/{need}  ·  {data.get('xp_remaining', 0)} XP lagi ke "
               f"{data.get('next_tier') or 'MAX'}",
               font=fnt(e["size"], e.get("bold", False)), fill=rgb("xptext", (225, 225, 235)))

    # Statistik (3 kolom).
    if el["stats"].get("show", True):
        e = el["stats"]
        stats = [
            ("BELANJA BULAN INI", _rupiah(data.get("spent_month", 0))),
            ("TOTAL ORDER", f"{data.get('total_orders', 0)}x"),
            ("ULASAN", f"{data.get('total_reviews', 0)}"),
        ]
        sx, sy = int(e["x"]), int(e["y"])
        col_w = (W - sx - 60) // 3
        label_sz = max(10, int(e["size"]) - 12)
        for i, (label, val) in enumerate(stats):
            # Center label & nilai di tengah masing-masing kolom (anchor "ma").
            cx = sx + i * col_w + col_w // 2
            d.text((cx, sy), label, font=fnt(label_sz, True),
                   fill=(200, 200, 215), anchor="ma")
            d.text((cx, sy + label_sz + 6), val, font=fnt(e["size"], e.get("bold", True)),
                   fill=rgb("stats", (255, 255, 255)), anchor="ma")

    # Badge (teks polos dipisah bullet, tanpa emoji warna).
    if el["badges"].get("show", True) and badges:
        e = el["badges"]
        d.text((e["x"], e["y"]), "  •  ".join(badges),
               font=fnt(e["size"], e.get("bold", True)), fill=rgb("badges", accent))

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf


# Ukuran kartu notifikasi achievement (banner, lebih pendek dari kartu profil).
ACH_W, ACH_H = 880, 300


def _badge_bg_path_for(tier: str):
    """Path background kustom kartu badge untuk tier (atau None). Pola sama
    dengan /setprofilbg: data/badgebg_<tier>.<ext>."""
    base = f"{BADGE_BG_BASE}_{(tier or '').lower()}"
    for ext in ALLOWED_IMAGE_EXTS:
        path = os.path.join(DATA_DIR, base + ext)
        if os.path.exists(path):
            return path
    return None


def _badge_icon_path():
    """Path ikon/thumbnail kartu badge (atau None). Di-upload via panel:
    data/badge_icon.<ext>. Satu ikon global (bukan per tier)."""
    for ext in ALLOWED_IMAGE_EXTS:
        path = os.path.join(DATA_DIR, "badge_icon" + ext)
        if os.path.exists(path):
            return path
    return None


def render_achievement_card(name: str, avatar_bytes, badge_names, tier: str = "Bronze",
                            *, theme=None, bg_path=None, icon_path=None) -> io.BytesIO:
    """Render kartu 'Achievement Unlocked' -> PNG BytesIO. Murni Pillow.

    Dipakai notifikasi badge baru (cogs/reviews.py). Posisi, warna, ukuran font,
    teks judul, visibilitas, opacity panel & font kustom diambil dari `theme`
    (utils.achievement_theme). `bg_path` = background kustom per tier (cover-fit
    ACH_W×ACH_H); bila None pakai gradien tema tier. `icon_path` = gambar
    ikon/thumbnail dekoratif (elemen 'icon', sisi kanan); bila None elemen ikon
    tidak digambar. Teks polos (font bundel tak render emoji warna).
    """
    dark, mid, accent = TIER_THEME.get(tier, TIER_THEME["Bronze"])
    badge_names = [str(b) for b in (badge_names or []) if str(b)][:4]

    theme = achthemelib.merge_theme(theme)
    el = theme["elements"]
    font_file = theme.get("font_file")

    def fnt(size, bold=False):
        return _font(size, bold=bold, font_file=font_file)

    def rgb(key, fallback):
        try:
            return achthemelib.hex_to_rgb(el[key]["color"])
        except Exception:
            return fallback

    bg = None
    if bg_path:
        try:
            src = Image.open(bg_path).convert("RGBA")
            sw, sh = src.size
            scale = max(ACH_W / sw, ACH_H / sh)
            nw, nh = int(sw * scale), int(sh * scale)
            src = src.resize((nw, nh))
            left, top = (nw - ACH_W) // 2, (nh - ACH_H) // 2
            bg = src.crop((left, top, left + ACH_W, top + ACH_H))
        except Exception:
            bg = None
    if bg is None:
        bg = _gradient(dark, mid).resize((ACH_W, ACH_H)).convert("RGBA")
    card = bg

    panel = Image.new("RGBA", (ACH_W, ACH_H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    _rounded(pd, (20, 20, ACH_W - 20, ACH_H - 20), 26, (0, 0, 0, int(theme["panel_opacity"])))
    card = Image.alpha_composite(card, panel)
    d = ImageDraw.Draw(card)

    # Avatar bulat + ring aksen.
    av = el["avatar"]
    if av.get("show", True):
        av_size = int(av["size"])
        ax, ay = int(av["x"]), int(av["y"])
        d.ellipse((ax - 6, ay - 6, ax + av_size + 6, ay + av_size + 6), fill=accent + (255,))
        if avatar_bytes:
            try:
                im = Image.open(io.BytesIO(avatar_bytes))
                circ = _circle_avatar(im, av_size)
                card.paste(circ, (ax, ay), circ)
            except Exception:
                d.ellipse((ax, ay, ax + av_size, ay + av_size), fill=(60, 60, 70, 255))
        else:
            d.ellipse((ax, ay, ax + av_size, ay + av_size), fill=(60, 60, 70, 255))

    # Judul (teks bisa diganti).
    if el["title"].get("show", True):
        e = el["title"]
        d.text((e["x"], e["y"]), str(e.get("text") or "ACHIEVEMENT UNLOCKED"),
               font=fnt(e["size"], e.get("bold", True)), fill=rgb("title", accent))

    # Nama member.
    if el["name"].get("show", True):
        e = el["name"]
        d.text((e["x"], e["y"]), name[:24], font=fnt(e["size"], e.get("bold", True)),
               fill=rgb("name", (255, 255, 255)))

    # Daftar badge (header "Badge baru:" + tiap badge sebagai bullet).
    if el["badges"].get("show", True):
        e = el["badges"]
        bx, by = int(e["x"]), int(e["y"])
        label_sz = max(12, int(e["size"]) - 4)
        d.text((bx, by), "Badge baru:", font=fnt(label_sz, False), fill=(210, 210, 220))
        by += label_sz + 8
        for bn in badge_names:
            d.text((bx, by), f"\u2022  {bn}", font=fnt(e["size"], e.get("bold", True)),
                   fill=rgb("badges", (255, 255, 255)))
            by += int(e["size"]) + 8

    # Ikon/thumbnail dekoratif (sisi kanan). Hanya digambar bila gambar tersedia.
    ic = el.get("icon")
    if ic and ic.get("show", True) and icon_path:
        try:
            isz = int(ic["size"])
            ix, iy = int(ic["x"]), int(ic["y"])
            src = Image.open(icon_path).convert("RGBA")
            # contain-fit ke kotak isz x isz (jaga rasio, tengah).
            src.thumbnail((isz, isz))
            iw, ih = src.size
            ox, oy = ix + (isz - iw) // 2, iy + (isz - ih) // 2
            # masker sudut membulat agar rapi.
            mask = Image.new("L", (iw, ih), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, iw, ih), radius=max(8, isz // 8), fill=255)
            card.paste(src, (ox, oy), mask)
        except Exception:
            pass

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf



RATING_BG_BASE = "ratingcardbg"


def _rating_bg_path():
    """Path background kartu testimoni/rating (atau None). Di-upload via panel:
    data/ratingcardbg.<ext>. Satu background global."""
    for ext in ALLOWED_IMAGE_EXTS:
        path = os.path.join(DATA_DIR, RATING_BG_BASE + ext)
        if os.path.exists(path):
            return path
    return None


def _wrap_text(draw, text, font, max_w, max_lines):
    """Bungkus `text` jadi beberapa baris yang muat di lebar `max_w` (piksel).

    Memotong ke `max_lines` baris; baris terakhir diberi elipsis bila masih ada
    sisa. Murni Pillow (pakai draw.textlength)."""
    words = str(text).split()
    if not words:
        return []

    def width(s):
        try:
            return draw.textlength(s, font=font)
        except Exception:
            return len(s) * (font.size * 0.5 if hasattr(font, "size") else 8)

    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if width(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
            if len(lines) >= max_lines:
                break
    if len(lines) < max_lines and cur:
        lines.append(cur)

    # Bila masih ada kata tersisa (terpotong), tambahkan elipsis ke baris akhir.
    used = sum(len(l.split()) for l in lines)
    if used < len(words) and lines:
        last = lines[-1]
        while last and width(last + "\u2026") > max_w:
            parts = last.rsplit(" ", 1)
            if len(parts) == 1:
                last = last[:-1]
            else:
                last = parts[0]
        lines[-1] = (last + "\u2026").strip()
    return lines


def render_rating_card(name: str, avatar_bytes, *, stars: str, review=None,
                       theme=None, bg_path=None) -> io.BytesIO:
    """Render kartu testimoni/ulasan pelanggan -> PNG BytesIO. Murni Pillow.

    Dipakai cogs/reviews.publish_review saat kartu rating diaktifkan di panel.
    Elemen: foto profil (ring warna bisa diatur), judul, nama, bintang, dan
    teks ulasan (dibungkus multi-baris). TANPA nama layanan. Posisi/warna/ukuran
    font/visibilitas/opacity/font kustom dari `theme` (utils.rating_theme).
    `bg_path` = background kustom (cover-fit RATING_W×RATING_H); None = gradien
    default. Teks polos (font bundel tak render emoji warna).
    """
    from utils import rating_theme as ratingthemelib
    W, H = ratingthemelib.RATING_W, ratingthemelib.RATING_H

    theme = ratingthemelib.merge_theme(theme)
    el = theme["elements"]
    font_file = theme.get("font_file")

    def fnt(size, bold=False):
        return _font(size, bold=bold, font_file=font_file)

    def rgb(key, fallback):
        try:
            return ratingthemelib.hex_to_rgb(el[key]["color"])
        except Exception:
            return fallback

    bg = None
    if bg_path:
        try:
            src = Image.open(bg_path).convert("RGBA")
            sw, sh = src.size
            scale = max(W / sw, H / sh)
            nw, nh = int(sw * scale), int(sh * scale)
            src = src.resize((nw, nh))
            left, top = (nw - W) // 2, (nh - H) // 2
            bg = src.crop((left, top, left + W, top + H))
        except Exception:
            bg = None
    if bg is None:
        bg = _gradient((28, 28, 40), (74, 60, 30)).resize((W, H)).convert("RGBA")
    card = bg

    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    _rounded(pd, (20, 20, W - 20, H - 20), 26, (0, 0, 0, int(theme["panel_opacity"])))
    card = Image.alpha_composite(card, panel)
    d = ImageDraw.Draw(card)

    # Avatar bulat + ring (warna bisa diatur).
    av = el["avatar"]
    if av.get("show", True):
        ring = ratingthemelib.hex_to_rgb(av.get("ring_color") or ratingthemelib.RING_DEFAULT)
        av_size = int(av["size"])
        ax, ay = int(av["x"]), int(av["y"])
        d.ellipse((ax - 6, ay - 6, ax + av_size + 6, ay + av_size + 6), fill=ring + (255,))
        if avatar_bytes:
            try:
                im = Image.open(io.BytesIO(avatar_bytes))
                circ = _circle_avatar(im, av_size)
                card.paste(circ, (ax, ay), circ)
            except Exception:
                d.ellipse((ax, ay, ax + av_size, ay + av_size), fill=(60, 60, 70, 255))
        else:
            d.ellipse((ax, ay, ax + av_size, ay + av_size), fill=(60, 60, 70, 255))

    # Judul (teks bisa diganti).
    if el["title"].get("show", True):
        e = el["title"]
        d.text((e["x"], e["y"]), str(e.get("text") or ratingthemelib.DEFAULT_TITLE),
               font=fnt(e["size"], e.get("bold", True)), fill=rgb("title", (255, 193, 7)))

    # Nama pelanggan (dinamis).
    if el["name"].get("show", True):
        e = el["name"]
        d.text((e["x"], e["y"]), (name or "Pelanggan")[:24],
               font=fnt(e["size"], e.get("bold", True)), fill=rgb("name", (255, 255, 255)))

    # Bintang rating (dinamis).
    if el["stars"].get("show", True) and stars:
        e = el["stars"]
        d.text((e["x"], e["y"]), str(stars),
               font=fnt(e["size"], e.get("bold", True)), fill=rgb("stars", (255, 210, 77)))

    # Teks ulasan (dinamis, dibungkus multi-baris). Dilewati bila kosong.
    if el["review"].get("show", True) and review:
        e = el["review"]
        rx, ry = int(e["x"]), int(e["y"])
        size = int(e["size"])
        review_font = fnt(size, e.get("bold", False))
        max_w = max(80, W - rx - 40)
        lines = _wrap_text(d, review, review_font, max_w, max_lines=3)
        line_h = size + 8
        for i, line in enumerate(lines):
            d.text((rx, ry + i * line_h), line, font=review_font,
                   fill=rgb("review", (226, 228, 236)))

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf


# Gradien latar default per jenis kartu notifikasi (dipakai bila tak ada
# background kustom). Senada dengan warna ring/aksen tiap jenis.
NOTIFY_GRADIENTS = {
    "welcome": ((26, 29, 44), (52, 44, 88)),
    "boost":   ((44, 26, 52), (96, 40, 90)),
    "leave":   ((30, 32, 40), (58, 62, 74)),
}


def render_notify_card(kind: str, avatar_bytes, *, values=None,
                       theme=None, bg_path=None) -> io.BytesIO:
    """Render kartu notifikasi member (welcome/boost/leave) -> PNG BytesIO.

    Murni Pillow (dipanggil di executor). Satu fungsi generik untuk ketiga
    jenis kartu yang strukturnya identik (lihat utils.welcome_theme).

    `kind`        : "welcome" | "boost" | "leave".
    `values`      : dict nilai elemen dinamis, mis. {"name": "...",
                    "membercount": "Member #12"}. Elemen teks dinamis yang
                    tidak ada/None di `values` tidak digambar.
    `theme`       : dict tema (utils.welcome_theme) untuk jenis ini.
    `bg_path`     : background kustom (cover-fit kanvas); None = gradien default.

    Teks polos (font bundel tak render emoji warna).
    """
    from utils import welcome_theme as wtheme
    kind = kind if kind in wtheme.KINDS else "welcome"
    W, H = wtheme.CANVAS[kind]
    values = values or {}

    theme = wtheme.merge_theme(theme, kind)
    el = theme["elements"]
    font_file = theme.get("font_file")

    def fnt(size, bold=False):
        return _font(size, bold=bold, font_file=font_file)

    def rgb(key, fallback):
        try:
            return wtheme.hex_to_rgb(el[key]["color"])
        except Exception:
            return fallback

    bg = None
    if bg_path:
        try:
            src = Image.open(bg_path).convert("RGBA")
            sw, sh = src.size
            scale = max(W / sw, H / sh)
            nw, nh = int(sw * scale), int(sh * scale)
            src = src.resize((nw, nh))
            left, top = (nw - W) // 2, (nh - H) // 2
            bg = src.crop((left, top, left + W, top + H))
        except Exception:
            bg = None
    if bg is None:
        g1, g2 = NOTIFY_GRADIENTS.get(kind, NOTIFY_GRADIENTS["welcome"])
        bg = _gradient(g1, g2).resize((W, H)).convert("RGBA")
    card = bg

    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    _rounded(pd, (20, 20, W - 20, H - 20), 28, (0, 0, 0, int(theme["panel_opacity"])))
    card = Image.alpha_composite(card, panel)
    d = ImageDraw.Draw(card)

    for key in wtheme.ELEMENT_ORDER:
        e = el.get(key)
        if not e or not e.get("show", True):
            continue

        if e.get("type") == "avatar":
            # Avatar bulat + ring (warna bisa diatur per kartu).
            ring = wtheme.hex_to_rgb(e.get("ring_color")
                                     or wtheme.RING_DEFAULTS.get(kind, "#8B9BE0"))
            av_size = int(e["size"])
            ax, ay = int(e["x"]), int(e["y"])
            d.ellipse((ax - 6, ay - 6, ax + av_size + 6, ay + av_size + 6), fill=ring + (255,))
            if avatar_bytes:
                try:
                    im = Image.open(io.BytesIO(avatar_bytes))
                    circ = _circle_avatar(im, av_size)
                    card.paste(circ, (ax, ay), circ)
                except Exception:
                    d.ellipse((ax, ay, ax + av_size, ay + av_size), fill=(60, 60, 70, 255))
            else:
                d.ellipse((ax, ay, ax + av_size, ay + av_size), fill=(60, 60, 70, 255))
            continue

        # Elemen teks. Statis (title/subtitle) pakai e["text"]; dinamis
        # (name/membercount) pakai values[key] — bila tak ada, dilewati.
        if key in values:
            val = values.get(key)
            if val is None or str(val) == "":
                continue
            txt = str(val)
        elif "text" in e:
            txt = str(e.get("text") or "")
        else:
            # Elemen dinamis tanpa nilai -> tidak digambar.
            continue
        d.text((e["x"], e["y"]), txt,
               font=fnt(e["size"], e.get("bold", False)),
               fill=rgb(key, (255, 255, 255)))

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf


def render_welcome_card(name: str, avatar_bytes, *, member_count=None,
                        theme=None, bg_path=None) -> io.BytesIO:
    """Wrapper kompatibilitas: render kartu sambutan welcome.

    Sekarang delegasi ke render_notify_card("welcome", ...). Dipakai
    cogs/welcome.py & editor preview. `member_count` (bila ada) jadi teks
    "Member #N" pada elemen membercount.
    """
    values = {"name": (name or "Member")[:24]}
    if member_count is not None:
        values["membercount"] = f"Member #{member_count}"
    return render_notify_card("welcome", avatar_bytes, values=values,
                              theme=theme, bg_path=bg_path)


def _is_admin(member) -> bool:
    return any(r.id == ADMIN_ROLE_ID for r in getattr(member, "roles", []))


def _compute_badges(data: dict, rank, is_priority: bool) -> list:
    # Catatan: Pillow tidak bisa render emoji berwarna (jadi kotak-kotak), jadi
    # badge pakai teks polos + bullet sederhana yang didukung font biasa.
    #
    # Sumber tunggal badge = utils.achievements (sama dgn command /badges), supaya
    # konsisten. Badge tier akun (Member Gold/Diamond) di-skip di kartu karena
    # tier sudah tampil sebagai "GOLD · Level X". "Top Spender" tetap dari rank
    # bulan ini (bukan bagian achievements). Dibatasi agar muat di kartu.
    badges = []
    if is_priority or rank:
        badges.append("Top Spender")
    for b in achlib.compute_achievements(data)["earned"]:
        if b["category"] == "tier":
            continue
        badges.append(b["name"])
    return badges[:4]


class MemberProfile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _fetch_avatar(self, member) -> bytes | None:
        try:
            url = member.display_avatar.replace(size=256).url
        except Exception:
            return None
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url) as r:
                    if r.status == 200:
                        return await r.read()
        except Exception:
            return None
        return None

    def _rank_of(self, user_id: int):
        """Peringkat Top Spender bulan ini (1-based) atau None."""
        if get_top_spenders is None:
            return None, False
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            top = get_top_spenders(now.year, now.month, TOP_SPENDER_TOP_N)
            for i, s in enumerate(top, 1):
                if s.get("user_id") == user_id:
                    return i, True
        except Exception:
            pass
        return None, False

    @app_commands.command(name="profil",
                          description="Lihat kartu profil member (statistik, level, badge)")
    @app_commands.describe(member="(Admin) lihat profil member lain")
    async def profil(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        # Hanya admin yang boleh melihat profil member lain.
        if member is not None and member.id != interaction.user.id and not _is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Kamu hanya bisa melihat profilmu sendiri.", ephemeral=True)
            return

        await interaction.response.defer()
        data = profilelib.get_member_profile(target.id)
        rank, is_priority = self._rank_of(target.id)
        badges = _compute_badges(data, rank, is_priority)
        avatar = await self._fetch_avatar(target)
        name = target.display_name
        bg_path = _bg_path_for(data.get("tier"))
        theme = themelib.load_theme()

        try:
            buf = await self.bot.loop.run_in_executor(
                None, lambda: render_profile_card(name, avatar, data, rank=rank,
                                                   badges=badges, bg_path=bg_path, theme=theme)
            )
            file = discord.File(buf, filename="profil.png")
            await interaction.followup.send(file=file)
        except Exception as e:
            print(f"[Profile] render error: {e}")
            # Fallback embed bila rendering gambar gagal.
            embed = discord.Embed(
                title=bptext.render_text("profile_title", name=name),
                description=(f"**{data['tier']} · Level {data['level']}**\n"
                            f"XP {data['xp_into_level']}/{data['xp_for_next']}"),
                color=0x5865F2,
            )
            embed.add_field(name="Belanja bln ini", value=_rupiah(data["spent_month"]), inline=True)
            embed.add_field(name="Total order", value=f"{data['total_orders']}x", inline=True)
            embed.add_field(name="Ulasan", value=str(data["total_reviews"]), inline=True)
            if badges:
                embed.add_field(name="Badge", value=" · ".join(badges), inline=False)
            embed.set_footer(text=bptext.render_text("profile_footer", store=STORE_NAME))
            await interaction.followup.send(embed=embed)


    async def _save_bg(self, attachment: discord.Attachment, tier: str,
                       base_name: str = PROFILE_BG_BASE):
        """Download & simpan background tier -> data/<base_name>_<tier>.<ext>."""
        ext = os.path.splitext(attachment.filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            return None
        base = f"{base_name}_{tier.lower()}"
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            for old_ext in ALLOWED_IMAGE_EXTS:
                old = os.path.join(DATA_DIR, base + old_ext)
                if os.path.exists(old):
                    try:
                        os.remove(old)
                    except Exception:
                        pass
            path = os.path.join(DATA_DIR, base + ext)
            async with aiohttp.ClientSession() as s:
                async with s.get(attachment.url) as r:
                    if r.status == 200:
                        with open(path, "wb") as f:
                            f.write(await r.read())
                        return path
        except Exception as e:
            print(f"[Profile] bg save error: {e}")
        return None

    @app_commands.command(
        name="setprofilbg",
        description="[ADMIN] Set background kartu profil per tier (upload PNG/JPG)")
    @app_commands.describe(
        tier="Tier yang diatur backgroundnya",
        image="Gambar background (PNG/JPG/WEBP). Kosongkan + reset:True untuk hapus.",
        reset="Hapus background kustom tier ini (kembali ke gradien default).")
    @app_commands.choices(tier=[
        app_commands.Choice(name=t, value=t) for t in VALID_TIERS
    ])
    async def setprofilbg(self, interaction: discord.Interaction,
                          tier: app_commands.Choice[str],
                          image: discord.Attachment = None,
                          reset: bool = False):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        tname = tier.value

        if reset:
            removed = False
            base = f"{PROFILE_BG_BASE}_{tname.lower()}"
            for ext in ALLOWED_IMAGE_EXTS:
                pth = os.path.join(DATA_DIR, base + ext)
                if os.path.exists(pth):
                    try:
                        os.remove(pth)
                        removed = True
                    except Exception:
                        pass
            msg = (f"🗑️ Background tier **{tname}** dihapus (kembali ke gradien default)."
                   if removed else f"ℹ️ Tier **{tname}** memang belum punya background kustom.")
            await interaction.followup.send(msg, ephemeral=True)
            return

        if image is None:
            await interaction.followup.send(
                "❌ Sertakan gambar (`image:`) atau gunakan `reset:True` untuk menghapus.",
                ephemeral=True)
            return
        path = await self._save_bg(image, tname)
        if path:
            await interaction.followup.send(
                f"✅ Background tier **{tname}** diset. Coba `/profil` untuk melihat.",
                ephemeral=True)
        else:
            await interaction.followup.send(
                "❌ Gagal menyimpan. Pastikan format PNG/JPG/WEBP.", ephemeral=True)

    @app_commands.command(
        name="setbadgebg",
        description="[ADMIN] Set background kartu badge 'Achievement' per tier (upload PNG/JPG)")
    @app_commands.describe(
        tier="Tier yang diatur backgroundnya",
        image="Gambar background (PNG/JPG/WEBP). Kosongkan + reset:True untuk hapus.",
        reset="Hapus background kustom tier ini (kembali ke gradien default).")
    @app_commands.choices(tier=[
        app_commands.Choice(name=t, value=t) for t in VALID_TIERS
    ])
    async def setbadgebg(self, interaction: discord.Interaction,
                         tier: app_commands.Choice[str],
                         image: discord.Attachment = None,
                         reset: bool = False):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        tname = tier.value

        if reset:
            removed = False
            base = f"{BADGE_BG_BASE}_{tname.lower()}"
            for ext in ALLOWED_IMAGE_EXTS:
                pth = os.path.join(DATA_DIR, base + ext)
                if os.path.exists(pth):
                    try:
                        os.remove(pth)
                        removed = True
                    except Exception:
                        pass
            msg = (f"🗑️ Background kartu badge tier **{tname}** dihapus (kembali ke gradien default)."
                   if removed else f"ℹ️ Tier **{tname}** memang belum punya background kartu badge kustom.")
            await interaction.followup.send(msg, ephemeral=True)
            return

        if image is None:
            await interaction.followup.send(
                "❌ Sertakan gambar (`image:`) atau gunakan `reset:True` untuk menghapus.",
                ephemeral=True)
            return
        path = await self._save_bg(image, tname, base_name=BADGE_BG_BASE)
        if path:
            await interaction.followup.send(
                f"✅ Background kartu badge tier **{tname}** diset. Berlaku saat member "
                f"berikutnya dapat badge baru (tier {tname}). Atur tata letak teks/avatar "
                f"lewat panel **Editor Badge**.",
                ephemeral=True)
        else:
            await interaction.followup.send(
                "❌ Gagal menyimpan. Pastikan format PNG/JPG/WEBP.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberProfile(bot))
    print("Cog MemberProfile siap.")
