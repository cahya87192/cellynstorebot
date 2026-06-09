"""Unit test logika murni teks katalog GP (utils/gp_text.py).

Bagian Discord (cogs/gp.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import gp_text as g


def test_specs_keys_and_defaults():
    assert set(g.GP_SPECS) == {
        "catalog_title", "catalog_desc", "catalog_howto",
        "catalog_note", "catalog_footer", "done_success",
    }
    for spec in g.GP_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = g.render_template("Toko {store} min {min} {x}", store="Cellyn", min=300)
    assert out == "Toko Cellyn min 300 {x}"
    assert g.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in g.GP_SPECS.items():
        assert g.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    g.save_text("catalog_howto", text="Langkah baru")
    assert g.load_text("catalog_howto") == "Langkah baru"


def test_empty_resets_to_default(db):
    g.save_text("catalog_note", text="custom")
    g.save_text("catalog_note", text="")
    assert g.load_text("catalog_note") == g.DEFAULT_CATALOG_NOTE


def test_save_isolated_per_kind(db):
    g.save_text("catalog_title", text="GAMEPASS {store}")
    assert g.load_text("catalog_title") == "GAMEPASS {store}"
    assert g.load_text("catalog_desc") == g.DEFAULT_CATALOG_DESC
    assert g.load_text("done_success") == g.DEFAULT_DONE_SUCCESS


def test_render_catalog_title_store(db):
    assert g.render_text("catalog_title", store="Cellyn Store") == \
        "TOPUP ROBUX VIA GAMEPASS — Cellyn Store"


def test_render_catalog_desc_min(db):
    out = g.render_text("catalog_desc", min=300)
    assert "300" in out and "{min}" not in out


def test_render_done_success_custom(db):
    g.save_text("done_success", text="Beres di {store}!")
    assert g.render_text("done_success", store="MyShop") == "Beres di MyShop!"
