"""Unit test logika murni teks DM pengingat langganan (utils/sub_followup_text.py).

Bagian Discord (cogs/sub_followup.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import sub_followup_text as s


def test_specs_keys_and_defaults():
    assert set(s.SUB_FOLLOWUP_SPECS) == {"title", "description", "footer", "button_label"}
    for spec in s.SUB_FOLLOWUP_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = s.render_template("Halo {store} {waktu} {x}", store="Cellyn", waktu="besok")
    assert out == "Halo Cellyn besok {x}"
    assert s.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in s.SUB_FOLLOWUP_SPECS.items():
        assert s.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    s.save_text("button_label", text="Perpanjang sekarang")
    assert s.load_text("button_label") == "Perpanjang sekarang"


def test_empty_resets_to_default(db):
    s.save_text("title", text="custom")
    s.save_text("title", text="")
    assert s.load_text("title") == s.DEFAULT_TITLE


def test_save_isolated_per_kind(db):
    s.save_text("footer", text="{store} — ingat ya")
    assert s.load_text("footer") == "{store} — ingat ya"
    assert s.load_text("title") == s.DEFAULT_TITLE
    assert s.load_text("description") == s.DEFAULT_DESC


def test_render_description_substitution(db):
    out = s.render_text("description", store="Cellyn Store", item="Netflix", waktu="besok")
    assert "Cellyn Store" in out and "Netflix" in out and "besok" in out
    assert "{store}" not in out and "{item}" not in out and "{waktu}" not in out


def test_render_footer_store(db):
    assert s.render_text("footer", store="Cellyn Store") == "Cellyn Store · pengingat perpanjangan"


def test_render_description_custom(db):
    s.save_text("description", text="{item} habis {waktu} di {store}")
    out = s.render_text("description", store="MyShop", item="Canva", waktu="hari ini")
    assert out == "Canva habis hari ini di MyShop"
