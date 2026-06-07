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
