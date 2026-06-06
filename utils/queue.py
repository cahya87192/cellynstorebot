"""Logika murni sistem antrian tiket (tanpa dependensi discord).

Mengumpulkan tiket aktif dari semua cog layanan, menormalkannya ke bentuk
seragam, lalu mengurutkan & menghitung posisi antrian. Sengaja dipisah dari
cog supaya:
  - mudah diuji tanpa Discord, dan
  - bersifat READ-ONLY terhadap cog lain (tidak pernah mengubah tiket).

Konvensi tiket per-layanan berbeda-beda, jadi normalisasi dibuat toleran:
  - Midman  : member di "pihak1" (objek Member), admin di "admin"/"verified_by",
              "opened_at" berupa objek datetime.
  - JualBeli: member di "p1_id", "admin_id"/"status" menandai sudah diproses.
  - Lainnya : member di "user_id", "opened_at" berupa string ISO, dan sinyal
              proses lewat "admin_id"/"paid"/"fee_paid" bila ada.
"""

import datetime


# Nama class cog layanan -> label layanan (slug, selaras dengan utils.ticket_ui).
SERVICE_COGS = {
    "Midman": "midman",
    "RobuxStore": "robux",
    "MLStore": "ml",
    "GPStore": "gp",
    "JualBeli": "jualbeli",
    "Vilog": "vilog",
    "LainnyaStore": "lainnya",
}

# Status menunggu pada tiket jual-beli (sebelum admin setup).
_JB_WAITING_STATUS = "menunggu_admin"


def _as_datetime(value):
    """Konversi nilai opened_at (datetime / string ISO) -> datetime aware UTC."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        dt = value
    else:
        try:
            dt = datetime.datetime.fromisoformat(str(value))
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _member_id(ticket):
    """Ambil ID member pembuka tiket dari berbagai konvensi kunci."""
    if ticket.get("user_id"):
        return ticket["user_id"]
    if ticket.get("p1_id"):
        return ticket["p1_id"]
    p1 = ticket.get("pihak1")
    if p1 is not None:
        return getattr(p1, "id", None)
    return None


def _admin_id(ticket):
    """Ambil ID admin penanggung tiket (untuk ditampilkan 'diproses oleh').

    Toleran lintas-layanan: midman menyimpan objek Member di "admin" /
    "verified_by", layanan lain memakai "admin_id".
    """
    for key in ("admin", "verified_by"):
        obj = ticket.get(key)
        if obj is not None:
            aid = getattr(obj, "id", None) if not isinstance(obj, int) else obj
            if aid:
                return aid
    return ticket.get("admin_id") or ticket.get("verified_by_id")


def is_handling(ticket):
    """True bila tiket sudah ditangani admin / pembayaran terkonfirmasi.

    Best-effort lintas-layanan: tidak semua cog menyimpan penanda admin di
    memori, jadi kita pakai beberapa sinyal yang umum dipakai.
    """
    if ticket.get("admin") or ticket.get("admin_id") or ticket.get("verified_by"):
        return True
    if ticket.get("paid") or ticket.get("fee_paid"):
        return True
    status = ticket.get("status")
    if status and status != _JB_WAITING_STATUS:
        return True
    return False


def normalize_ticket(layanan, channel_id, ticket):
    """Bentuk seragam satu tiket untuk keperluan antrian."""
    return {
        "channel_id": channel_id,
        "layanan": layanan,
        "member_id": _member_id(ticket),
        "admin_id": _admin_id(ticket),
        "ticket_number": ticket.get("ticket_number") or 0,
        "opened_at": _as_datetime(ticket.get("opened_at")),
        "handling": is_handling(ticket),
    }


def collect_tickets(bot, guild=None):
    """Kumpulkan tiket aktif dari semua cog layanan -> list dict ternormalisasi.

    Bila `guild` diberikan, tiket yang channel-nya sudah tidak ada akan
    dilewati supaya antrian tidak menampilkan sisa tiket "hantu".
    """
    out = []
    for cog_name, layanan in SERVICE_COGS.items():
        cog = bot.cogs.get(cog_name)
        if not cog or not hasattr(cog, "active_tickets"):
            continue
        for ch_id, ticket in list(cog.active_tickets.items()):
            if guild is not None and guild.get_channel(ch_id) is None:
                continue
            if not isinstance(ticket, dict):
                continue
            out.append(normalize_ticket(layanan, ch_id, ticket))
    return out


def build_queue(tickets):
    """Urutkan tiket (terlama dulu) & hitung posisi antrian untuk yg menunggu.

    Mengembalikan list terurut; tiap entri ditambah:
      - 'position': nomor antrean (mulai 1) untuk tiket menunggu, None bila
        sedang diproses.
      - 'ahead': jumlah tiket menunggu yang ada di depannya (None bila diproses).

    Tiket yang sedang diproses tidak dihitung sebagai "di depan" tiket lain,
    karena sudah keluar dari barisan tunggu.
    """
    _far_future = datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)

    def _key(t):
        return t["opened_at"] or _far_future

    ordered = sorted(tickets, key=_key)
    waiting_seen = 0
    for t in ordered:
        if t["handling"]:
            t["position"] = None
            t["ahead"] = None
        else:
            t["ahead"] = waiting_seen
            t["position"] = waiting_seen + 1
            waiting_seen += 1
    return ordered


def queue_counts(ordered):
    """Hitung ringkasan: (jumlah_menunggu, jumlah_diproses)."""
    handling = sum(1 for t in ordered if t["handling"])
    waiting = len(ordered) - handling
    return waiting, handling
