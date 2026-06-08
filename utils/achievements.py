"""Sistem Achievement / Badge — logika murni (tanpa discord / PIL).

Menentukan badge yang diraih member dari statistik profil
(`utils.profile.get_member_profile`): total_spent, total_orders, total_reviews,
dan tier akun.

Badge BERTINGKAT: untuk tiap kategori hanya tier TERTINGGI yang sudah dicapai
yang ditampilkan sebagai "sudah diraih". Tier di atasnya menjadi target
berikutnya ("belum diraih"). Dipisah dari cog supaya bisa diuji tanpa Discord.
"""

# ── Tangga badge per kategori: daftar (nama, ambang) menaik ────────────────────
SPENDING_TIERS = [
    ("Pelanggan Setia", 250_000),
    ("Big Spender", 1_000_000),
    ("Juragan", 5_000_000),
    ("Sultan", 10_000_000),
]

ORDER_TIERS = [
    ("First Order", 1),
    ("Repeat Buyer", 10),
    ("Pelanggan Emas", 50),
    ("Legenda", 100),
]

REVIEW_TIERS = [
    ("Suara Member", 3),
    ("Reviewer Setia", 10),
    ("Kritikus", 25),
]

# Badge tier akun (berdasarkan tier dari utils.profile). Hanya Gold & Diamond
# yang berbadge.
TIER_BADGES = [
    ("Gold", "Member Gold"),
    ("Diamond", "Member Diamond"),
]

# Urutan tier akun untuk perbandingan.
TIER_ORDER = {"Bronze": 0, "Silver": 1, "Gold": 2, "Diamond": 3}


def _rupiah(n) -> str:
    try:
        return "Rp " + f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp 0"


def _spend_desc(threshold: int) -> str:
    return f"Belanja total {_rupiah(threshold)}"


def _order_desc(threshold: int) -> str:
    return "Transaksi pertama selesai" if threshold <= 1 else f"{threshold}x transaksi selesai"


def _review_desc(threshold: int) -> str:
    return f"Beri {threshold} ulasan"


def _badge(name, threshold, desc, category):
    return {"name": name, "threshold": threshold, "desc": desc, "category": category}


def _evaluate_ladder(tiers, value, desc_fn, category):
    """Kembalikan (badge_tertinggi_yang_diraih | None, list_badge_terkunci)."""
    earned = None
    locked = []
    for name, threshold in tiers:
        badge = _badge(name, threshold, desc_fn(threshold), category)
        if value >= threshold:
            earned = badge
        else:
            locked.append(badge)
    return earned, locked


def _evaluate_tier(tier):
    """Badge tier akun: kembalikan (badge_tertinggi | None, list_terkunci)."""
    order = TIER_ORDER.get(tier or "Bronze", 0)
    earned = None
    locked = []
    for tier_name, badge_name in TIER_BADGES:
        badge = _badge(badge_name, tier_name, f"Capai tier akun {tier_name}", "tier")
        if order >= TIER_ORDER[tier_name]:
            earned = badge
        else:
            locked.append(badge)
    return earned, locked


def compute_achievements(profile: dict) -> dict:
    """Hitung badge dari dict profil member.

    `profile` diharapkan punya key: total_spent, total_orders, total_reviews,
    tier (seperti output utils.profile.get_member_profile). Semua key opsional;
    nilai hilang dianggap 0 / Bronze.

    Return dict:
      - "earned": list badge tertinggi per kategori yang sudah diraih.
      - "locked": list badge yang belum diraih (target berikutnya), urut dari
        yang paling dekat dicapai.
    """
    profile = profile or {}
    spent = max(0, int(profile.get("total_spent") or 0))
    orders = max(0, int(profile.get("total_orders") or 0))
    reviews = max(0, int(profile.get("total_reviews") or 0))
    tier = profile.get("tier") or "Bronze"

    earned = []
    locked = []
    for value, tiers, desc_fn, category in [
        (spent, SPENDING_TIERS, _spend_desc, "belanja"),
        (orders, ORDER_TIERS, _order_desc, "order"),
        (reviews, REVIEW_TIERS, _review_desc, "ulasan"),
    ]:
        e, l = _evaluate_ladder(tiers, value, desc_fn, category)
        if e:
            earned.append(e)
        locked.extend(l)

    te, tl = _evaluate_tier(tier)
    if te:
        earned.append(te)
    locked.extend(tl)

    return {"earned": earned, "locked": locked}


def earned_badge_names(profile: dict) -> list:
    """Daftar nama badge yang sudah diraih (tertinggi per kategori)."""
    return [b["name"] for b in compute_achievements(profile)["earned"]]


def newly_earned(profile: dict, announced_names) -> list:
    """Badge yang diraih SEKARANG tapi BELUM pernah diumumkan.

    `announced_names`: iterable nama badge yang sudah pernah diumumkan ke member.
    Return list badge dict (urut sesuai earned) untuk badge yang baru. Dipakai
    sistem notifikasi badge agar tiap badge hanya diumumkan sekali.
    """
    announced = set(announced_names or [])
    return [b for b in compute_achievements(profile)["earned"]
            if b["name"] not in announced]
