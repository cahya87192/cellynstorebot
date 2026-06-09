"""Unit test logika murni teks panel Midman (utils/midman_text.py).

Bagian Discord (cogs/midman.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import midman_text as m


def test_specs_keys_and_defaults():
    assert set(m.MIDMAN_SPECS) == {"catalog_title", "catalog_desc", "acc_success"}
    for spec in m.MIDMAN_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = m.render_template("Midman {store} {x}", store="Toko")
    assert out == "Midman Toko {x}"
    assert m.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in m.MIDMAN_SPECS.items():
        assert m.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    m.save_text("acc_success", text="Trade beres!")
    assert m.load_text("acc_success") == "Trade beres!"


def test_empty_resets_to_default(db):
    m.save_text("catalog_title", text="custom")
    m.save_text("catalog_title", text="")
    assert m.load_text("catalog_title") == m.DEFAULT_CATALOG_TITLE


def test_save_isolated_per_kind(db):
    m.save_text("catalog_desc", text="Deskripsi baru {store}")
    assert m.load_text("catalog_desc") == "Deskripsi baru {store}"
    assert m.load_text("catalog_title") == m.DEFAULT_CATALOG_TITLE
    assert m.load_text("acc_success") == m.DEFAULT_ACC_SUCCESS


def test_render_text_store_substitution(db):
    assert m.render_text("catalog_title", store="Cellyn Store") == "MIDMAN TRADE — Cellyn Store"
    out = m.render_text("catalog_desc", store="Cellyn Store")
    assert "Cellyn Store" in out and "{store}" not in out


def test_render_text_custom(db):
    m.save_text("catalog_title", text="MIDMAN · {store}")
    assert m.render_text("catalog_title", store="MyShop") == "MIDMAN · MyShop"
