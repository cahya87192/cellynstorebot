"""Test warna bingkai (ring_color) avatar untuk kartu Profil & Badge.

ring_color None/""/invalid = "otomatis" (render memakai warna aksen tier);
string hex valid = override warna ring. Backward compatible: data lama tanpa
ring_color tetap None (auto). Murni — pakai fixture `db`.
"""
import pytest

from utils import profile_theme as pt
from utils import achievement_theme as at


@pytest.mark.parametrize("mod", [pt, at])
def test_default_avatar_ring_is_auto(mod):
    av = mod.default_theme()["elements"]["avatar"]
    assert "ring_color" in av
    assert av["ring_color"] is None          # None = otomatis (warna tier)


@pytest.mark.parametrize("mod", [pt, at])
def test_custom_ring_color_kept(mod):
    m = mod.merge_theme({"elements": {"avatar": {"ring_color": "#1a2b3c"}}})
    assert m["elements"]["avatar"]["ring_color"] == "#1A2B3C"
    m2 = mod.merge_theme({"elements": {"avatar": {"ring_color": "f0a"}}})
    assert m2["elements"]["avatar"]["ring_color"] == "#F0A"


@pytest.mark.parametrize("mod", [pt, at])
def test_invalid_or_empty_ring_becomes_auto(mod):
    assert mod.merge_theme({"elements": {"avatar": {"ring_color": "zzz"}}})["elements"]["avatar"]["ring_color"] is None
    assert mod.merge_theme({"elements": {"avatar": {"ring_color": ""}}})["elements"]["avatar"]["ring_color"] is None
    assert mod.merge_theme({"elements": {"avatar": {"ring_color": None}}})["elements"]["avatar"]["ring_color"] is None


@pytest.mark.parametrize("mod", [pt, at])
def test_old_data_without_ring_color_is_auto(mod):
    # Data tema lama tidak punya field ring_color sama sekali -> tetap auto.
    m = mod.merge_theme({"elements": {"avatar": {"x": 10, "y": 20, "size": 120}}})
    assert m["elements"]["avatar"]["ring_color"] is None
    assert m["elements"]["avatar"]["size"] == 120


@pytest.mark.parametrize("mod", [pt, at])
def test_ring_color_size_independent(mod):
    # ring_color tidak mengganggu validasi size avatar.
    m = mod.merge_theme({"elements": {"avatar": {"size": 9999, "ring_color": "#00FF00"}}})
    assert m["elements"]["avatar"]["size"] == 300        # clamp atas
    assert m["elements"]["avatar"]["ring_color"] == "#00FF00"


@pytest.mark.parametrize("mod", [pt, at])
def test_ring_color_persist_round_trip(mod, db):
    th = mod.default_theme()
    th["elements"]["avatar"]["ring_color"] = "#FF00AA"
    mod.save_theme(th)
    assert mod.load_theme()["elements"]["avatar"]["ring_color"] == "#FF00AA"
    # set kembali ke auto
    th2 = mod.load_theme()
    th2["elements"]["avatar"]["ring_color"] = None
    mod.save_theme(th2)
    assert mod.load_theme()["elements"]["avatar"]["ring_color"] is None
