"""Test override emoji katalog 'lainnya' (utils/catalog_emoji_settings.py) — murni."""
from utils import catalog_emoji_settings as es


def test_clean_emoji_unicode_and_custom():
    assert es.clean_emoji("\U0001F3AE") == "\U0001F3AE"      # 🎮
    assert es.clean_emoji("  \U0001F5C2  ") == "\U0001F5C2"  # trim
    assert es.clean_emoji("<:abc:123>") == "<:abc:123>"
    assert es.clean_emoji("<a:boost:456>") == "<a:boost:456>"


def test_clean_emoji_rejects_invalid():
    assert es.clean_emoji("") is None
    assert es.clean_emoji("   ") is None
    assert es.clean_emoji(None) is None
    assert es.clean_emoji(123) is None
    assert es.clean_emoji("hello") is None          # teks biasa (huruf ASCII)
    assert es.clean_emoji("ab") is None             # huruf ASCII
    assert es.clean_emoji("\U0001F3AE x") is None   # ada spasi
    assert es.clean_emoji("<:bad emoji:1>") is None  # custom tak valid (spasi)
    assert es.clean_emoji("x" * 100) is None         # terlalu panjang


def test_merge_overrides_structure_and_filter():
    raw = {
        "groups": {
            "AI": "<:ai:1>",
            "GAMING": "\U0001F3AE",
            "BAD": "teks",          # invalid -> dibuang
            "  ": "<:x:1>",          # nama kosong -> dibuang
        },
        "categories": {
            "CHATGPT": "<:gpt:9>",
            "X": "not emoji",        # invalid -> dibuang
        },
        "asing": {"Y": "<:y:1>"},    # section asing diabaikan
    }
    m = es.merge_overrides(raw)
    assert m["groups"]["AI"] == "<:ai:1>"
    assert m["groups"]["GAMING"] == "\U0001F3AE"
    assert "BAD" not in m["groups"]
    assert "  " not in m["groups"]
    assert m["categories"]["CHATGPT"] == "<:gpt:9>"
    assert "X" not in m["categories"]
    assert set(m.keys()) == {"groups", "categories"}


def test_merge_overrides_bad_input():
    assert es.merge_overrides(None) == {"groups": {}, "categories": {}}
    assert es.merge_overrides("bukan json") == {"groups": {}, "categories": {}}
    assert es.merge_overrides(123) == {"groups": {}, "categories": {}}
    import json
    assert es.merge_overrides(json.dumps({"groups": {"AI": "\U0001F916"}})) == {
        "groups": {"AI": "\U0001F916"}, "categories": {}}


def test_effective_map_override_wins():
    static = {"AI": "<:ai_default:1>", "GAMING": "\U0001F3AE"}
    ov = {"AI": "\U0001F916"}
    eff = es.effective_map(static, ov)
    assert eff["AI"] == "\U0001F916"          # override menang
    assert eff["GAMING"] == "\U0001F3AE"      # tak di-override -> default
    # tidak mengubah dict asli
    assert static["AI"] == "<:ai_default:1>"


def test_effective_map_none_override():
    static = {"AI": "x"}
    assert es.effective_map(static, None) == {"AI": "x"}
    assert es.effective_map(None, None) == {}


def test_save_and_load_round_trip(db):
    es.save_overrides({
        "groups": {"AI": "\U0001F916", "BAD": "teks"},
        "categories": {"CHATGPT": "<:gpt:9>"},
    })
    loaded = es.load_overrides()
    assert loaded["groups"] == {"AI": "\U0001F916"}
    assert loaded["categories"] == {"CHATGPT": "<:gpt:9>"}


def test_save_empty_resets(db):
    es.save_overrides({"groups": {"AI": "\U0001F916"}})
    assert es.load_overrides()["groups"] == {"AI": "\U0001F916"}
    es.save_overrides({})
    assert es.load_overrides() == {"groups": {}, "categories": {}}
