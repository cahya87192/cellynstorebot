"""Unit test logika murni teks Badge & Profil (utils/badge_profile_text.py).

Bagian Discord (cogs/achievements.py, cogs/profile.py) tidak diuji di sini; fokus
pada substitusi placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import badge_profile_text as b


def test_specs_keys_and_defaults():
    assert set(b.BADGE_PROFILE_SPECS) == {
        "badge_title", "badge_empty", "badge_footer", "profile_title", "profile_footer",
    }
    for spec in b.BADGE_PROFILE_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = b.render_template("Badge {name} {x}", name="Andi")
    assert out == "Badge Andi {x}"
    assert b.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in b.BADGE_PROFILE_SPECS.items():
        assert b.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    b.save_text("badge_empty", text="Belum punya badge")
    assert b.load_text("badge_empty") == "Belum punya badge"


def test_empty_resets_to_default(db):
    b.save_text("badge_title", text="custom")
    b.save_text("badge_title", text="")
    assert b.load_text("badge_title") == b.DEFAULT_BADGE_TITLE


def test_save_isolated_per_kind(db):
    b.save_text("profile_title", text="Kartu {name}")
    assert b.load_text("profile_title") == "Kartu {name}"
    assert b.load_text("badge_title") == b.DEFAULT_BADGE_TITLE


def test_render_badge_title_name(db):
    assert b.render_text("badge_title", name="Andi") == "🏅 Badge — Andi"


def test_render_profile_title_name(db):
    assert b.render_text("profile_title", name="Budi") == "Profil Budi"


def test_render_footer_store(db):
    assert b.render_text("badge_footer", store="Cellyn Store") == "Cellyn Store"
    assert b.render_text("profile_footer", store="Cellyn Store") == "Cellyn Store"
