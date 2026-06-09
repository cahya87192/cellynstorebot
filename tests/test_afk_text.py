"""Unit test logika murni teks AFK (utils/afk.py).

Bagian Discord (cogs/afk.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import afk as a


def test_afk_specs_has_all_kinds():
    assert set(a.AFK_SPECS) == {"set", "back", "mention", "already"}
    for spec in a.AFK_SPECS.values():
        assert spec["key"] and spec["default"]
        assert spec["placeholders"]


def test_render_template_replaces_placeholders():
    out = a.render_template("{member} AFK: {reason}", member="@Andi", reason="makan")
    assert out == "@Andi AFK: makan"


def test_render_template_ignores_unknown_braces_and_none():
    out = a.render_template("{member} {unknown}", member="Budi")
    assert out == "Budi {unknown}"
    assert a.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in a.AFK_SPECS.items():
        assert a.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    a.save_text("set", text="{member} pergi: {reason}")
    assert a.load_text("set") == "{member} pergi: {reason}"


def test_save_load_isolated_per_kind(db):
    a.save_text("mention", text="{name} AFK {durasi}")
    assert a.load_text("mention") == "{name} AFK {durasi}"
    # jenis lain tetap default
    assert a.load_text("set") == a.DEFAULT_SET
    assert a.load_text("back") == a.DEFAULT_BACK
    assert a.load_text("already") == a.DEFAULT_ALREADY


def test_empty_string_resets_to_default(db):
    a.save_text("back", text="custom")
    a.save_text("back", text="")
    assert a.load_text("back") == a.DEFAULT_BACK


def test_render_text_default_substitution(db):
    out = a.render_text("set", member="@Citra", reason="tidur")
    assert "@Citra" in out and "tidur" in out
    assert "{member}" not in out and "{reason}" not in out


def test_render_text_custom_substitution(db):
    a.save_text("mention", text="**{name}** AFK: {reason} ({durasi})")
    out = a.render_text("mention", name="Dewi", reason="rapat", durasi="10 menit lalu")
    assert out == "**Dewi** AFK: rapat (10 menit lalu)"
