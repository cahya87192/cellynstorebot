"""Unit test logika murni teks order (utils/order_text.py).

Bagian Discord (cogs/orders.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import order_text as o


def test_specs_keys_and_defaults():
    assert set(o.ORDER_SPECS) == {"success", "cancel_title", "cancel_reason_default"}
    for spec in o.ORDER_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = o.render_template("Makasih belanja di {store} {x}", store="Toko")
    assert out == "Makasih belanja di Toko {x}"
    assert o.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in o.ORDER_SPECS.items():
        assert o.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    o.save_text("cancel_title", text="Order Batal")
    assert o.load_text("cancel_title") == "Order Batal"


def test_empty_resets_to_default(db):
    o.save_text("cancel_reason_default", text="custom")
    o.save_text("cancel_reason_default", text="")
    assert o.load_text("cancel_reason_default") == o.DEFAULT_CANCEL_REASON


def test_save_isolated_per_kind(db):
    o.save_text("success", text="Selesai di {store}")
    assert o.load_text("success") == "Selesai di {store}"
    assert o.load_text("cancel_title") == o.DEFAULT_CANCEL_TITLE


def test_render_text_store_substitution(db):
    out = o.render_text("success", store="Cellyn Store")
    assert "Cellyn Store" in out and "{store}" not in out


def test_render_text_custom(db):
    o.save_text("success", text="Beres! Makasih ya di {store}.")
    assert o.render_text("success", store="MyShop") == "Beres! Makasih ya di MyShop."
