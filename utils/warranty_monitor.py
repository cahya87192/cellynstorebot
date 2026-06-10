"""Monitor garansi untuk admin panel.

Menggabungkan transaksi bergaransi (reviews status rated/published) dengan
durasi garansi (override manual > durasi langganan dari nama item >
WARRANTY_DEFAULT_DAYS) untuk menghitung sisa masa garansi tiap pembelian,
lalu mengklasifikasikannya: aktif / akan habis / habis / tanpa batas.

Logika murni (lewat utils.reviews + utils.subscription) supaya gampang diuji
tanpa Flask/Discord. Halaman /warranty (admin_insights.py) tinggal merender
hasilnya.
"""
from utils import reviews as rv
from utils import subscription as sub

# Ambang "akan segera habis" (hari).
SOON_DAYS = 7

# Urutan tampil per status (paling mendesak dulu).
_STATUS_RANK = {"soon": 0, "active": 1, "unlimited": 2, "expired": 3}


def _resolve_default_days(default_days="__auto__"):
    """Default hari garansi: argumen eksplisit, atau dari config (fallback 7)."""
    if default_days != "__auto__":
        return default_days
    try:
        from utils.config import WARRANTY_DEFAULT_DAYS
        return WARRANTY_DEFAULT_DAYS
    except Exception:
        return 7


def classify(remaining, soon_days=SOON_DAYS):
    """Klasifikasi status garansi dari sisa hari.

    None -> 'unlimited' (durasi tak terbaca & tanpa default), <=0 -> 'expired',
    <= soon_days -> 'soon', selain itu 'active'.
    """
    if remaining is None:
        return "unlimited"
    if remaining <= 0:
        return "expired"
    if remaining <= soon_days:
        return "soon"
    return "active"


def _sort_key(r):
    rank = _STATUS_RANK.get(r["status"], 9)
    rem = r["remaining"]
    if rem is None:
        sub_key = 0
    elif r["status"] == "expired":
        # paling baru habis (mendekati 0) lebih dulu.
        sub_key = -rem
    else:
        sub_key = rem
    return (rank, sub_key)


def list_warranties(now=None, default_days="__auto__", soon_days=SOON_DAYS, status=None):
    """Daftar semua garansi (lintas member) beserta sisa hari & status.

    Tiap item: {tx_id, user_id, layanan, item, nominal, rating, rated_at,
    warranty_days, remaining, status, manual}. Diurutkan paling mendesak dulu
    (akan habis -> aktif -> tanpa batas -> habis). Bila `status` diberikan,
    hanya kembalikan item dengan status itu.
    """
    dd = _resolve_default_days(default_days)
    out = []
    for t in rv.get_all_warranty_transactions():
        start = t.get("rated_at") or t.get("closed_at")
        remaining = sub.days_remaining(
            start, t.get("item"), now=now,
            default_days=dd, override_days=t.get("warranty_days"),
        )
        cls = classify(remaining, soon_days)
        out.append({
            "tx_id": t.get("tx_id"),
            "user_id": t.get("user_id"),
            "layanan": t.get("layanan"),
            "item": t.get("item"),
            "nominal": t.get("nominal") or 0,
            "rating": t.get("rating") or 0,
            "rated_at": t.get("rated_at"),
            "warranty_days": t.get("warranty_days"),
            "remaining": remaining,
            "status": cls,
            "manual": t.get("warranty_days") is not None,
        })
    out.sort(key=_sort_key)
    if status:
        out = [r for r in out if r["status"] == status]
    return out


def summary(now=None, default_days="__auto__", soon_days=SOON_DAYS):
    """Ringkasan jumlah per status: {total, active, soon, expired, unlimited}."""
    items = list_warranties(now=now, default_days=default_days, soon_days=soon_days)
    s = {"total": len(items), "active": 0, "soon": 0, "expired": 0, "unlimited": 0}
    for r in items:
        if r["status"] in s:
            s[r["status"]] += 1
    return s
