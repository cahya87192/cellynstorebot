"""Unit test logika murni teks pembungkus FAQ (utils/faq_text.py).

Bagian Discord (cogs/faq.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import faq_text as f


def test_specs_keys_and_defaults():
    assert set(f.FAQ_TEXT_SPECS) == {
        "faq_title", "faq_title_cont", "faq_desc", "faq_footer",
        "autocs_title", "autocs_footer",
        "saran_title", "saran_footer", "saran_success",
        "saran_no_channel", "saran_fail",
    }
    for spec in f.FAQ_TEXT_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = f.render_template("FAQ {store} {x}", store="Cellyn")
    assert out == "FAQ Cellyn {x}"
    assert f.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in f.FAQ_TEXT_SPECS.items():
        assert f.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    f.save_text("saran_title", text="Masukan Baru!")
    assert f.load_text("saran_title") == "Masukan Baru!"


def test_empty_resets_to_default(db):
    f.save_text("faq_footer", text="custom")
    f.save_text("faq_footer", text="")
    assert f.load_text("faq_footer") == f.DEFAULT_FAQ_FOOTER


def test_save_isolated_per_kind(db):
    f.save_text("faq_title", text="FAQ {store} keren")
    assert f.load_text("faq_title") == "FAQ {store} keren"
    assert f.load_text("faq_desc") == f.DEFAULT_FAQ_DESC
    assert f.load_text("saran_success") == f.DEFAULT_SARAN_SUCCESS


def test_render_faq_title_store(db):
    assert f.render_text("faq_title", store="Cellyn Store") == "❓ FAQ — Cellyn Store"


def test_render_autocs_title_question(db):
    out = f.render_text("autocs_title", question="Berapa lama prosesnya?")
    assert out == "💬 Berapa lama prosesnya?"


def test_render_saran_success_no_placeholder(db):
    assert f.render_text("saran_success") == f.DEFAULT_SARAN_SUCCESS


def test_render_faq_desc_custom(db):
    f.save_text("faq_desc", text="Tanya seputar {store} ya!")
    assert f.render_text("faq_desc", store="MyShop") == "Tanya seputar MyShop ya!"
