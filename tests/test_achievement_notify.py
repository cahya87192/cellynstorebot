"""Test logika notifikasi badge baru.

- utils/achievements.newly_earned: diff badge earned vs yang sudah diumumkan (murni).
- utils/achievement_state: persistensi badge yang sudah diumumkan (pakai fixture db).
"""
from utils import achievements as ach
from utils import achievement_state as achstate


# ── newly_earned (murni) ──────────────────────────────────────────────────────
def test_newly_earned_all_when_nothing_announced():
    profile = {"total_spent": 300_000, "total_orders": 1, "total_reviews": 0,
               "tier": "Bronze"}
    new = ach.newly_earned(profile, [])
    names = [b["name"] for b in new]
    assert "Pelanggan Setia" in names
    assert "First Order" in names


def test_newly_earned_skips_already_announced():
    profile = {"total_spent": 300_000, "total_orders": 1, "total_reviews": 0,
               "tier": "Bronze"}
    new = ach.newly_earned(profile, ["Pelanggan Setia"])
    names = [b["name"] for b in new]
    assert "Pelanggan Setia" not in names
    assert "First Order" in names


def test_newly_earned_empty_when_all_announced():
    profile = {"total_spent": 300_000, "total_orders": 1, "tier": "Bronze"}
    new = ach.newly_earned(profile, ["Pelanggan Setia", "First Order"])
    assert new == []


def test_newly_earned_none_profile_safe():
    assert ach.newly_earned(None, []) == []


# ── achievement_state (DB) ────────────────────────────────────────────────────
def test_announced_empty_initially(db):
    assert achstate.get_announced(123) == set()


def test_mark_and_get_announced(db):
    achstate.mark_announced(123, ["Sultan", "Legenda"])
    assert achstate.get_announced(123) == {"Sultan", "Legenda"}


def test_mark_announced_merges(db):
    achstate.mark_announced(123, ["Sultan"])
    achstate.mark_announced(123, ["Legenda", "Sultan"])
    assert achstate.get_announced(123) == {"Sultan", "Legenda"}


def test_mark_announced_per_user_isolated(db):
    achstate.mark_announced(1, ["Sultan"])
    achstate.mark_announced(2, ["Kritikus"])
    assert achstate.get_announced(1) == {"Sultan"}
    assert achstate.get_announced(2) == {"Kritikus"}


def test_mark_announced_empty_noop(db):
    achstate.mark_announced(5, [])
    assert achstate.get_announced(5) == set()


def test_full_flow_no_double_announce(db):
    """Simulasi: badge yang sudah diumumkan tak muncul lagi di pengecekan berikut."""
    profile = {"total_spent": 1_000_000, "total_orders": 10, "tier": "Bronze"}
    first = ach.newly_earned(profile, achstate.get_announced(77))
    achstate.mark_announced(77, [b["name"] for b in first])
    # Cek lagi tanpa perubahan stat -> tidak ada badge baru.
    second = ach.newly_earned(profile, achstate.get_announced(77))
    assert second == []
