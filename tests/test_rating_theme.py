"""Test logika tema Kartu Testimoni/Rating (utils/rating_theme.py).

Mencakup default, flag enabled, clamp/validasi, warna bingkai (ring_color),
trim teks judul, dan persist round-trip. Murni — pakai fixture `db`.
"""
from utils import rating_theme as t


def test_default_theme_shape():
    th = t.default_theme()
    assert th["enabled"] is False
    assert th["panel_opacity"] == 150
    assert th["font_file"] is None
    els = th["elements"]
    assert set(els) == {"avatar", "title", "name", "stars", "review"}
    assert els["avatar"]["type"] == "avatar"
    assert "ring_color" in els["avatar"]
    assert els["title"]["text"] == t.DEFAULT_TITLE
    # name/stars/review dinamis (tanpa teks statis)
    for k in ("name", "stars", "review"):
        assert "text" not in els[k]


def test_no_layanan_element():
    # Sesuai permintaan: kartu testimoni TANPA elemen nama layanan.
    assert "layanan" not in t.default_theme()["elements"]
    assert "service" not in t.default_theme()["elements"]


def test_ring_default_valid():
    ring = t.default_theme()["elements"]["avatar"]["ring_color"]
    assert ring == t._valid_hex(t.RING_DEFAULT, "#000000")


def test_merge_clamps_and_validates():
    m = t.merge_theme({
        "enabled": True,
        "panel_opacity": -10,
        "elements": {
            "review": {"x": 9999, "y": -5, "size": 999, "color": "nope"},
            "avatar": {"size": 5, "ring_color": "zzz"},
        },
    })
    assert m["enabled"] is True
    assert m["panel_opacity"] == 0
    assert m["elements"]["review"]["x"] == t.RATING_W
    assert m["elements"]["review"]["y"] == 0
    assert m["elements"]["review"]["size"] == 120
    assert m["elements"]["review"]["color"] == "#E2E4EC"   # invalid -> default
    assert m["elements"]["avatar"]["size"] == 32           # clamp bawah
    assert m["elements"]["avatar"]["ring_color"] == t._valid_hex(t.RING_DEFAULT, "#000")


def test_ring_color_valid_kept():
    m = t.merge_theme({"elements": {"avatar": {"ring_color": "#1a2b3c"}}})
    assert m["elements"]["avatar"]["ring_color"] == "#1A2B3C"
    m2 = t.merge_theme({"elements": {"avatar": {"ring_color": "f0a"}}})
    assert m2["elements"]["avatar"]["ring_color"] == "#F0A"


def test_title_text_trimmed():
    m = t.merge_theme({"elements": {"title": {"text": "  " + "z" * 200 + "  "}}})
    assert m["elements"]["title"]["text"] == "z" * t.MAX_TEXT_LEN


def test_hex_to_rgb():
    assert t.hex_to_rgb("#FFC107") == (255, 193, 7)
    assert t.hex_to_rgb("#abc") == (170, 187, 204)
    assert t.hex_to_rgb("bukan") == (255, 255, 255)


def test_bad_json_returns_default():
    assert t.merge_theme("{tidak valid") == t.default_theme()
    assert t.merge_theme(None) == t.default_theme()


def test_save_load_round_trip(db):
    th = t.default_theme()
    th["enabled"] = True
    th["panel_opacity"] = 222
    th["elements"]["avatar"]["ring_color"] = "#00FF00"
    th["elements"]["title"]["text"] = "TESTIMONI KEREN"
    t.save_theme(th)
    loaded = t.load_theme()
    assert loaded["enabled"] is True
    assert loaded["panel_opacity"] == 222
    assert loaded["elements"]["avatar"]["ring_color"] == "#00FF00"
    assert loaded["elements"]["title"]["text"] == "TESTIMONI KEREN"


def test_load_default_when_unset(db):
    assert t.load_theme() == t.default_theme()
