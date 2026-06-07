"""Logika murni Kartu Profil Member (tanpa dependensi discord / PIL).

Berisi:
  - aturan XP & level (gampang dites & di-tweak), dan
  - agregasi statistik member dari DB (transaction_log, manual_spending, reviews).

Rendering gambar (PNG) ada di cogs/profile.py. Dipisah supaya logikanya bisa
diuji tanpa Discord maupun Pillow.

ATURAN XP (ditetapkan owner via Kiro, bisa diubah di konstanta bawah):
  - 1 XP per Rp 1.000 yang dibelanjakan (akumulasi seumur transaksi),
  - +50 XP per transaksi selesai,
  - +30 XP per ulasan/rating yang diberikan member.

TIER berdasarkan level:
  - Bronze   : Lv 1-4
  - Silver   : Lv 5-9
  - Gold     : Lv 10-19
  - Diamond  : Lv 20+
"""

import datetime

from utils.db import get_conn

# ── Konstanta XP (silakan tweak) ────────────────────────────────────────────────
XP_PER_RUPIAH_DIVISOR = 1000   # 1 XP tiap Rp 1.000
XP_PER_ORDER = 50
XP_PER_REVIEW = 30

# Biaya XP dari level L ke L+1 = LEVEL_BASE + (L-1) * LEVEL_STEP.
LEVEL_BASE = 1000
LEVEL_STEP = 500

TIERS = [
    (20, "Diamond"),
    (10, "Gold"),
    (5, "Silver"),
    (1, "Bronze"),
]


def tier_for_level(level: int) -> str:
    for min_lv, name in TIERS:
        if level >= min_lv:
            return name
    return "Bronze"


def _level_cost(level: int) -> int:
    """XP yang dibutuhkan untuk naik DARI `level` ke `level+1`."""
    return LEVEL_BASE + (level - 1) * LEVEL_STEP


def compute_xp(total_spent: int, total_orders: int, total_reviews: int) -> int:
    """Total XP dari belanja + jumlah order + jumlah ulasan."""
    spent = max(0, int(total_spent or 0))
    orders = max(0, int(total_orders or 0))
    reviews = max(0, int(total_reviews or 0))
    return (spent // XP_PER_RUPIAH_DIVISOR
            + orders * XP_PER_ORDER
            + reviews * XP_PER_REVIEW)


def level_from_xp(total_xp: int) -> dict:
    """Hitung level & progres dari total XP.

    Return dict: level, tier, xp_total, xp_into_level (XP di dalam level saat ini),
    xp_for_next (XP yang dibutuhkan untuk naik level), xp_remaining.
    """
    total_xp = max(0, int(total_xp or 0))
    level = 1
    remaining = total_xp
    while True:
        cost = _level_cost(level)
        if remaining < cost:
            break
        remaining -= cost
        level += 1
        if level > 999:  # pengaman
            break
    cost_next = _level_cost(level)
    return {
        "level": level,
        "tier": tier_for_level(level),
        "xp_total": total_xp,
        "xp_into_level": remaining,
        "xp_for_next": cost_next,
        "xp_remaining": max(0, cost_next - remaining),
    }


def next_tier_info(level: int):
    """(nama_tier_berikut, level_mulai) tier berikutnya, atau (None, None) bila
    sudah tier tertinggi."""
    ladder = sorted(TIERS, key=lambda x: x[0])  # Bronze..Diamond
    for min_lv, name in ladder:
        if min_lv > level:
            return name, min_lv
    return None, None



def _month_bounds(when=None):
    now = when or datetime.datetime.now(datetime.timezone.utc)
    start = f"{now.year:04d}-{now.month:02d}-01"
    if now.month == 12:
        end = f"{now.year + 1:04d}-01-01"
    else:
        end = f"{now.year:04d}-{now.month + 1:02d}-01"
    return start, end


def get_member_profile(user_id: int, when=None) -> dict:
    """Agregasi statistik member untuk kartu profil.

    Mengembalikan dict berisi: total_orders, total_spent (seumur), spent_month
    (bulan berjalan), total_reviews, first_order (ISO str / None), plus hasil
    level_from_xp(...) yang sudah digabung.
    """
    conn = get_conn()
    c = conn.cursor()
    month_start, month_end = _month_bounds(when)

    # Total order & belanja seumur hidup (transaction_log).
    row = c.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(nominal),0) AS total, MIN(closed_at) AS first "
        "FROM transaction_log WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    total_orders = row["n"] or 0
    total_spent_tx = row["total"] or 0
    first_order = row["first"]

    # Belanja bulan berjalan (transaction_log + manual_spending).
    spent_month = c.execute(
        "SELECT COALESCE(SUM(nominal),0) FROM transaction_log "
        "WHERE user_id = ? AND closed_at >= ? AND closed_at < ?",
        (user_id, month_start, month_end),
    ).fetchone()[0] or 0
    try:
        ms = c.execute(
            "SELECT COALESCE(SUM(nominal),0) FROM manual_spending "
            "WHERE user_id = ? AND added_at >= ? AND added_at < ?",
            (user_id, month_start, month_end),
        ).fetchone()[0] or 0
    except Exception:
        ms = 0
    spent_month += ms

    # Tambahan belanja manual seumur (untuk XP) + total spent gabungan.
    try:
        ms_total = c.execute(
            "SELECT COALESCE(SUM(nominal),0) FROM manual_spending WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0] or 0
    except Exception:
        ms_total = 0
    total_spent = total_spent_tx + ms_total

    # Jumlah ulasan/rating yang diberikan member.
    try:
        total_reviews = c.execute(
            "SELECT COUNT(*) FROM reviews WHERE user_id = ? AND rating IS NOT NULL",
            (user_id,),
        ).fetchone()[0] or 0
    except Exception:
        total_reviews = 0
    conn.close()

    xp = compute_xp(total_spent, total_orders, total_reviews)
    data = {
        "user_id": user_id,
        "total_orders": total_orders,
        "total_spent": total_spent,
        "spent_month": spent_month,
        "total_reviews": total_reviews,
        "first_order": first_order,
    }
    data.update(level_from_xp(xp))
    nt_name, nt_level = next_tier_info(data["level"])
    data["next_tier"] = nt_name
    data["next_tier_level"] = nt_level
    return data
