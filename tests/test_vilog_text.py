"""Unit test logika murni teks katalog Vilog (utils/vilog_text.py).

Bagian Discord (cogs/vilog.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import vilog_text as v


def test_specs_keys_and_defaults():
    assert set(v.VILOG_SPECS) == {
        "catalog_title", "catalog_desc", "catalog_note",
        "catalog_footer", "done_success", "cancel_title",
    }
    for spec in v.VILOG_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = v.render_template("Toko {store} step {step} {x}", store="Cellyn", step=500)
    assert out == "Toko Cellyn step 500 {x}"
    assert v.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in v.VILOG_SPECS.items():
        assert v.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    v.save_text("cancel_title", text="Vilog Batal")
    assert v.load_text("cancel_title") == "Vilog Batal"


def test_empty_resets_to_default(db):
    v.save_text("catalog_note", text="custom")
    v.save_text("catalog_note", text="")
    assert v.load_text("catalog_note") == v.DEFAULT_CATALOG_NOTE


def test_save_isolated_per_kind(db):
    v.save_text("catalog_title", text="VILOG {store}")
    assert v.load_text("catalog_title") == "VILOG {store}"
    assert v.load_text("catalog_desc") == v.DEFAULT_CATALOG_DESC
    assert v.load_text("done_success") == v.DEFAULT_DONE_SUCCESS


def test_render_catalog_title_store(db):
    assert v.render_text("catalog_title", store="Cellyn Store") == \
        "TOPUP ROBUX VIA LOGIN (VILOG) — Cellyn Store"


def test_render_catalog_footer_all_placeholders(db):
    out = v.render_text("catalog_footer", store="Cellyn Store", step=500, max=10000)
    assert "Cellyn Store" in out and "500" in out and "10000" in out
    assert "{store}" not in out and "{step}" not in out and "{max}" not in out


def test_render_done_success_custom(db):
    v.save_text("done_success", text="Beres topup di {store}!")
    assert v.render_text("done_success", store="MyShop") == "Beres topup di MyShop!"
