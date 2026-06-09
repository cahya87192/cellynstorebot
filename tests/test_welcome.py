"""Unit test logika murni teks Welcome (utils/welcome.py).

Bagian Discord (cogs/welcome.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat template (fallback default) lewat bot_state.
"""
from utils import welcome as w


def test_render_template_replaces_placeholders():
    out = w.render_template("Halo {member}, di {store}! Member ke-{count}",
                            member="Andi", store="CellynStore", count=42)
    assert out == "Halo Andi, di CellynStore! Member ke-42"


def test_render_template_ignores_unknown_braces_and_none():
    # Brace asing dibiarkan apa adanya (tidak error seperti str.format).
    out = w.render_template("Halo {member} {unknown} {x}", member="Budi")
    assert out == "Halo Budi {unknown} {x}"
    assert w.render_template(None) == ""


def test_load_welcome_texts_default_when_unset(db):
    title, desc = w.load_welcome_texts()
    assert title == w.DEFAULT_WELCOME_TITLE
    assert desc == w.DEFAULT_WELCOME_DESC


def test_save_and_load_welcome_texts(db):
    w.save_welcome_texts(title="Selamat datang {member}!", desc="Isi {store}")
    title, desc = w.load_welcome_texts()
    assert title == "Selamat datang {member}!"
    assert desc == "Isi {store}"


def test_save_only_one_field_keeps_other(db):
    w.save_welcome_texts(title="Judul custom", desc="Desc custom")
    # Update hanya desc; title tidak boleh berubah.
    w.save_welcome_texts(desc="Desc baru")
    title, desc = w.load_welcome_texts()
    assert title == "Judul custom"
    assert desc == "Desc baru"


def test_empty_string_resets_to_default(db):
    w.save_welcome_texts(title="Custom", desc="Custom desc")
    # String kosong -> reset (hapus) -> kembali ke default.
    w.save_welcome_texts(title="", desc="")
    title, desc = w.load_welcome_texts()
    assert title == w.DEFAULT_WELCOME_TITLE
    assert desc == w.DEFAULT_WELCOME_DESC


def test_render_welcome_uses_custom_text(db):
    w.save_welcome_texts(title="Hai {member}", desc="Kamu member ke-{count} di {store}")
    title, desc = w.render_welcome("Citra", "CellynStore", 7)
    assert title == "Hai Citra"
    assert desc == "Kamu member ke-7 di CellynStore"


def test_render_welcome_default_substitution(db):
    title, desc = w.render_welcome("Dewi", "CellynStore", 99)
    # Default title memuat {member} & {store}; pastikan tersubstitusi.
    assert "Dewi" in title and "CellynStore" in title
    assert "ke-**99**" in desc
    assert "{" not in title  # tak ada placeholder tersisa di title
