"""Unit test logika murni teks katalog ML (utils/ml_text.py).

Bagian Discord (cogs/ml.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import ml_text as m


def test_specs_keys_and_defaults():
    assert set(m.ML_SPECS) == {
        "catalog_title", "catalog_desc", "catalog_footer", "done_success", "cancel_title",
    }
    for spec in m.ML_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = m.render_template("Toko {store} game {games} {x}", store="Cellyn", games="ML")
    assert out == "Toko Cellyn game ML {x}"
    assert m.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in m.ML_SPECS.items():
        assert m.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    m.save_text("cancel_title", text="Topup Batal")
    assert m.load_text("cancel_title") == "Topup Batal"


def test_empty_resets_to_default(db):
    m.save_text("catalog_footer", text="custom")
    m.save_text("catalog_footer", text="")
    assert m.load_text("catalog_footer") == m.DEFAULT_CATALOG_FOOTER


def test_save_isolated_per_kind(db):
    m.save_text("catalog_title", text="DIAMOND TOPUP")
    assert m.load_text("catalog_title") == "DIAMOND TOPUP"
    assert m.load_text("catalog_desc") == m.DEFAULT_CATALOG_DESC
    assert m.load_text("done_success") == m.DEFAULT_DONE_SUCCESS


def test_render_catalog_desc_substitution(db):
    out = m.render_text("catalog_desc", store="Cellyn Store", games="• ML\n• FF")
    assert "Cellyn Store" in out and "• ML" in out
    assert "{store}" not in out and "{games}" not in out


def test_render_done_success_custom(db):
    m.save_text("done_success", text="Topup beres di {store}!")
    assert m.render_text("done_success", store="MyShop") == "Topup beres di MyShop!"


def test_render_footer_store(db):
    assert m.render_text("catalog_footer", store="Cellyn Store") == "Cellyn Store"
