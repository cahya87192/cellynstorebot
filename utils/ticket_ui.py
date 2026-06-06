"""Helper tampilan tiket terpusat: penamaan channel, warna neon per-layanan,
embed buka tiket, dan embed log transaksi berhasil.

Dipakai semua cog layanan supaya tampilan seragam.

Konvensi:
- Nomor tiket GLOBAL (utils.counter.next_ticket_number), ditampilkan 7 digit.
- Nama channel: "📍-{layanan}-{0000044}-{username}".
- Judul embed polos (tanpa emoji), bahasa formal.
- Embed buka tiket: warna NEON per-layanan.
- Embed log sukses: selalu NEON HIJAU + reminder rating 24 jam.
- Tanggal footer: dd/mm/yyyy.
"""

import datetime
import re

import discord

from utils.config import STORE_NAME

# ── Warna neon per-layanan (embed buka tiket) ────────────────────────────────────
NEON_COLORS = {
    "lainnya": 0x1F51FF,   # neon blue
    "robux": 0xFF10F0,     # neon pink
    "ml": 0x00FFFF,        # neon cyan
    "ff": 0x00FFFF,        # neon cyan (Free Fire ikut ML)
    "vilog": 0xFFFF33,     # neon yellow
    "gp": 0xB026FF,        # neon purple
    "jualbeli": 0xFF6700,  # neon orange
    "midman": 0x39FF14,    # neon green
}
NEON_GREEN = 0x39FF14      # warna log transaksi berhasil (semua layanan)
DEFAULT_NEON = 0x1F51FF

# Label layanan ramah-tampilan (judul embed).
LAYANAN_DISPLAY = {
    "lainnya": "LAINNYA",
    "robux": "ROBUX",
    "ml": "MOBILE LEGENDS",
    "ff": "FREE FIRE",
    "vilog": "VILOG",
    "gp": "GAMEPASS",
    "jualbeli": "JUAL BELI",
    "midman": "MIDDLEMAN",
}

TICKET_NUMBER_PAD = 7  # 0000044


def neon_color(layanan: str) -> int:
    return NEON_COLORS.get((layanan or "").lower(), DEFAULT_NEON)


def format_number(num: int) -> str:
    """Nomor tiket -> string 7 digit, mis. 44 -> '0000044'."""
    return str(int(num)).zfill(TICKET_NUMBER_PAD)


def _sanitize_username(username: str) -> str:
    """Amankan username untuk nama channel Discord (lowercase, tanpa karakter aneh)."""
    u = (username or "user").lower()
    u = re.sub(r"[^a-z0-9_-]", "", u)  # buang karakter non-aman
    return u[:20] or "user"


def channel_name(layanan: str, number: int, username: str) -> str:
    """Bangun nama channel: '📍-{layanan}-{0000044}-{username}'."""
    return f"📍-{layanan.lower()}-{format_number(number)}-{_sanitize_username(username)}"


def _today_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y")


def avatar_url(member) -> str | None:
    """Ambil URL foto profil member/user dengan aman (None bila tidak ada)."""
    if member is None:
        return None
    try:
        return member.display_avatar.url
    except Exception:
        try:
            return member.avatar.url if member.avatar else None
        except Exception:
            return None


def open_ticket_embed(
    layanan: str,
    number: int,
    member: discord.abc.User,
    *,
    item: str = None,
    total: str = None,
    payment: str = "QRIS",
    extra_fields: list[tuple[str, str, bool]] = None,
    description: str = None,
    terms: str = None,
) -> discord.Embed:
    """Embed standar saat tiket dibuka (judul polos, formal, warna neon layanan).

    extra_fields: list (name, value, inline) untuk field spesifik layanan.
    """
    display = LAYANAN_DISPLAY.get((layanan or "").lower(), (layanan or "ORDER").upper())
    num = format_number(number)

    embed = discord.Embed(
        title=f"TIKET {display} · #{num}",
        description=(
            f"Terima kasih telah membuka tiket di {STORE_NAME}.\n"
            "Admin kami akan segera memproses pesanan Anda."
        ),
        color=neon_color(layanan),
    )
    embed.add_field(name="Member", value=member.mention, inline=True)
    embed.add_field(name="Tiket", value=f"#{num}", inline=True)
    embed.add_field(name="Layanan", value=display.title(), inline=True)

    if item:
        embed.add_field(name="Item", value=str(item)[:1024], inline=False)
    if total is not None:
        embed.add_field(name="Total", value=str(total), inline=True)
    if payment:
        embed.add_field(name="Metode Pembayaran", value=payment, inline=True)

    for name, value, inline in (extra_fields or []):
        embed.add_field(name=name, value=value, inline=inline)

    if description:
        embed.add_field(name="Deskripsi", value=str(description)[:1024], inline=False)
    if terms:
        embed.add_field(name="Syarat & Ketentuan", value=str(terms)[:1024], inline=False)

    embed.set_footer(text=f"{STORE_NAME} · {_today_str()}")
    return embed


def success_log_embed(
    layanan: str,
    number: int,
    *,
    subtitle: str = None,
    member_value: str = None,
    admin_value: str = None,
    item: str = None,
    total: str = None,
    payment: str = "QRIS",
    extra_fields: list[tuple[str, str, bool]] = None,
    rating_reminder: bool = True,
    thumbnail_url: str = None,
) -> discord.Embed:
    """Embed log 'TRANSAKSI BERHASIL' (selalu neon hijau, + reminder rating).

    thumbnail_url: foto profil pembeli, tampil di pojok kanan atas embed.
    """
    num = format_number(number)
    embed = discord.Embed(
        title=f"TRANSAKSI BERHASIL · #{num}",
        description=subtitle or None,
        color=NEON_GREEN,
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if member_value:
        embed.add_field(name="Member", value=member_value, inline=True)
    if admin_value:
        embed.add_field(name="Admin", value=admin_value, inline=True)
    if item:
        embed.add_field(name="Item", value=str(item)[:1024], inline=False)
    if total is not None:
        embed.add_field(name="Total", value=str(total), inline=True)
    if payment:
        embed.add_field(name="Metode Pembayaran", value=payment, inline=True)

    for name, value, inline in (extra_fields or []):
        embed.add_field(name=name, value=value, inline=inline)

    if rating_reminder:
        embed.add_field(
            name="\u200b",
            value=(
                "Mohon berikan rating dalam **24 jam**. "
                "Tanpa rating, garansi transaksi tidak berlaku."
            ),
            inline=False,
        )
    embed.set_footer(text=f"{STORE_NAME} · {_today_str()}")
    return embed


# Garis pemisah tipis di AKHIR pesan log transaksi. Tujuannya supaya beberapa
# log "transaksi berhasil" yang tercetak berdekatan tetap terlihat terpisah
# (tidak nempel), tanpa hiasan berlebihan.
LOG_DIVIDER = "─" * 50


def warranty_status_line(rating: int | None) -> str:
    """Baris status garansi untuk pesan log transaksi (flat text).

    rating None/0 -> belum aktif; 1-5 -> aktif dengan jumlah bintang.
    """
    if rating:
        r = max(1, min(5, int(rating)))
        return f"🟢 *Aktif (Sudah DiRating {r} ⭐)*"
    return "🛑 *Belum Aktif (belum DiRating 💢)*"


def success_log_text(
    *,
    seller: str,
    buyer: str,
    product: str,
    qty=1,
    harga=0,
    rating: int | None = None,
    rating_channel_id: int = 0,
    buyer_badge: str = "",
) -> str:
    """Pesan log 'transaksi berhasil' dalam bentuk TEKS FLAT.

    Status garansi otomatis menyesuaikan: 'belum aktif' bila belum dirating,
    'aktif' bila sudah. `seller`/`buyer` boleh mention (mis. '<@123>') atau teks.
    Dipakai juga untuk merender ulang pesan setelah member memberi rating.

    `buyer_badge` (opsional): emoji/teks yang ditempel setelah nama buyer, mis.
    badge Top Spender. Boleh emoji custom server ("<a:nama:id>") karena baris ini
    dirender sebagai message content biasa (emoji custom tampil normal di situ).
    """
    rating_ref = f"<#{rating_channel_id}>" if rating_channel_id else "channel rating"
    buyer_line = f"{buyer} {buyer_badge}".rstrip() if buyer_badge else buyer
    try:
        # Format ribuan gaya Indonesia: 11000 -> 11.000
        harga_str = f"Rp {int(harga):,}".replace(",", ".")
    except (TypeError, ValueError):
        harga_str = f"Rp {harga}"
    return (
        f"**🔔 𝗣𝗘𝗠𝗕𝗘𝗟𝗜𝗔𝗡 𝗕𝗘𝗥𝗛𝗔𝗦𝗜𝗟 𝗗𝗜𝗦𝗘𝗟𝗘𝗦𝗔𝗜𝗞𝗔𝗡 🔔**\n"
        f"**𝗔𝗗𝗠𝗜𝗡** : {seller}\n"
        f"**𝗕𝗨𝗬𝗘𝗥** : {buyer_line}\n"
        f"**𝗜𝗧𝗘𝗠** : {product}\n"
        f"**𝗝𝗨𝗠𝗟𝗔𝗛** : {qty}\n"
        f"**𝗛𝗔𝗥𝗚𝗔** : {harga_str}\n"
        f"**𝗚𝗔𝗥𝗔𝗡𝗦𝗜** : {warranty_status_line(rating)}\n"
        f"**𝗝𝗔𝗡𝗚𝗔𝗡 𝗟𝗨𝗣𝗔 𝗥𝗔𝗧𝗜𝗡𝗚 𝗗𝗜 {rating_ref} 𝗔𝗚𝗔𝗥 𝗚𝗔𝗥𝗔𝗡𝗦𝗜 𝗔𝗞𝗧𝗜𝗙**\n"
        f"**𝗞𝗔𝗠𝗜 𝗧𝗨𝗡𝗚𝗚𝗨 𝗥𝗘𝗣𝗘𝗔𝗧 𝗢𝗥𝗗𝗘𝗥𝗡𝗬𝗔, 𝗧𝗘𝗥𝗜𝗠𝗔 𝗞𝗔𝗦𝗜𝗛!**\n"
        f"{LOG_DIVIDER}"
    )



# ── Notice penutupan tiket (sukses / batal) ──────────────────────────────────
# Warna konsisten dipakai semua layanan untuk pesan singkat sebelum channel
# tiket dihapus, supaya seragam & lebih rapi daripada teks polos.
COLOR_TICKET_SUCCESS = 0x2ECC71  # hijau
COLOR_TICKET_CANCEL = 0xED4245   # merah


def ticket_success_embed(message: str, *, countdown: int = 5) -> discord.Embed:
    """Embed kecil 'transaksi selesai' sebelum tiket ditutup otomatis.

    `message` = isi utama (mis. 'Topup berhasil diproses...'). `countdown` =
    jeda detik sebelum channel dihapus (ditampilkan agar member tidak kaget).
    """
    embed = discord.Embed(
        title="✅ Transaksi Selesai",
        description=message,
        color=COLOR_TICKET_SUCCESS,
    )
    embed.add_field(
        name="\u200b",
        value=f"_Tiket akan ditutup otomatis dalam {countdown} detik._",
        inline=False,
    )
    embed.set_footer(text=f"{STORE_NAME} · Terima kasih sudah berbelanja 💛")
    return embed


def ticket_cancel_embed(*, by_mention: str, reason: str | None = None,
                        countdown: int = 5,
                        title: str = "❌ Transaksi Dibatalkan") -> discord.Embed:
    """Embed kecil pembatalan tiket yang seragam untuk semua layanan."""
    embed = discord.Embed(title=title, color=COLOR_TICKET_CANCEL)
    embed.add_field(name="Dibatalkan oleh", value=by_mention, inline=True)
    embed.add_field(
        name="Alasan",
        value=reason or "Tidak ada alasan diberikan.",
        inline=False,
    )
    embed.add_field(
        name="\u200b",
        value=f"_Tiket akan ditutup otomatis dalam {countdown} detik._",
        inline=False,
    )
    embed.set_footer(text=STORE_NAME)
    return embed
