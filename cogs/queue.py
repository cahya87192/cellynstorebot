"""Sistem antrian tiket (Opsi A: posisi + status, tanpa estimasi waktu).

Dua bagian:
  1. Papan antrian admin  — satu pesan di channel khusus yang otomatis
     diperbarui, menampilkan semua tiket aktif terurut (terlama di atas)
     beserta status 🟡 menunggu / 🟢 diproses.
  2. Kartu posisi customer — pesan kecil di dalam tiap tiket yang memberi tahu
     member posisi antreannya, diperbarui otomatis saat antrean bergerak.

Cog ini READ-ONLY terhadap cog layanan lain: ia hanya membaca `active_tickets`
milik cog lain dan mengelola pesannya sendiri. Tidak pernah mengubah/menutup
tiket, sehingga aman ditambahkan tanpa risiko mengganggu alur transaksi.

Pengaturan disimpan di tabel `bot_state` (key/value), jadi tidak perlu
mengubah .env:
  - queue_board_channel_id : channel papan antrian (diset via !antrianboard)
  - queue_board_message_id : id pesan papan (dikelola otomatis)
  - queue_cards_enabled    : "1"/"0" toggle kartu customer
  - queue_card_messages    : JSON {channel_id: message_id} kartu per-tiket
  - queue_handling_map     : JSON {channel_id: admin_id} — SUMBER KEBENARAN
        TUNGGAL status "diproses". Diisi lewat !pay, dihapus lewat !unpay,
        bertahan restart, dan dibersihkan otomatis saat channel tiket dihapus.
"""

import asyncio
import datetime
import json
import time

import discord
from discord.ext import commands, tasks

from utils.config import GUILD_ID, ADMIN_ROLE_ID, STORE_NAME

try:
    from utils.config import PUBLIC_QUEUE_CHANNEL_ID as _PUBLIC_DEFAULT
except Exception:  # pragma: no cover
    _PUBLIC_DEFAULT = 0
try:
    from utils.config import TOP_SPENDER_BADGE as _PRIORITY_BADGE
except Exception:  # pragma: no cover
    _PRIORITY_BADGE = ""
PRIORITY_BADGE = _PRIORITY_BADGE or "👑"
from utils.db import get_conn
from utils import queue as queuelib
from utils import ticket_ui

try:
    # Deteksi prioritas dari DATA transaksi (bukan role). Diimpor defensif supaya
    # cog antrian tetap jalan walau modul top_spender berubah/absen.
    from cogs.top_spender import get_top_spenders, TOP_SPENDER_TOP_N
except Exception:  # pragma: no cover - fallback bila modul tidak tersedia
    get_top_spenders = None
    TOP_SPENDER_TOP_N = 10

try:
    # Badge mahkota prioritas (emoji server). Fallback ke 👑 unicode bila absen.
    from utils.config import TOP_SPENDER_BADGE as _PRIORITY_BADGE
except Exception:  # pragma: no cover
    _PRIORITY_BADGE = ""
PRIORITY_BADGE = _PRIORITY_BADGE or "👑"

BOARD_CHANNEL_KEY = "queue_board_channel_id"
BOARD_MESSAGE_KEY = "queue_board_message_id"
CARDS_ENABLED_KEY = "queue_cards_enabled"
CARD_MESSAGES_KEY = "queue_card_messages"
HANDLING_MAP_KEY = "queue_handling_map"
PUBLIC_CHANNEL_KEY = "queue_public_channel_id"
PUBLIC_MESSAGE_KEY = "queue_public_message_id"

REFRESH_SECONDS = 30
MAX_BOARD_ROWS = 25  # batas baris di papan agar tetap rapi & dalam limit embed

# Kartu STICKY: jaga kartu posisi tetap di paling bawah channel tiket, tetapi
# dengan debounce ketat supaya tidak spam / kena rate-limit.
STICKY_COOLDOWN_SECONDS = 25   # jeda minimal antar re-stick per channel
STICKY_MIN_MESSAGES = 3        # baru re-stick bila kartu sudah "ketimbun" pesan

COLOR_BOARD = 0x5865F2
COLOR_WAITING = 0xFFA500   # oranye
COLOR_HANDLING = 0x39FF14  # neon hijau

# Thumbnail papan antrian publik.
PUBLIC_BOARD_THUMBNAIL = "https://i.imgur.com/32I6YIx.png"
# Penjelasan fungsi papan (ditampilkan di bagian bawah embed publik).
PUBLIC_BOARD_INFO = (
    "Papan ini menampilkan antrean tiket secara **real-time** agar kamu tahu "
    "posisi & estimasi giliranmu. Admin memproses tiket **berurutan dari yang "
    "paling lama menunggu** (pesanan Top Spender diprioritaskan). Mohon "
    "ditunggu dengan sabar ya — setiap tiket pasti dilayani. 🙏"
)

# Emoji per-layanan untuk papan & kartu. Per keputusan owner, semua layanan
# memakai satu emoji server yang sama. Ganti SERVICE_EMOJI bila ingin set lain;
# bila dikosongkan, _layanan_emoji() jatuh ke "🎫" unicode.
SERVICE_EMOJI = "<:symbolcheck:1480599052109217892>"
LAYANAN_EMOJI = {
    "midman": SERVICE_EMOJI,
    "jualbeli": SERVICE_EMOJI,
    "robux": SERVICE_EMOJI,
    "vilog": SERVICE_EMOJI,
    "gp": SERVICE_EMOJI,
    "ml": SERVICE_EMOJI,
    "lainnya": SERVICE_EMOJI,
}


def _get_setting(key):
    conn = get_conn()
    row = conn.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def _set_setting(key, value):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
        (key, "" if value is None else str(value)),
    )
    conn.commit()
    conn.close()


def _layanan_emoji(layanan) -> str:
    return LAYANAN_EMOJI.get((layanan or "").lower(), SERVICE_EMOJI or "🎫")


def _layanan_label(layanan) -> str:
    return ticket_ui.LAYANAN_DISPLAY.get(layanan, str(layanan or "").upper()).title()


def _fmt_ticket_no(number) -> str:
    """Nomor tiket -> '#0000044'. Safety-net: 0/None -> '—' (bukan '0000000')."""
    if not number:
        return "—"
    return f"#{ticket_ui.format_number(number)}"


def _fmt_relative(opened_at) -> str:
    """Waktu buka -> timestamp relatif Discord (mis. '2 jam lalu'). '-' bila kosong."""
    if not opened_at:
        return "-"
    return f"<t:{int(opened_at.timestamp())}:R>"


def _is_admin(member) -> bool:
    return any(r.id == ADMIN_ROLE_ID for r in getattr(member, "roles", []))


class TicketQueue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._card_text_cache = {}  # channel_id -> teks kartu terakhir (kurangi edit)
        self._sticky_msgcount = {}  # channel_id -> jumlah pesan sejak kartu terakhir
        self._sticky_last = {}      # channel_id -> monotonic ts re-stick terakhir
        self._sticky_lock = asyncio.Lock()
        # Seed channel papan publik dari config bila belum pernah diset (sekali).
        if _PUBLIC_DEFAULT and not _get_setting(PUBLIC_CHANNEL_KEY):
            _set_setting(PUBLIC_CHANNEL_KEY, _PUBLIC_DEFAULT)
        self.refresh_queue.start()

    def cog_unload(self):
        self.refresh_queue.cancel()

    # ── State helpers ───────────────────────────────────────────────────────────
    def _load_handling_map(self):
        """Map {int channel_id: admin_id} status 'diproses' (dari !pay)."""
        raw = _get_setting(HANDLING_MAP_KEY)
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return {}
        if not isinstance(data, dict):
            return {}
        out = {}
        for k, v in data.items():
            try:
                out[int(k)] = v
            except (ValueError, TypeError):
                continue
        return out

    def _save_handling_map(self, handling_map):
        _set_setting(HANDLING_MAP_KEY, json.dumps({str(k): v for k, v in handling_map.items()}))

    def _get_priority_ids(self):
        """Set member_id Top Spender bulan berjalan (Top-N), dari DATA transaksi.

        Bukan dari role. Defensif: kembalikan set kosong bila data/akses gagal.
        """
        if get_top_spenders is None:
            return set()
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            top = get_top_spenders(now.year, now.month, TOP_SPENDER_TOP_N)
            return {s["user_id"] for s in top if s.get("user_id")}
        except Exception as e:
            print(f"[Queue] priority lookup error: {e}")
            return set()

    def _collect_ordered(self, guild):
        """Kumpulkan + urutkan tiket dengan handling_map & priority_ids terkini."""
        handling_map = self._load_handling_map()
        priority_ids = self._get_priority_ids()
        tickets = queuelib.collect_tickets(self.bot, guild, handling_map, priority_ids)
        return queuelib.build_queue(tickets)

    async def _refresh_now(self, guild):
        """Perbarui papan + kartu seketika (dipakai oleh !pay/!unpay)."""
        ordered = self._collect_ordered(guild)
        await self._update_board(guild, ordered)
        await self._update_public_board(guild, ordered)
        if (_get_setting(CARDS_ENABLED_KEY) or "1") == "1":
            await self._update_cards(guild, ordered)
        return ordered

    # ── Loop utama ────────────────────────────────────────────────────────────
    @tasks.loop(seconds=REFRESH_SECONDS)
    async def refresh_queue(self):
        try:
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                return
            self._prune_handling_map(guild)
            ordered = self._collect_ordered(guild)
            await self._update_board(guild, ordered)
            await self._update_public_board(guild, ordered)
            if (_get_setting(CARDS_ENABLED_KEY) or "1") == "1":
                await self._update_cards(guild, ordered)
        except Exception as e:
            print(f"[Queue] refresh error: {e}")

    @refresh_queue.before_loop
    async def before_refresh(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

    def _prune_handling_map(self, guild):
        """Bersihkan entri 'diproses' untuk channel tiket yang sudah dihapus."""
        handling_map = self._load_handling_map()
        if not handling_map:
            return
        alive = {cid: aid for cid, aid in handling_map.items()
                 if guild.get_channel(cid) is not None}
        if len(alive) != len(handling_map):
            self._save_handling_map(alive)

    # ── Papan antrian admin ────────────────────────────────────────────────────
    def _board_row(self, t, *, prefix=""):
        """Satu baris papan. `prefix` mis. '1.' untuk barisan menunggu."""
        emoji = _layanan_emoji(t["layanan"])
        num = _fmt_ticket_no(t["ticket_number"])
        disp = _layanan_label(t["layanan"])
        mention = f"<@{t['member_id']}>" if t["member_id"] else "-"
        when = _fmt_relative(t["opened_at"])
        chan = f"<#{t['channel_id']}>"
        head = f"{prefix} " if prefix else ""
        crown = f"{PRIORITY_BADGE} " if t.get("is_priority") else ""
        base = f"{head}{emoji} `{num}` **{disp}** · {crown}{mention}"
        if t["handling"]:
            admin = f"<@{t['admin_id']}>" if t.get("admin_id") else "admin"
            return f"{base} · ditangani oleh {admin} · {chan}"
        return f"{base} · {when} · {chan}"

    def _board_embed(self, ordered):
        now = datetime.datetime.now(datetime.timezone.utc)
        waiting, handling = queuelib.queue_counts(ordered)
        embed = discord.Embed(
            title="🛗 DAFTAR ANTRIAN TIKET",
            color=COLOR_BOARD,
            timestamp=now,
        )
        if not ordered:
            embed.description = "Tidak ada tiket aktif saat ini. 🎉"
            embed.set_footer(text=f"{STORE_NAME} • diperbarui otomatis")
            return embed

        processing = [t for t in ordered if t["handling"]]
        waiting_list = [t for t in ordered if not t["handling"]]

        lines = [f"⛔ Menunggu: **{waiting}**   •   ♻️ Diproses: **{handling}**"]

        # Seksi: sedang diproses
        lines.append("")
        lines.append("**🟢 SEDANG DIPROSES**")
        if processing:
            for t in processing[:MAX_BOARD_ROWS]:
                lines.append(self._board_row(t))
        else:
            lines.append("_Tidak ada tiket yang sedang diproses._")

        # Seksi: menunggu (terlama di atas), bernomor 1,2,3,...
        lines.append("")
        lines.append("**⛔ MENUNGGU**")
        if waiting_list:
            shown = waiting_list[:MAX_BOARD_ROWS]
            for i, t in enumerate(shown, start=1):
                lines.append(self._board_row(t, prefix=f"`{i}.`"))
            if len(waiting_list) > MAX_BOARD_ROWS:
                lines.append(f"… dan {len(waiting_list) - MAX_BOARD_ROWS} tiket menunggu lagi.")
        else:
            lines.append("_Tidak ada tiket yang menunggu._")

        embed.description = "\n".join(lines)[:4000]
        embed.set_footer(text=f"{STORE_NAME} • diperbarui otomatis tiap {REFRESH_SECONDS} detik")
        return embed

    async def _update_board(self, guild, ordered):
        ch_raw = _get_setting(BOARD_CHANNEL_KEY)
        if not ch_raw or not str(ch_raw).isdigit():
            return
        channel = guild.get_channel(int(ch_raw))
        if not channel:
            return

        embed = self._board_embed(ordered)
        msg_id_raw = _get_setting(BOARD_MESSAGE_KEY)
        if msg_id_raw and str(msg_id_raw).isdigit():
            try:
                await channel.get_partial_message(int(msg_id_raw)).edit(embed=embed)
                return
            except discord.NotFound:
                pass  # pesan hilang, buat baru di bawah
            except discord.HTTPException as e:
                print(f"[Queue] board edit error: {e}")
                return
        try:
            msg = await channel.send(embed=embed)
            _set_setting(BOARD_MESSAGE_KEY, msg.id)
        except Exception as e:
            print(f"[Queue] board send error: {e}")

    # ── Papan PUBLIK (ringkas & anonim, untuk member) ───────────────────────────
    def _public_board_embed(self, ordered):
        """Versi ringkas papan untuk channel member: tanpa nama/mention & tanpa
        link channel. Hanya jumlah, urutan layanan, dan tanda prioritas 👑."""
        now = datetime.datetime.now(datetime.timezone.utc)
        waiting, handling = queuelib.queue_counts(ordered)
        embed = discord.Embed(
            title="🛗 Antrian Toko — Live",
            color=COLOR_BOARD,
            timestamp=now,
        )
        if PUBLIC_BOARD_THUMBNAIL:
            embed.set_thumbnail(url=PUBLIC_BOARD_THUMBNAIL)
        if not ordered:
            embed.description = ("Tidak ada antrean saat ini. Toko siap melayani — "
                                 "silakan buka tiket! 🎉")
            embed.add_field(name="ℹ️ Tentang Papan Ini", value=PUBLIC_BOARD_INFO, inline=False)
            embed.set_footer(text=f"{STORE_NAME} • diperbarui otomatis")
            return embed

        processing = [t for t in ordered if t["handling"]]
        waiting_list = [t for t in ordered if not t["handling"]]

        lines = [f"🟢 Sedang diproses: **{handling}**   •   ⛔ Menunggu: **{waiting}**", ""]

        lines.append("**🟢 SEDANG DIPROSES**")
        if processing:
            for t in processing[:MAX_BOARD_ROWS]:
                admin = f" — ditangani <@{t['admin_id']}>" if t.get("admin_id") else ""
                lines.append(f"{_layanan_emoji(t['layanan'])} {_layanan_label(t['layanan'])}{admin}")
        else:
            lines.append("_Belum ada yang diproses._")

        lines.append("")
        lines.append("**⛔ ANTREAN MENUNGGU** _(terlama di atas)_")
        if waiting_list:
            for i, t in enumerate(waiting_list[:MAX_BOARD_ROWS], start=1):
                crown = f" {PRIORITY_BADGE}" if t.get("is_priority") else ""
                lines.append(f"`{i}.` {_layanan_emoji(t['layanan'])} {_layanan_label(t['layanan'])}{crown}")
            if len(waiting_list) > MAX_BOARD_ROWS:
                lines.append(f"… dan {len(waiting_list) - MAX_BOARD_ROWS} lagi.")
        else:
            lines.append("_Tidak ada yang menunggu._")

        lines.append("")
        lines.append(f"{PRIORITY_BADGE} = pesanan diprioritaskan (Top Spender)")
        embed.description = "\n".join(lines)[:4000]
        embed.add_field(name="ℹ️ Tentang Papan Ini", value=PUBLIC_BOARD_INFO, inline=False)
        embed.set_footer(text=f"{STORE_NAME} • antrean diperbarui otomatis")
        return embed

    async def _update_public_board(self, guild, ordered):
        ch_raw = _get_setting(PUBLIC_CHANNEL_KEY)
        if not ch_raw or not str(ch_raw).isdigit():
            return
        channel = guild.get_channel(int(ch_raw))
        if not channel:
            return
        embed = self._public_board_embed(ordered)
        msg_id_raw = _get_setting(PUBLIC_MESSAGE_KEY)
        if msg_id_raw and str(msg_id_raw).isdigit():
            try:
                await channel.get_partial_message(int(msg_id_raw)).edit(embed=embed)
                return
            except discord.NotFound:
                pass
            except discord.HTTPException as e:
                print(f"[Queue] public board edit error: {e}")
                return
        try:
            msg = await channel.send(embed=embed)
            _set_setting(PUBLIC_MESSAGE_KEY, msg.id)
        except Exception as e:
            print(f"[Queue] public board send error: {e}")

    # ── Kartu posisi customer ───────────────────────────────────────────────────
    def _load_card_map(self):
        raw = _get_setting(CARD_MESSAGES_KEY)
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except (ValueError, TypeError):
            return {}

    def _save_card_map(self, card_map):
        _set_setting(CARD_MESSAGES_KEY, json.dumps(card_map))

    def _card_text(self, t):
        """Teks status untuk customer. Dipakai juga sebagai cache key (kurangi edit)."""
        if t["handling"]:
            admin = f"<@{t['admin_id']}>" if t.get("admin_id") else "admin"
            return f"🟢 Sedang diproses oleh {admin}. Mohon tunggu sebentar ya"
        if t["position"] == 1:
            return ("🟡 **Posisi Antrean: 1** — kamu berada di antrean terdepan. "
                    "Admin akan segera memproses pesananmu")
        ahead = t.get("ahead") or 0
        return (f"🔄 **Posisi Antrean: {t['position']}** "
                f"({ahead} tiket di depanmu). Mohon ditunggu ya!")

    def _card_embed(self, t, text):
        num = _fmt_ticket_no(t["ticket_number"])
        disp = _layanan_label(t["layanan"])
        emoji = _layanan_emoji(t["layanan"])
        embed = discord.Embed(
            title=f"{emoji} Tiket {num} · {disp}",
            description=text,
            color=COLOR_HANDLING if t["handling"] else COLOR_WAITING,
        )
        embed.set_footer(text=f"{STORE_NAME} • status antrean diperbarui otomatis")
        return embed

    async def _update_cards(self, guild, ordered):
        card_map = self._load_card_map()
        active_ch_ids = set()
        changed = False

        for t in ordered:
            ch_id = t["channel_id"]
            active_ch_ids.add(ch_id)
            channel = guild.get_channel(ch_id)
            if not channel:
                continue

            text = self._card_text(t)
            if self._card_text_cache.get(ch_id) == text:
                continue  # tidak ada perubahan, lewati edit

            embed = self._card_embed(t, text)
            key = str(ch_id)
            msg_id = card_map.get(key)
            sent_id = None

            if msg_id and str(msg_id).isdigit():
                try:
                    await channel.get_partial_message(int(msg_id)).edit(embed=embed)
                    sent_id = int(msg_id)
                except discord.NotFound:
                    sent_id = None
                except discord.HTTPException:
                    sent_id = int(msg_id)  # biarkan, coba lagi siklus berikutnya

            if sent_id is None:
                try:
                    msg = await channel.send(embed=embed)
                    sent_id = msg.id
                except Exception as e:
                    print(f"[Queue] card send error ({ch_id}): {e}")
                    continue

            card_map[key] = sent_id
            self._card_text_cache[ch_id] = text
            changed = True

        # Bersihkan entri untuk tiket yang sudah tidak aktif (channel terhapus).
        for key in list(card_map.keys()):
            if int(key) not in active_ch_ids:
                del card_map[key]
                changed = True
        for cid in list(self._card_text_cache.keys()):
            if cid not in active_ch_ids:
                del self._card_text_cache[cid]

        if changed:
            self._save_card_map(card_map)

    # ── Perintah admin ──────────────────────────────────────────────────────────
    @commands.command(name="antrianboard")
    async def antrianboard(self, ctx):
        """Set channel ini sebagai Papan Antrian dan langsung tampilkan."""
        if not _is_admin(ctx.author):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        _set_setting(BOARD_CHANNEL_KEY, ctx.channel.id)
        _set_setting(BOARD_MESSAGE_KEY, "")  # paksa buat pesan baru di sini
        guild = self.bot.get_guild(GUILD_ID)
        ordered = self._collect_ordered(guild)
        await self._update_board(guild, ordered)
        await ctx.send(
            "✅ Channel ini diset sebagai **Papan Antrian**. "
            "Papan akan diperbarui otomatis.",
            delete_after=8,
        )

    @commands.command(name="antrianoff")
    async def antrianoff(self, ctx):
        """Nonaktifkan papan antrian."""
        if not _is_admin(ctx.author):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        _set_setting(BOARD_CHANNEL_KEY, "")
        await ctx.send("🛑 Papan antrian dinonaktifkan.", delete_after=8)

    @commands.command(name="antrianpublik")
    async def antrianpublik(self, ctx):
        """Set channel ini sebagai Papan Antrian PUBLIK (ringkas & anonim untuk member)."""
        if not _is_admin(ctx.author):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        _set_setting(PUBLIC_CHANNEL_KEY, ctx.channel.id)
        _set_setting(PUBLIC_MESSAGE_KEY, "")  # paksa buat pesan baru di sini
        guild = self.bot.get_guild(GUILD_ID)
        ordered = self._collect_ordered(guild)
        await self._update_public_board(guild, ordered)
        await ctx.send(
            "✅ Channel ini diset sebagai **Papan Antrian Publik** "
            "(versi ringkas tanpa nama/link, aman untuk member).",
            delete_after=8,
        )

    @commands.command(name="antrianpublikoff")
    async def antrianpublikoff(self, ctx):
        """Nonaktifkan papan antrian publik."""
        if not _is_admin(ctx.author):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        _set_setting(PUBLIC_CHANNEL_KEY, "")
        await ctx.send("🛑 Papan antrian publik dinonaktifkan.", delete_after=8)

    @commands.command(name="antrianrefresh")
    async def antrianrefresh(self, ctx):
        """Paksa perbarui papan & kartu antrian sekarang."""
        if not _is_admin(ctx.author):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        guild = self.bot.get_guild(GUILD_ID)
        ordered = self._collect_ordered(guild)
        await self._update_board(guild, ordered)
        await self._update_public_board(guild, ordered)
        if (_get_setting(CARDS_ENABLED_KEY) or "1") == "1":
            await self._update_cards(guild, ordered)
        await ctx.send("🔄 Antrian diperbarui.", delete_after=5)

    @commands.command(name="antriancards")
    async def antriancards(self, ctx, mode: str = None):
        """Aktif/nonaktifkan kartu posisi antrean untuk customer: on / off."""
        if not _is_admin(ctx.author):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        mode = (mode or "").lower()
        if mode not in ("on", "off"):
            cur = (_get_setting(CARDS_ENABLED_KEY) or "1") == "1"
            await ctx.send(
                f"Kartu antrean customer saat ini: **{'ON' if cur else 'OFF'}**. "
                "Gunakan `!antriancards on` atau `!antriancards off`.",
                delete_after=10,
            )
            return
        _set_setting(CARDS_ENABLED_KEY, "1" if mode == "on" else "0")
        await ctx.send(f"✅ Kartu antrean customer di-set **{mode.upper()}**.", delete_after=8)

    # ── !pay / !unpay : sumber kebenaran tunggal status "diproses" ───────────────
    @commands.command(name="pay")
    async def pay_cmd(self, ctx):
        """Tandai tiket INI sedang diproses oleh admin yang menjalankan.

        Disimpan di bot_state (tahan restart). Papan & kartu langsung diperbarui.
        """
        if not _is_admin(ctx.author):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        guild = self.bot.get_guild(GUILD_ID) or ctx.guild
        ch_id = ctx.channel.id
        active_ids = {t["channel_id"] for t in queuelib.collect_tickets(self.bot, guild)}
        if ch_id not in active_ids:
            await ctx.send(
                "⚠️ `!pay` hanya untuk dijalankan **di dalam channel tiket aktif**.",
                delete_after=8,
            )
            return
        handling_map = self._load_handling_map()
        handling_map[ch_id] = ctx.author.id
        self._save_handling_map(handling_map)
        self._card_text_cache.pop(ch_id, None)  # paksa kartu diperbarui
        await self._refresh_now(guild)
        await ctx.send(
            f"🚨 Tiket ini ditandai **sedang diproses** oleh {ctx.author.mention}.",
            delete_after=8,
        )

    @commands.command(name="unpay")
    async def unpay_cmd(self, ctx):
        """Batalkan tanda 'sedang diproses' pada tiket ini (undo !pay)."""
        if not _is_admin(ctx.author):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        guild = self.bot.get_guild(GUILD_ID) or ctx.guild
        ch_id = ctx.channel.id
        handling_map = self._load_handling_map()
        if ch_id not in handling_map:
            await ctx.send(
                "ℹ️ Tiket ini memang belum ditandai 'sedang diproses'.",
                delete_after=8,
            )
            return
        del handling_map[ch_id]
        self._save_handling_map(handling_map)
        self._card_text_cache.pop(ch_id, None)
        await self._refresh_now(guild)
        await ctx.send(
            "🟡 Tanda 'sedang diproses' dibatalkan. Tiket kembali ke antrean menunggu.",
            delete_after=8,
        )

    # ── Kartu STICKY ────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message):
        """Jaga kartu posisi tetap di bawah; di-debounce ketat agar tak spam.

        Re-stick hanya bila: channel punya kartu, kartu sudah "ketimbun" minimal
        STICKY_MIN_MESSAGES pesan, DAN cooldown STICKY_COOLDOWN_SECONDS terlewati.
        """
        if message.author.bot or message.guild is None:
            return
        if (_get_setting(CARDS_ENABLED_KEY) or "1") != "1":
            return
        ch_id = message.channel.id
        if str(ch_id) not in self._load_card_map():
            return  # bukan channel tiket yang punya kartu

        self._sticky_msgcount[ch_id] = self._sticky_msgcount.get(ch_id, 0) + 1
        if self._sticky_msgcount[ch_id] < STICKY_MIN_MESSAGES:
            return
        if time.monotonic() - self._sticky_last.get(ch_id, 0.0) < STICKY_COOLDOWN_SECONDS:
            return

        async with self._sticky_lock:
            now = time.monotonic()
            if now - self._sticky_last.get(ch_id, 0.0) < STICKY_COOLDOWN_SECONDS:
                return
            self._sticky_last[ch_id] = now
            self._sticky_msgcount[ch_id] = 0
            try:
                await self._restick_card(message.channel)
            except Exception as e:
                print(f"[Queue] sticky error ({ch_id}): {e}")

    async def _restick_card(self, channel):
        """Hapus kartu lama lalu kirim ulang di paling bawah channel."""
        ordered = self._collect_ordered(channel.guild)
        t = next((x for x in ordered if x["channel_id"] == channel.id), None)
        if t is None:
            return  # tiket sudah tidak aktif
        card_map = self._load_card_map()
        key = str(channel.id)
        old_id = card_map.get(key)
        text = self._card_text(t)
        try:
            msg = await channel.send(embed=self._card_embed(t, text))
        except Exception as e:
            print(f"[Queue] sticky send error ({channel.id}): {e}")
            return
        card_map[key] = msg.id
        self._save_card_map(card_map)
        self._card_text_cache[channel.id] = text
        if old_id and str(old_id).isdigit() and int(old_id) != msg.id:
            try:
                await channel.get_partial_message(int(old_id)).delete()
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(TicketQueue(bot))
