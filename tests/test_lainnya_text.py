"""Unit test logika murni teks katalog Lainnya (utils/lainnya_text.py).

Bagian Discord (cogs/lainnya.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import lainnya_text as la


def test_specs_keys_and_defaults():
    assert set(la.LAINNYA_SPECS) == {
        "catalog_title", "catalog_desc", "catalog_footer",
        "autoreply_cat_title", "autoreply_cat_footer",
        "autoreply_search_title", "autoreply_search_footer",
    }
    for spec in la.LAINNYA_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = la.render_template("Toko {store} grup {groups} {x}", store="Cellyn", groups="AI")
    assert out == "Toko Cellyn grup AI {x}"
    assert la.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in la.LAINNYA_SPECS.items():
        assert la.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    la.save_text("catalog_footer", text="{store} — toko digital")
    assert la.load_text("catalog_footer") == "{store} — toko digital"


def test_empty_resets_to_default(db):
    la.save_text("autoreply_cat_footer", text="custom")
    la.save_text("autoreply_cat_footer", text="")
    assert la.load_text("autoreply_cat_footer") == la.DEFAULT_AUTOREPLY_CAT_FOOTER


def test_save_isolated_per_kind(db):
    la.save_text("catalog_title", text="LAYANAN {store}")
    assert la.load_text("catalog_title") == "LAYANAN {store}"
    assert la.load_text("catalog_desc") == la.DEFAULT_CATALOG_DESC


def test_render_catalog_title_store(db):
    assert la.render_text("catalog_title", store="Cellyn Store") == "🛒 LAYANAN — Cellyn Store"


def test_render_catalog_desc_groups(db):
    out = la.render_text("catalog_desc", groups="🤖 AI — 5 produk")
    assert "🤖 AI — 5 produk" in out and "{groups}" not in out


def test_render_autoreply_cat_title(db):
    out = la.render_text("autoreply_cat_title", category="CANVA", store="Cellyn Store")
    assert out == "📦 CANVA — Cellyn Store"
