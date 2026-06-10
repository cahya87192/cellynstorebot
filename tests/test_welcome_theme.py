"""Test logika tema Kartu Notifikasi (utils/welcome_theme.py).

Mencakup multi-kind (welcome/boost/leave), validasi/clamp, warna bingkai
(ring_color), dan kompatibilitas API lama (tanpa argumen kind = welcome).
Murni — pakai fixture `db`.
"""
import pytest

from utils import welcome_theme as t


def test_kinds_and_keys_distinct():
    assert set(t.KINDS) == {"welcome", "boost", "leave"}
    keys = {t.THEME_KEYS[k] for k in t.KINDS}
    assert len(keys) == 3                       # tiap jenis key berbeda
    assert t.THEME_KEYS["welcome"] == "welcome_card_theme"  # kompatibilitas data lama
    assert t.THEME_KEY == "welcome_card_theme"  # alias lama


def test_canvas_aliases():
    assert t.CANVAS["welcome"] == (t.WELCOME_W, t.WELCOME_H)


def test_default_theme_per_kind_text_and_ring():
    for kind in t.KINDS:
        th = t.default_theme(kind)
        assert th["enabled"] is False
        assert th["panel_opacity"] == 140
        assert th["elements"]["avatar"]["type"] == "avatar"
        # ring_color = default jenis ybs, ter-validasi (#RRGGBB uppercase).
        ring = th["elements"]["avatar"]["ring_color"]
        assert ring == t._valid_hex(t.RING_DEFAULTS[kind], "#000000")
        # title & subtitle punya teks; name & membercount dinamis (tanpa teks).
        assert th["elements"]["title"]["text"]
        assert th["elements"]["subtitle"]["text"]
        assert "text" not in th["elements"]["name"]
        assert "text" not in th["elements"]["membercount"]


def test_default_no_kind_is_welcome():
    assert t.default_theme() == t.default_theme("welcome")
    assert t.merge_theme(None) == t.merge_theme(None, "welcome")


def test_unknown_kind_falls_back_to_welcome():
    assert t.default_theme("bogus") == t.default_theme("welcome")


def test_merge_clamps_and_validates():
    m = t.merge_theme({
        "enabled": True,
        "panel_opacity": 999,
        "font_file": "  myfont.ttf  ",
        "elements": {
            "title": {"x": -50, "y": 5000, "size": 999, "color": "zzz", "show": False},
            "avatar": {"size": 9999, "ring_color": "nothex"},
        },
    }, "boost")
    assert m["enabled"] is True
    assert m["panel_opacity"] == 255
    assert m["font_file"] == "  myfont.ttf  "
    assert m["elements"]["title"]["x"] == 0
    assert m["elements"]["title"]["y"] == t.CANVAS["boost"][1]
    assert m["elements"]["title"]["size"] == 120        # clamp atas
    assert m["elements"]["title"]["color"] == "#FFFFFF"  # invalid -> default jenis
    assert m["elements"]["title"]["show"] is False
    assert m["elements"]["avatar"]["size"] == 320        # clamp atas
    # ring_color invalid -> fallback ke default boost.
    assert m["elements"]["avatar"]["ring_color"] == t._valid_hex(t.RING_DEFAULTS["boost"], "#000000")


def test_ring_color_valid_value_kept():
    m = t.merge_theme({"elements": {"avatar": {"ring_color": "f0a"}}}, "leave")
    assert m["elements"]["avatar"]["ring_color"] == "#F0A"
    m2 = t.merge_theme({"elements": {"avatar": {"ring_color": "#123456"}}}, "welcome")
    assert m2["elements"]["avatar"]["ring_color"] == "#123456"


def test_hex_to_rgb():
    assert t.hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert t.hex_to_rgb("#000000") == (0, 0, 0)
    assert t.hex_to_rgb("#abc") == (170, 187, 204)
    assert t.hex_to_rgb("bukanwarna") == (255, 255, 255)


def test_text_trimmed_to_max_len():
    long = "x" * 200
    m = t.merge_theme({"elements": {"title": {"text": "  " + long + "  "}}}, "welcome")
    assert m["elements"]["title"]["text"] == "x" * t.MAX_TEXT_LEN


def test_save_and_load_round_trip_per_kind(db):
    custom = t.default_theme("boost")
    custom["enabled"] = True
    custom["elements"]["avatar"]["ring_color"] = "#FF0000"
    custom["elements"]["title"]["x"] = 321
    custom["panel_opacity"] = 200
    t.save_theme(custom, "boost")
    loaded = t.load_theme("boost")
    assert loaded["enabled"] is True
    assert loaded["elements"]["avatar"]["ring_color"] == "#FF0000"
    assert loaded["elements"]["title"]["x"] == 321
    assert loaded["panel_opacity"] == 200


def test_kinds_isolated_in_db(db):
    t.save_theme({"enabled": True, "elements": {"avatar": {"ring_color": "#111111"}}}, "welcome")
    t.save_theme({"enabled": False, "elements": {"avatar": {"ring_color": "#222222"}}}, "leave")
    w = t.load_theme("welcome")
    l = t.load_theme("leave")
    b = t.load_theme("boost")  # belum pernah disimpan -> default
    assert w["enabled"] is True and w["elements"]["avatar"]["ring_color"] == "#111111"
    assert l["enabled"] is False and l["elements"]["avatar"]["ring_color"] == "#222222"
    assert b == t.default_theme("boost")


def test_load_default_when_unset(db):
    assert t.load_theme("welcome") == t.default_theme("welcome")


def test_backward_compat_no_kind_save_load(db):
    th = t.default_theme()
    th["panel_opacity"] = 99
    t.save_theme(th)            # tanpa kind -> welcome
    assert t.load_theme()["panel_opacity"] == 99            # tanpa kind -> welcome
    assert t.load_theme("welcome")["panel_opacity"] == 99


def test_element_order_and_labels():
    assert t.ELEMENT_ORDER == ["avatar", "title", "name", "subtitle", "membercount"]
    labels = dict(t.element_labels("welcome"))
    assert set(labels) == set(t.ELEMENT_ORDER)
    assert dict(t.ELEMENT_LABELS) == labels
