"""Test logika tema Kartu Profil (utils/profile_theme.py) — murni, pakai fixture db."""
from utils import profile_theme as t


def test_default_and_merge_none():
    th = t.merge_theme(None)
    assert th["elements"]["name"]["x"] == 256
    assert th["panel_opacity"] == 120
    assert th["font_file"] is None


def test_merge_clamps_and_validates():
    m = t.merge_theme({
        "panel_opacity": 999,
        "font_file": "  myfont.ttf  ",
        "elements": {
            "name": {"x": -50, "y": 5000, "size": 999, "color": "zzz", "show": False},
            "avatar": {"size": 9999},
            "xpbar": {"w": 99999, "h": 1},
        },
    })
    assert m["panel_opacity"] == 255
    assert m["font_file"] == "  myfont.ttf  "  # disimpan apa adanya (string non-kosong)
    assert m["elements"]["name"]["x"] == 0 and m["elements"]["name"]["y"] == t.CARD_H
    assert m["elements"]["name"]["size"] == 120          # clamp atas
    assert m["elements"]["name"]["color"] == "#FFFFFF"   # invalid -> default
    assert m["elements"]["name"]["show"] is False
    assert m["elements"]["avatar"]["size"] == 300        # clamp atas
    assert m["elements"]["xpbar"]["w"] == t.CARD_W and m["elements"]["xpbar"]["h"] == 6


def test_hex_to_rgb():
    assert t.hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert t.hex_to_rgb("#000000") == (0, 0, 0)
    assert t.hex_to_rgb("#abc") == (170, 187, 204)
    assert t.hex_to_rgb("bukanwarna") == (255, 255, 255)  # fallback


def test_save_and_load_round_trip(db):
    custom = t.default_theme()
    custom["elements"]["name"]["x"] = 123
    custom["elements"]["name"]["color"] = "#FF0000"
    custom["panel_opacity"] = 200
    t.save_theme(custom)
    loaded = t.load_theme()
    assert loaded["elements"]["name"]["x"] == 123
    assert loaded["elements"]["name"]["color"] == "#FF0000"
    assert loaded["panel_opacity"] == 200


def test_invalid_color_kept_3digit():
    m = t.merge_theme({"elements": {"tier": {"color": "f0a"}}})
    assert m["elements"]["tier"]["color"] == "#F0A"
