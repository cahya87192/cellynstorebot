"""Test logika tema Kartu Badge/Achievement (utils/achievement_theme.py) — murni."""
from utils import achievement_theme as t


def test_default_and_merge_none():
    th = t.merge_theme(None)
    assert th["elements"]["name"]["x"] == 246
    assert th["panel_opacity"] == 150
    assert th["font_file"] is None
    assert th["elements"]["title"]["text"] == t.DEFAULT_TITLE


def test_merge_clamps_and_validates():
    m = t.merge_theme({
        "panel_opacity": 999,
        "font_file": "  myfont.ttf  ",
        "elements": {
            "name": {"x": -50, "y": 5000, "size": 999, "color": "zzz", "show": False},
            "avatar": {"size": 9999},
            "title": {"size": 2},
        },
    })
    assert m["panel_opacity"] == 255
    assert m["font_file"] == "  myfont.ttf  "  # disimpan apa adanya (string non-kosong)
    assert m["elements"]["name"]["x"] == 0 and m["elements"]["name"]["y"] == t.ACH_H
    assert m["elements"]["name"]["size"] == 120          # clamp atas
    assert m["elements"]["name"]["color"] == "#FFFFFF"   # invalid -> default
    assert m["elements"]["name"]["show"] is False
    assert m["elements"]["avatar"]["size"] == 300        # clamp atas
    assert m["elements"]["title"]["size"] == 8           # clamp bawah


def test_title_text_custom_and_trim():
    m = t.merge_theme({"elements": {"title": {"text": "  Selamat!  "}}})
    assert m["elements"]["title"]["text"] == "Selamat!"
    # teks kosong/invalid -> kembali ke default
    m2 = t.merge_theme({"elements": {"title": {"text": "   "}}})
    assert m2["elements"]["title"]["text"] == t.DEFAULT_TITLE
    m3 = t.merge_theme({"elements": {"title": {"text": 12345}}})
    assert m3["elements"]["title"]["text"] == t.DEFAULT_TITLE


def test_title_text_max_len():
    long_text = "X" * 200
    m = t.merge_theme({"elements": {"title": {"text": long_text}}})
    assert len(m["elements"]["title"]["text"]) == t.MAX_TITLE_LEN


def test_hex_to_rgb():
    assert t.hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert t.hex_to_rgb("#000000") == (0, 0, 0)
    assert t.hex_to_rgb("#abc") == (170, 187, 204)
    assert t.hex_to_rgb("bukanwarna") == (255, 255, 255)  # fallback


def test_invalid_color_kept_3digit():
    m = t.merge_theme({"elements": {"badges": {"color": "f0a"}}})
    assert m["elements"]["badges"]["color"] == "#F0A"


def test_bad_json_string_returns_default():
    m = t.merge_theme("{not valid json")
    assert m["elements"]["title"]["text"] == t.DEFAULT_TITLE
    assert m["panel_opacity"] == 150


def test_save_and_load_round_trip(db):
    custom = t.default_theme()
    custom["elements"]["name"]["x"] = 123
    custom["elements"]["name"]["color"] = "#FF0000"
    custom["elements"]["title"]["text"] = "KEREN!"
    custom["panel_opacity"] = 200
    t.save_theme(custom)
    loaded = t.load_theme()
    assert loaded["elements"]["name"]["x"] == 123
    assert loaded["elements"]["name"]["color"] == "#FF0000"
    assert loaded["elements"]["title"]["text"] == "KEREN!"
    assert loaded["panel_opacity"] == 200
