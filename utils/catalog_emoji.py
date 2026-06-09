"""Resolusi emoji katalog "lainnya" yang aman lintas-server (logika murni).

Server self-host lain tidak punya custom emoji Cellyn (format `<:nama:id>` /
`<a:nama:id>`). Bila custom emoji dimatikan (LAINNYA_USE_CUSTOM_EMOJI=false),
custom emoji di-fallback ke unicode netral supaya UI katalog tetap rapi —
tidak menampilkan teks mentah dan tidak membuat opsi dropdown ditolak Discord.

Default (use_custom=True) = perilaku server Cellyn tidak berubah.

Dipisah dari cog supaya bisa diuji tanpa Discord.
"""

# Fallback unicode per GRUP saat custom emoji dimatikan.
GROUP_EMOJI_FALLBACK = {
    "AI": "\U0001F916",            # 🤖
    "STREAMING": "\U0001F3AC",     # 🎬
    "MUSIK": "\U0001F3B5",         # 🎵
    "EDITING": "\U0001F3A8",       # 🎨
    "AKUN & STORAGE": "\U0001F5C4", # 🗄
    "GAMING": "\U0001F3AE",        # 🎮
    "DISCORD": "\U0001F4AC",       # 💬
    "SOCIAL MEDIA": "\U0001F4F1",  # 📱
    "LAINNYA": "\U0001F5C2",       # 🗂
}


def is_custom_emoji(value) -> bool:
    """True bila string berbentuk custom emoji Discord `<:nama:id>`/`<a:nama:id>`."""
    return (
        isinstance(value, str)
        and value.startswith("<")
        and value.endswith(">")
        and ":" in value
    )


def safe_emoji(value, fallback=None, use_custom: bool = True):
    """Emoji aman untuk komponen UI (SelectOption/Button) lintas-server.

    Custom emoji server (mis. `<:Robux:123>`) akan DITOLAK Discord di server lain
    yang tidak punya emoji itu, sehingga dropdown/tombol gagal tampil. Helper ini:
      - use_custom=True  -> kembalikan emoji asli (perilaku server asal).
      - use_custom=False -> custom emoji diganti `fallback` (unicode/None aman);
        emoji yang sudah unicode atau None dibiarkan apa adanya.
    """
    if use_custom:
        return value
    if is_custom_emoji(value):
        return fallback
    return value


def resolve_group_emoji(group, group_emoji_map, use_custom: bool = True):
    """Emoji untuk sebuah grup, aman lintas-server.

    - use_custom=True  -> kembalikan emoji asli (custom server Cellyn).
    - use_custom=False -> custom emoji diganti fallback unicode; emoji yang sudah
      unicode (mis. GAMING/LAINNYA) atau None dibiarkan apa adanya.
    """
    raw = group_emoji_map.get(group)
    if use_custom:
        return raw
    if is_custom_emoji(raw):
        return GROUP_EMOJI_FALLBACK.get(group)
    return raw


def resolve_category_emoji(category, group, category_emoji_map, group_emoji_map,
                           use_custom: bool = True):
    """Emoji untuk sebuah kategori, dengan fallback ke emoji grup.

    Mempertahankan perilaku lama: emoji kategori dulu, kalau tidak ada pakai
    emoji grup. Saat use_custom=False, custom emoji kategori di-skip lalu
    jatuh ke emoji grup (yang juga sudah di-fallback).
    """
    raw = category_emoji_map.get(category)
    if not use_custom and is_custom_emoji(raw):
        raw = None
    if raw:
        return raw
    return resolve_group_emoji(group, group_emoji_map, use_custom)
