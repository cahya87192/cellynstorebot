"""Unit test logika murni teks papan Top Spender (utils/top_spender_text.py).

Bagian Discord (cogs/top_spender.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import top_spender_text as t


def test_specs_keys_and_defaults():
    assert set(t.TOP_SPENDER_SPECS) == {"title", "description", "empty", "benefit", "footer"}
    for spec in t.TOP_SPENDER_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = t.render_template("{month} di {store} {x}", month="Juni 2026", store="Cellyn")
    assert out == "Juni 2026 di Cellyn {x}"
    assert t.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in t.TOP_SPENDER_SPECS.items():
        assert t.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    t.save_text("empty", text="Belum ada nih")
    assert t.load_text("empty") == "Belum ada nih"


def test_empty_resets_to_default(db):
    t.save_text("benefit", text="custom")
    t.save_text("benefit", text="")
    assert t.load_text("benefit") == t.DEFAULT_BENEFIT


def test_save_isolated_per_kind(db):
    t.save_text("title", text="🏆 Juara — {month}")
    assert t.load_text("title") == "🏆 Juara — {month}"
    assert t.load_text("description") == t.DEFAULT_DESC
    assert t.load_text("footer") == t.DEFAULT_FOOTER


def test_render_title_month(db):
    assert t.render_text("title", month="Juni 2026") == "🏆 Top Spender — Juni 2026"


def test_render_description_store(db):
    out = t.render_text("description", store="Cellyn Store")
    assert "Cellyn Store" in out and "{store}" not in out


def test_render_footer_custom(db):
    t.save_text("footer", text="{store} • bulanan")
    assert t.render_text("footer", store="MyShop") == "MyShop • bulanan"
