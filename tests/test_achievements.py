"""Test logika murni sistem Achievement / Badge (utils/achievements.py).

Tidak menyentuh Discord/PIL. Memverifikasi badge bertingkat (tertinggi per
kategori) + daftar yang belum diraih.
"""
from utils import achievements as ach


def _names(badges):
    return [b["name"] for b in badges]


def test_empty_profile_no_badges():
    res = ach.compute_achievements({})
    assert res["earned"] == []
    # Semua tier dasar masih terkunci (4 belanja + 4 order + 3 ulasan + 2 tier).
    assert len(res["locked"]) == 13
    # Target terdekat tetap muncul.
    assert "Pelanggan Setia" in _names(res["locked"])
    assert "First Order" in _names(res["locked"])


def test_none_profile_is_safe():
    res = ach.compute_achievements(None)
    assert res["earned"] == []


def test_highest_tier_per_category_only():
    profile = {
        "total_spent": 1_500_000,   # >= Big Spender (1jt), < Juragan (5jt)
        "total_orders": 12,          # >= Repeat Buyer (10), < Pelanggan Emas (50)
        "total_reviews": 3,          # >= Suara Member (3)
        "tier": "Gold",
    }
    res = ach.compute_achievements(profile)
    earned = _names(res["earned"])
    # Hanya tier tertinggi per kategori.
    assert "Big Spender" in earned
    assert "Pelanggan Setia" not in earned   # tertutup oleh Big Spender
    assert "Repeat Buyer" in earned
    assert "Suara Member" in earned
    assert "Member Gold" in earned
    assert "Member Diamond" not in earned    # tier akun belum Diamond

    locked = _names(res["locked"])
    assert "Juragan" in locked
    assert "Pelanggan Emas" in locked
    assert "Member Diamond" in locked


def test_top_tier_everything():
    profile = {
        "total_spent": 20_000_000,
        "total_orders": 200,
        "total_reviews": 100,
        "tier": "Diamond",
    }
    res = ach.compute_achievements(profile)
    earned = _names(res["earned"])
    assert earned == ["Sultan", "Legenda", "Kritikus", "Member Diamond"]
    assert res["locked"] == []


def test_first_order_threshold():
    res = ach.compute_achievements({"total_orders": 1, "tier": "Bronze"})
    assert "First Order" in _names(res["earned"])


def test_earned_badge_names_helper():
    profile = {"total_spent": 300_000, "total_orders": 0, "total_reviews": 0,
               "tier": "Silver"}
    names = ach.earned_badge_names(profile)
    assert names == ["Pelanggan Setia"]   # tier Silver tak berbadge


def test_descriptions_present():
    res = ach.compute_achievements({"total_spent": 250_000})
    spend = next(b for b in res["earned"] if b["name"] == "Pelanggan Setia")
    assert "Rp 250.000" in spend["desc"]
