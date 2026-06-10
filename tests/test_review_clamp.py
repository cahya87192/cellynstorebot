"""Test pembatasan teks ulasan & glyph bintang (utils/reviews.py).

clamp_review_text: agar ulasan tidak kepanjangan/berantakan di kartu testimoni.
star_glyphs: bintang sebagai glyph teks (★/☆) yang aman dirender font kartu.
"""
from utils import reviews as rv


def test_clamp_none_and_empty():
    assert rv.clamp_review_text(None) is None
    assert rv.clamp_review_text("") is None
    assert rv.clamp_review_text("    ") is None


def test_clamp_short_unchanged():
    assert rv.clamp_review_text("Mantap, cepat!") == "Mantap, cepat!"


def test_clamp_collapses_whitespace():
    assert rv.clamp_review_text("baris1\n\n  baris2\t  baris3") == "baris1 baris2 baris3"


def test_clamp_truncates_with_ellipsis():
    long = "kata " * 100  # jauh melebihi batas
    out = rv.clamp_review_text(long)
    assert len(out) <= rv.REVIEW_MAX_LEN + 1   # +1 untuk elipsis
    assert out.endswith("\u2026")


def test_clamp_respects_custom_max():
    out = rv.clamp_review_text("a" * 50, max_len=10)
    assert out.endswith("\u2026")
    assert len(out) <= 11


def test_clamp_word_boundary():
    text = "satu dua tiga empat lima enam tujuh delapan sembilan"
    out = rv.clamp_review_text(text, max_len=20)
    # tidak memotong di tengah kata (selain elipsis)
    assert "  " not in out
    assert out.endswith("\u2026")


def test_star_glyphs():
    assert rv.star_glyphs(5) == "\u2605" * 5
    assert rv.star_glyphs(3) == "\u2605\u2605\u2605\u2606\u2606"
    assert rv.star_glyphs(0) == "\u2606" * 5
    assert rv.star_glyphs(99) == "\u2605" * 5    # clamp atas
    assert rv.star_glyphs(None) == "\u2606" * 5
    assert rv.star_glyphs("bukan") == "\u2606" * 5
