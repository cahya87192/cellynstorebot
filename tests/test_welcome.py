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



# ── Pesan boost & leave (generalisasi render_pair / load_texts) ──────────────────

def test_msg_specs_has_all_kinds():
    assert set(w.MSG_SPECS) == {"welcome", "boost", "leave"}
    for spec in w.MSG_SPECS.values():
        assert spec["title_key"] and spec["desc_key"]
        assert spec["default_title"] and spec["default_desc"]


def test_render_template_multiple_kwargs():
    out = w.render_template("{member} keluar setelah {durasi} di {store}",
                            member="Andi", durasi="3 bulan", store="CellynStore")
    assert out == "Andi keluar setelah 3 bulan di CellynStore"


def test_load_texts_default_per_kind(db):
    for kind in ("welcome", "boost", "leave"):
        title, desc = w.load_texts(kind)
        assert title == w.MSG_SPECS[kind]["default_title"]
        assert desc == w.MSG_SPECS[kind]["default_desc"]


def test_save_load_texts_isolated_per_kind(db):
    w.save_texts("boost", title="Boost {member}!", desc="Makasih {store}")
    # boost berubah, welcome & leave tetap default
    bt, bd = w.load_texts("boost")
    assert bt == "Boost {member}!" and bd == "Makasih {store}"
    assert w.load_texts("welcome")[0] == w.DEFAULT_WELCOME_TITLE
    assert w.load_texts("leave")[0] == w.DEFAULT_LEAVE_TITLE


def test_render_boost_default_and_custom(db):
    title, desc = w.render_boost("@Andi", "CellynStore")
    assert title == w.DEFAULT_BOOST_TITLE
    assert "@Andi" in desc and "CellynStore" in desc
    w.save_texts("boost", title="Wah {member}", desc="boost ke {store}")
    title, desc = w.render_boost("@Budi", "CellynStore")
    assert title == "Wah @Budi" and desc == "boost ke CellynStore"


def test_render_leave_default_substitution(db):
    title, desc = w.render_leave("Citra", "CellynStore", "2 tahun")
    assert "Citra" in title
    assert "2 tahun" in desc
    assert "{" not in title and "{durasi}" not in desc


def test_reset_kind_to_default(db):
    w.save_texts("leave", title="Bye {member}", desc="dah {durasi}")
    w.save_texts("leave", title="", desc="")
    title, desc = w.load_texts("leave")
    assert title == w.DEFAULT_LEAVE_TITLE and desc == w.DEFAULT_LEAVE_DESC



# ── DM sambutan (config multi-field + thumbnail + banner) ────────────────────────

def test_parse_dm_fields_tolerant():
    raw = '[{"name":"A","value":"x"},{"name":"","value":""},{"bad":1},"oops"]'
    out = w.parse_dm_fields(raw)
    # entry kosong & non-dict dibuang
    assert out == [{"name": "A", "value": "x"}]
    assert w.parse_dm_fields(None) is None
    assert w.parse_dm_fields("not-json") is None
    assert w.parse_dm_fields("{}") is None


def test_load_dm_config_defaults(db):
    cfg = w.load_dm_config()
    assert cfg["title"] == w.DEFAULT_DM_TITLE
    assert cfg["thumbnail"] == w.DEFAULT_DM_THUMBNAIL
    assert cfg["banner"] == ""  # default: tanpa banner
    assert len(cfg["fields"]) == len(w.DEFAULT_DM_FIELDS)


def test_save_and_load_dm_config(db):
    w.save_dm_config(title="Hai {member}", banner="https://x/banner.png",
                     fields=[{"name": "Info", "value": "halo {store}"}])
    cfg = w.load_dm_config()
    assert cfg["title"] == "Hai {member}"
    assert cfg["banner"] == "https://x/banner.png"
    assert cfg["fields"] == [{"name": "Info", "value": "halo {store}"}]
    # field teks lain tetap default
    assert cfg["desc"] == w.DEFAULT_DM_DESC


def test_save_dm_empty_fields_list_persists(db):
    w.save_dm_config(fields=[])
    assert w.load_dm_config()["fields"] == []


def test_render_dm_substitutes_placeholders(db):
    w.save_dm_config(title="Hai {member}", desc="Selamat datang di {store}",
                     banner="", thumbnail="https://x/t.png",
                     fields=[{"name": "Toko {store}", "value": "by {member}"}])
    out = w.render_dm("Andi", "CellynStore")
    assert out["title"] == "Hai Andi"
    assert out["desc"] == "Selamat datang di CellynStore"
    assert out["thumbnail"] == "https://x/t.png"
    assert out["banner"] is None  # kosong -> None (tanpa banner)
    assert out["fields"][0] == {"name": "Toko CellynStore", "value": "by Andi"}


def test_render_dm_banner_present(db):
    w.save_dm_config(banner="https://x/b.png")
    assert w.render_dm("A", "S")["banner"] == "https://x/b.png"


def test_reset_dm_config(db):
    w.save_dm_config(title="custom", banner="https://x/b.png", fields=[{"name": "n", "value": "v"}])
    w.reset_dm_config()
    cfg = w.load_dm_config()
    assert cfg["title"] == w.DEFAULT_DM_TITLE
    assert cfg["banner"] == ""
    assert len(cfg["fields"]) == len(w.DEFAULT_DM_FIELDS)
