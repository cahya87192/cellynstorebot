"""Logika murni untuk fitur sticky message umum (tanpa dependensi discord).

Dipisah dari cog supaya gampang diuji:
  - keputusan debounce (kapan boleh re-stick), dan
  - serialisasi payload sticky (teks / embed) ke & dari JSON untuk disimpan.

Cog `cogs/sticky.py` yang mengurus Discord-nya (kirim/hapus pesan, listener).
"""

import json

# Default debounce: baru re-stick bila sticky sudah "ketimbun" beberapa pesan
# DAN cooldown terlewati. Tujuannya menghindari spam / rate-limit.
DEFAULT_MIN_MESSAGES = 3
DEFAULT_COOLDOWN_SECONDS = 20


def should_restick(message_count, last_ts, now_ts, *,
                   min_messages=DEFAULT_MIN_MESSAGES,
                   cooldown=DEFAULT_COOLDOWN_SECONDS):
    """True bila sticky perlu dikirim ulang ke paling bawah channel.

    Syarat (keduanya wajib):
      - sudah ada >= `min_messages` pesan (non-bot) sejak sticky terakhir, dan
      - sudah lewat >= `cooldown` detik sejak re-stick terakhir (`last_ts`).

    `last_ts`/`now_ts` memakai jam monotonic (detik). `last_ts` boleh None/0
    untuk menandakan belum pernah re-stick.
    """
    if message_count < min_messages:
        return False
    if (now_ts - (last_ts or 0.0)) < cooldown:
        return False
    return True


def serialize_payload(content=None, embed_dict=None) -> str:
    """Bungkus payload sticky ke JSON string untuk disimpan di DB.

    `content`   : teks biasa (boleh None).
    `embed_dict`: dict embed (hasil Embed.to_dict()) atau None.
    """
    return json.dumps({"content": content, "embed": embed_dict})


def deserialize_payload(raw):
    """Kebalikan serialize_payload -> (content, embed_dict).

    Toleran: input kosong/rusak menghasilkan (None, None).
    """
    if not raw:
        return None, None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None, None
    if not isinstance(data, dict):
        return None, None
    return data.get("content"), data.get("embed")


def has_payload(content, embed_dict) -> bool:
    """True bila ada sesuatu yang layak dikirim (teks non-kosong atau embed)."""
    if content and str(content).strip():
        return True
    return bool(embed_dict)



# ── Kelola map sticky (untuk admin panel) ───────────────────────────────────────
# Sticky disimpan di tabel `bot_state` key `sticky_messages` sebagai JSON
# {channel_id: {message_id, content, embed}} (lihat cogs/sticky.py). Fungsi di
# bawah ini MURNI (parse/serialize/bentuk payload) supaya bisa dipakai admin
# panel Flask tanpa import discord, dan gampang diuji.

STICKY_KEY = "sticky_messages"
COLOR_DEFAULT = 0x5865F2


def parse_sticky_map(raw):
    """Parse JSON map sticky -> {int channel_id: entry dict}. Toleran rusak -> {}."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for k, v in data.items():
        try:
            cid = int(k)
        except (ValueError, TypeError):
            continue
        if isinstance(v, dict):
            out[cid] = v
    return out


def serialize_sticky_map(m):
    """Kebalikan parse_sticky_map: dict -> JSON string (key channel_id jadi str)."""
    return json.dumps({str(k): v for k, v in (m or {}).items()})


def parse_color_hex(text, default=COLOR_DEFAULT):
    """'#5865F2' / '5865F2' -> int. None/invalid -> default."""
    if not text:
        return default
    try:
        return int(str(text).lstrip("#"), 16)
    except (ValueError, TypeError):
        return default


def color_to_hex(value, default=COLOR_DEFAULT):
    """int warna -> '#RRGGBB' untuk ditampilkan di form. Invalid -> default."""
    try:
        n = int(value)
    except (ValueError, TypeError):
        n = default
    return "#{:06X}".format(n & 0xFFFFFF)


def build_embed_dict(title=None, description=None, color_hex=None, footer=None):
    """Bangun dict embed minimal, atau None bila tak ada judul/isi."""
    title = (title or "").strip() or None
    description = (description or "").strip() or None
    if not (title or description):
        return None
    embed = {"type": "rich", "color": parse_color_hex(color_hex)}
    if title:
        embed["title"] = title
    if description:
        embed["description"] = description
    if footer:
        embed["footer"] = {"text": footer}
    return embed


def make_entry(content=None, *, title=None, description=None, color_hex=None,
               footer=None, message_id=None):
    """Bentuk entry sticky {message_id, content, embed} untuk disimpan di map.

    Mengembalikan (entry|None, ok). ok=False bila tak ada payload (teks/embed).
    """
    content = (content or "").strip() or None
    embed = build_embed_dict(title, description, color_hex, footer)
    if not has_payload(content, embed):
        return None, False
    return {"message_id": message_id, "content": content, "embed": embed}, True


def entry_fields(entry):
    """Pecah entry tersimpan -> dict field flat untuk form admin.

    {content, title, description, color_hex, message_id, has_embed}
    """
    if not isinstance(entry, dict):
        entry = {}
    embed = entry.get("embed") if isinstance(entry.get("embed"), dict) else {}
    footer = embed.get("footer") if isinstance(embed.get("footer"), dict) else {}
    return {
        "content": entry.get("content") or "",
        "title": embed.get("title") or "",
        "description": embed.get("description") or "",
        "color_hex": color_to_hex(embed.get("color")) if embed else color_to_hex(COLOR_DEFAULT),
        "footer": (footer.get("text") if isinstance(footer, dict) else "") or "",
        "message_id": entry.get("message_id"),
        "has_embed": bool(embed),
    }


def entry_summary(entry, *, limit=80):
    """Ringkasan singkat isi sticky untuk daftar di admin panel."""
    if not isinstance(entry, dict):
        return ""
    content = (entry.get("content") or "").strip()
    if content:
        text = content
    else:
        embed = entry.get("embed") if isinstance(entry.get("embed"), dict) else {}
        text = (embed.get("title") or embed.get("description") or "").strip()
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[:limit - 1].rstrip() + "…"
    return text


def load_sticky_map():
    """Baca map sticky dari DB (bot_state). Lazy import get_conn."""
    from utils.db import get_conn
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM bot_state WHERE key=?", (STICKY_KEY,)
        ).fetchone()
    except Exception:
        row = None
    conn.close()
    return parse_sticky_map(row["value"] if row else None)


def save_sticky_map(m):
    """Tulis map sticky ke DB (bot_state). Lazy import get_conn."""
    from utils.db import get_conn
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
        (STICKY_KEY, serialize_sticky_map(m)),
    )
    conn.commit()
    conn.close()


def update_entry_content(m, channel_id, content=None, *, title=None,
                         description=None, color_hex=None, footer=None):
    """Perbarui payload sticky untuk channel di map (in-place), pertahankan message_id.

    Mengembalikan (map, ok). ok=False bila channel tak ada di map atau payload kosong.
    """
    try:
        cid = int(channel_id)
    except (ValueError, TypeError):
        return m, False
    if cid not in m:
        return m, False
    old = m.get(cid) or {}
    entry, ok = make_entry(
        content, title=title, description=description, color_hex=color_hex,
        footer=footer, message_id=old.get("message_id"),
    )
    if not ok:
        return m, False
    m[cid] = entry
    return m, True


def remove_entry(m, channel_id):
    """Hapus entry sticky channel dari map. Mengembalikan (map, removed_entry|None)."""
    try:
        cid = int(channel_id)
    except (ValueError, TypeError):
        return m, None
    return m, m.pop(cid, None)
