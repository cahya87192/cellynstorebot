"""Test resolusi emoji katalog 'lainnya' (utils/catalog_emoji.py). Logika murni.

Memastikan: default (use_custom=True) tidak mengubah perilaku Cellyn, dan saat
custom emoji dimatikan, custom emoji di-fallback ke unicode netral sementara
emoji unicode/None dibiarkan apa adanya.
"""
from utils import catalog_emoji as ce

# Subset map mirip data asli.
GROUP_EMOJI = {
    "AI": "<:emojigg_ai:1510724403627954256>",   # custom
    "GAMING": "\U0001F3AE",                       # sudah unicode 🎮
    "LAINNYA": "\U0001F5C2",                      # sudah unicode 🗂
}
CATEGORY_EMOJI = {
    "CHATGPT": "<:NewChatGPTlogo_Round:1485497156629696653>",  # custom
}


def test_is_custom_emoji():
    assert ce.is_custom_emoji("<:abc:123>") is True
    assert ce.is_custom_emoji("<a:abc:123>") is True
    assert ce.is_custom_emoji("\U0001F3AE") is False
    assert ce.is_custom_emoji("") is False
    assert ce.is_custom_emoji(None) is False


def test_group_emoji_custom_enabled_unchanged():
    # Default: kembalikan emoji asli (perilaku Cellyn).
    assert ce.resolve_group_emoji("AI", GROUP_EMOJI, use_custom=True) == GROUP_EMOJI["AI"]
    assert ce.resolve_group_emoji("GAMING", GROUP_EMOJI, use_custom=True) == "\U0001F3AE"


def test_group_emoji_custom_disabled_falls_back():
    # Custom emoji -> fallback unicode dari tabel.
    out = ce.resolve_group_emoji("AI", GROUP_EMOJI, use_custom=False)
    assert out == ce.GROUP_EMOJI_FALLBACK["AI"]
    assert not ce.is_custom_emoji(out)


def test_group_emoji_unicode_left_alone_when_disabled():
    # Emoji yang sudah unicode tidak diubah meski custom dimatikan.
    assert ce.resolve_group_emoji("GAMING", GROUP_EMOJI, use_custom=False) == "\U0001F3AE"
    assert ce.resolve_group_emoji("LAINNYA", GROUP_EMOJI, use_custom=False) == "\U0001F5C2"


def test_group_emoji_unknown_group():
    assert ce.resolve_group_emoji("TIDAK ADA", GROUP_EMOJI, use_custom=True) is None
    assert ce.resolve_group_emoji("TIDAK ADA", GROUP_EMOJI, use_custom=False) is None


def test_category_emoji_enabled_uses_category_then_group():
    # Kategori punya emoji sendiri.
    assert ce.resolve_category_emoji(
        "CHATGPT", "AI", CATEGORY_EMOJI, GROUP_EMOJI, use_custom=True) == CATEGORY_EMOJI["CHATGPT"]
    # Kategori tanpa emoji -> jatuh ke emoji grup.
    assert ce.resolve_category_emoji(
        "UNKNOWN", "AI", CATEGORY_EMOJI, GROUP_EMOJI, use_custom=True) == GROUP_EMOJI["AI"]


def test_category_emoji_disabled_falls_back_to_group_fallback():
    # Custom emoji kategori di-skip -> emoji grup (yang juga sudah di-fallback).
    out = ce.resolve_category_emoji(
        "CHATGPT", "AI", CATEGORY_EMOJI, GROUP_EMOJI, use_custom=False)
    assert out == ce.GROUP_EMOJI_FALLBACK["AI"]
    assert not ce.is_custom_emoji(out)


def test_category_emoji_no_group():
    # Tanpa grup & kategori tak dikenal -> None.
    assert ce.resolve_category_emoji(
        "UNKNOWN", None, CATEGORY_EMOJI, GROUP_EMOJI, use_custom=True) is None



def test_safe_emoji_enabled_returns_original():
    # use_custom=True -> emoji asli (custom maupun unicode) tidak diubah.
    assert ce.safe_emoji("<:Robux:123>", "\U0001FA99", use_custom=True) == "<:Robux:123>"
    assert ce.safe_emoji("\U0001F48E", "\U0001FA99", use_custom=True) == "\U0001F48E"


def test_safe_emoji_disabled_custom_uses_fallback():
    # Custom emoji -> fallback saat custom dimatikan.
    assert ce.safe_emoji("<:Robux:123>", "\U0001FA99", use_custom=False) == "\U0001FA99"
    assert ce.safe_emoji("<a:diamond:9>", "\U0001F48E", use_custom=False) == "\U0001F48E"


def test_safe_emoji_disabled_unicode_left_alone():
    # Emoji unicode/None dibiarkan apa adanya walau custom dimatikan.
    assert ce.safe_emoji("\U0001F3AE", "\U0001F525", use_custom=False) == "\U0001F3AE"
    assert ce.safe_emoji(None, "\U0001F48E", use_custom=False) is None


def test_safe_emoji_default_fallback_none():
    # Tanpa fallback eksplisit -> custom emoji jadi None saat dimatikan.
    assert ce.safe_emoji("<:x:1>", use_custom=False) is None
