"""Unit test logika murni teks rating & ulasan (utils/review_text.py).

Bagian Discord (cogs/reviews.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import review_text as r


def test_specs_keys_and_defaults():
    expected = {
        "prompt_title", "prompt_desc", "invoice_title", "invoice_desc", "invoice_footer",
        "expired_title", "expired_desc", "published_title", "reminder_title",
        "reminder_desc", "footer_warning", "thankyou_5star", "thankyou_normal",
    }
    assert set(r.REVIEW_SPECS) == expected
    for spec in r.REVIEW_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = r.render_template("Hai {store} dalam {hours} jam {x}", store="Toko", hours=24)
    assert out == "Hai Toko dalam 24 jam {x}"
    assert r.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in r.REVIEW_SPECS.items():
        assert r.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    r.save_text("prompt_title", text="Kasih Bintang Dong!")
    assert r.load_text("prompt_title") == "Kasih Bintang Dong!"


def test_empty_resets_to_default(db):
    r.save_text("reminder_title", text="custom")
    r.save_text("reminder_title", text="")
    assert r.load_text("reminder_title") == r.DEFAULT_REMINDER_TITLE


def test_save_isolated_per_kind(db):
    r.save_text("invoice_title", text="Nota")
    assert r.load_text("invoice_title") == "Nota"
    assert r.load_text("prompt_title") == r.DEFAULT_PROMPT_TITLE
    assert r.load_text("expired_title") == r.DEFAULT_EXPIRED_TITLE


def test_render_prompt_desc_substitution(db):
    out = r.render_text("prompt_desc", store="Cellyn Store", hours=24)
    assert "Cellyn Store" in out and "24" in out
    assert "{store}" not in out and "{hours}" not in out


def test_render_thankyou_5star(db):
    out = r.render_text("thankyou_5star", store="Cellyn Store", stars="⭐⭐⭐⭐⭐")
    assert "Cellyn Store" in out and "⭐⭐⭐⭐⭐" in out
    assert "{store}" not in out and "{stars}" not in out


def test_render_thankyou_normal(db):
    out = r.render_text("thankyou_normal", rating=4, stars="⭐⭐⭐⭐☆")
    assert "4/5" in out and "⭐⭐⭐⭐☆" in out
    assert "{rating}" not in out and "{stars}" not in out


def test_render_footer_warning_custom(db):
    r.save_text("footer_warning", text="{store} — rating dulu ya")
    assert r.render_text("footer_warning", store="MyShop") == "MyShop — rating dulu ya"
