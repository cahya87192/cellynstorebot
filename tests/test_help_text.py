"""Unit test logika murni teks /help (utils/help_text.py).

Bagian Discord (cogs/help_slash.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import help_text as h


def test_specs_keys_and_defaults():
    assert set(h.HELP_SPECS) == {"title", "description", "footer"}
    for spec in h.HELP_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = h.render_template("{store} hilang {seconds} dtk {x}", store="Cellyn", seconds=60)
    assert out == "Cellyn hilang 60 dtk {x}"
    assert h.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in h.HELP_SPECS.items():
        assert h.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    h.save_text("title", text="📖 Bantuan")
    assert h.load_text("title") == "📖 Bantuan"


def test_empty_resets_to_default(db):
    h.save_text("description", text="custom")
    h.save_text("description", text="")
    assert h.load_text("description") == h.DEFAULT_DESC


def test_save_isolated_per_kind(db):
    h.save_text("footer", text="{store} - {seconds}s")
    assert h.load_text("footer") == "{store} - {seconds}s"
    assert h.load_text("title") == h.DEFAULT_TITLE


def test_render_footer_substitution(db):
    out = h.render_text("footer", store="Cellyn Store", seconds=60)
    assert "Cellyn Store" in out and "60" in out
    assert "{store}" not in out and "{seconds}" not in out


def test_render_title_no_placeholder(db):
    assert h.render_text("title") == h.DEFAULT_TITLE


def test_render_footer_custom(db):
    h.save_text("footer", text="{store} • {seconds} detik ya")
    assert h.render_text("footer", store="MyShop", seconds=30) == "MyShop • 30 detik ya"
