"""Unit test logika murni teks pencarian produk (utils/product_search_text.py)."""
from utils import product_search_text as p


def test_specs_keys_and_defaults():
    assert set(p.PRODUCT_SEARCH_SPECS) == {
        "results_title", "results_footer", "suggest_title", "suggest_intro",
        "suggest_footer", "select_placeholder", "ticket_error",
    }
    for spec in p.PRODUCT_SEARCH_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = p.render_template("Cari {query} di {store} {x}", query="ml", store="Cellyn")
    assert out == "Cari ml di Cellyn {x}"
    assert p.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in p.PRODUCT_SEARCH_SPECS.items():
        assert p.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    p.save_text("ticket_error", text="Gagal, coba lagi.")
    assert p.load_text("ticket_error") == "Gagal, coba lagi."


def test_empty_resets_to_default(db):
    p.save_text("suggest_intro", text="custom")
    p.save_text("suggest_intro", text="")
    assert p.load_text("suggest_intro") == p.DEFAULT_SUGGEST_INTRO


def test_save_isolated_per_kind(db):
    p.save_text("results_title", text="Hasil: {query}")
    assert p.load_text("results_title") == "Hasil: {query}"
    assert p.load_text("results_footer") == p.DEFAULT_RESULTS_FOOTER


def test_render_results_title_query(db):
    out = p.render_text("results_title", query="diamond ml")
    assert "diamond ml" in out and "{query}" not in out


def test_render_results_footer_store(db):
    out = p.render_text("results_footer", store="Cellyn Store")
    assert "Cellyn Store" in out and "{store}" not in out


def test_backup_registry_includes_psearch():
    from utils import text_backup as tb
    keys = tb.collect_keys()
    assert p.PRODUCT_SEARCH_SPECS["results_title"]["key"] in keys
