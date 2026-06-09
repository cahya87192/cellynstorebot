"""Unit test logika murni teks katalog Robux (utils/robux_text.py).

Bagian Discord (cogs/robux.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import robux_text as r


def test_specs_keys_and_defaults():
    assert set(r.ROBUX_SPECS) == {"catalog_title", "catalog_desc", "catalog_footer"}
    for spec in r.ROBUX_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = r.render_template("{emoji} Toko {store} {x}", emoji="🪙", store="Cellyn")
    assert out == "🪙 Toko Cellyn {x}"
    assert r.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in r.ROBUX_SPECS.items():
        assert r.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    r.save_text("catalog_footer", text="{store} — harga sewaktu-waktu")
    assert r.load_text("catalog_footer") == "{store} — harga sewaktu-waktu"


def test_empty_resets_to_default(db):
    r.save_text("catalog_title", text="custom")
    r.save_text("catalog_title", text="")
    assert r.load_text("catalog_title") == r.DEFAULT_CATALOG_TITLE


def test_save_isolated_per_kind(db):
    r.save_text("catalog_desc", text="Deskripsi {rate} {categories}")
    assert r.load_text("catalog_desc") == "Deskripsi {rate} {categories}"
    assert r.load_text("catalog_title") == r.DEFAULT_CATALOG_TITLE


def test_render_catalog_title(db):
    out = r.render_text("catalog_title", emoji="🪙", store="Cellyn Store")
    assert out == "🪙 ROBUX STORE — Cellyn Store"


def test_render_catalog_desc_substitution(db):
    out = r.render_text("catalog_desc", rate="Rp 100/Robux", categories="🪙 GAMEPASS")
    assert "Rp 100/Robux" in out and "🪙 GAMEPASS" in out
    assert "{rate}" not in out and "{categories}" not in out


def test_render_catalog_footer_custom(db):
    r.save_text("catalog_footer", text="{store} • cek harga")
    assert r.render_text("catalog_footer", store="MyShop") == "MyShop • cek harga"
