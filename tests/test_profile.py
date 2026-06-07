"""Test logika murni Kartu Profil Member (utils/profile.py).

Fokus: XP, level, tier, progres, dan agregasi data dari DB (pakai fixture `db`).
Tidak menyentuh Pillow/discord.
"""
from utils import profile as p


def test_compute_xp_rules():
    # 1 XP per Rp1.000 + 50/order + 30/review
    assert p.compute_xp(0, 0, 0) == 0
    assert p.compute_xp(1000, 0, 0) == 1
    assert p.compute_xp(0, 1, 0) == 50
    assert p.compute_xp(0, 0, 1) == 30
    assert p.compute_xp(250000, 10, 3) == 250 + 500 + 90  # 840
    # negatif/None aman
    assert p.compute_xp(-5, None, None) == 0


def test_level_from_xp_progression():
    # Level 1 butuh 1000 XP untuk naik ke 2.
    lv1 = p.level_from_xp(0)
    assert lv1["level"] == 1 and lv1["tier"] == "Bronze"
    assert lv1["xp_for_next"] == 1000 and lv1["xp_into_level"] == 0
    # Tepat di ambang naik level.
    assert p.level_from_xp(1000)["level"] == 2
    # 1000 (L1->2) + 1500 (L2->3) = 2500 -> level 3
    assert p.level_from_xp(2500)["level"] == 3
    # progres parsial
    d = p.level_from_xp(1200)
    assert d["level"] == 2 and d["xp_into_level"] == 200
    assert d["xp_remaining"] == d["xp_for_next"] - 200


def test_tiers():
    assert p.tier_for_level(1) == "Bronze"
    assert p.tier_for_level(5) == "Silver"
    assert p.tier_for_level(10) == "Gold"
    assert p.tier_for_level(25) == "Diamond"


def test_next_tier_info():
    assert p.next_tier_info(1) == ("Silver", 5)
    assert p.next_tier_info(7) == ("Gold", 10)
    assert p.next_tier_info(12) == ("Diamond", 20)
    assert p.next_tier_info(30) == (None, None)


def test_get_member_profile_aggregates(db):
    uid = 4321
    # 3 transaksi: total 300.000, 3 order.
    db.log_transaction(layanan="robux", nominal=100000, item="A", user_id=uid)
    db.log_transaction(layanan="ml", nominal=120000, item="B", user_id=uid)
    db.log_transaction(layanan="gp", nominal=80000, item="C", user_id=uid)
    prof = p.get_member_profile(uid)
    assert prof["total_orders"] == 3
    assert prof["total_spent"] == 300000
    # XP = 300 (belanja) + 150 (3 order) + 0 review = 450 -> masih level 1
    assert prof["xp_total"] == 450
    assert prof["level"] == 1 and prof["tier"] == "Bronze"
    assert prof["spent_month"] >= 300000  # transaksi baru = bulan berjalan


def test_get_member_profile_empty(db):
    prof = p.get_member_profile(999999)
    assert prof["total_orders"] == 0
    assert prof["total_spent"] == 0
    assert prof["level"] == 1
    assert prof["xp_total"] == 0
