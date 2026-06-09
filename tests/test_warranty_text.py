"""Unit test logika murni teks garansi (utils/warranty_text.py).

Bagian Discord (cogs/warranty.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import warranty_text as w


def test_specs_keys_and_defaults():
    assert set(w.WARRANTY_SPECS) == {
        "panel_title", "panel_desc", "reject_unrated", "reject_expired", "ticket_desc",
    }
    for spec in w.WARRANTY_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = w.render_template("Halo {store} {x}", store="Toko")
    assert out == "Halo Toko {x}"
    assert w.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in w.WARRANTY_SPECS.items():
        assert w.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    w.save_text("panel_title", text="Garansi Toko")
    assert w.load_text("panel_title") == "Garansi Toko"


def test_empty_resets_to_default(db):
    w.save_text("reject_expired", text="custom")
    w.save_text("reject_expired", text="")
    assert w.load_text("reject_expired") == w.DEFAULT_REJECT_EXPIRED


def test_save_isolated_per_kind(db):
    w.save_text("panel_desc", text="desc baru {store}")
    assert w.load_text("panel_desc") == "desc baru {store}"
    assert w.load_text("panel_title") == w.DEFAULT_PANEL_TITLE
    assert w.load_text("ticket_desc") == w.DEFAULT_TICKET_DESC


def test_render_text_store_substitution(db):
    out = w.render_text("panel_desc", store="Cellyn Store")
    assert "Cellyn Store" in out and "{store}" not in out


def test_render_text_custom(db):
    w.save_text("panel_desc", text="Kendala di {store}? Klaim sekarang.")
    out = w.render_text("panel_desc", store="MyShop")
    assert out == "Kendala di MyShop? Klaim sekarang."
