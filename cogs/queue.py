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
"""

import asyncio
import datetime
import json

import discord
from discord.ext import commands, tasks

from utils.config import GUILD_ID, ADMIN_ROLE_ID, STORE_NAME
from utils.db import get_conn
from utils import queue as queuelib
from utils import ticket_ui

BOARD_CHANNEL_KEY = "queue_board_channel_id"
BOARD_MESSAGE_KEY = "queue_board_message_id"
CARDS_ENABLED_KEY = "queue_cards_enabled"
CARD_MESSAGES_KEY = "queue_card_messages"

REFRESH_SECONDS = 30
MAX_BOARD_ROWS = 25  # batas baris di papan agar tetap rapi & dalam limit embed

COLOR_BOARD = 0x5865F2
COLOR_WAITING = 0xFFA500   # oranye
COLOR_HANDLING = 0x39FF14  # neon hijau


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


def _fmt_age(opened_at, now):
    """Lama tiket terbuka -> string ringkas, mis. '2j 5m', '12m', '8s'."""
    if not opened_at:
        return "-"
    secs = int((now - opened_at).total_seconds())
    if secs < 0:
        secs = 0
    jam = secs // 3600
    menit = (secs % 3600) // 60
    if jam > 0:
        return f"{jam}j {menit}m"
    if menit > 0:
        return f"{menit}m"
    return f"{secs}s"


def _is_admin(member) -> bool:
    return any(r.id == ADMIN_ROLE_ID for r in getattr(member, "roles", []))


class TicketQueue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._card_text_cache = {}  # channel_id -> teks kartu terakhir (kurangi edit)
        self.refresh_queue.start()

    def cog_unload(self):
        self.refresh_queue.cancel()

    # ── Loop utama ────────────────────────────────────────────────────────────
    @tasks.loop(seconds=REFRESH_SECONDS)
    async def refresh_queue(self):
        try:
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                return
            tickets = queuelib.collect_tickets(self.bot, guild)
            ordered = queuelib.build_queue(tickets)
            await self._update_board(guild, ordered)
            if (_get_setting(CARDS_ENABLED_KEY) or "1") == "1":
                await self._update_cards(guild, ordered)
        except Exception as e:
            print(f"[Queue] refresh error: {e}")

    @refresh_queue.before_loop
    async def before_refresh(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

    # ── Papan antrian admin ────────────────────────────────────────────────────
    def _board_embed(self, ordered):
        now = datetime.datetime.now(datetime.timezone.utc)
        waiting, handling = queuelib.queue_counts(ordered)
        embed = discord.Embed(
            title="📋 Papan Antrian Tiket",
            color=COLOR_BOARD,
            timestamp=now,
        )
        if not ordered:
            embed.description = "Tidak ada tiket aktif saat ini. 🎉"
            embed.set_footer(text=f"{STORE_NAME} • diperbarui otomatis")
            return embed

        lines = [f"🟡 Menunggu: **{waiting}**  •  🟢 Diproses: **{handling}**", ""]
        for t in ordered[:MAX_BOARD_ROWS]:
            emoji = "🟢" if t["handling"] else "🟡"
            num = ticket_ui.format_number(t["ticket_number"])
            disp = ticket_ui.LAYANAN_DISPLAY.get(t["layanan"], t["layanan"].upper())
            mention = f"<@{t['member_id']}>" if t["member_id"] else "-"
            age = _fmt_age(t["opened_at"], now)
            chan = f"<#{t['channel_id']}>"
            lines.append(f"{emoji} `#{num}` **{disp}** · {mention} · {age} · {chan}")

        if len(ordered) > MAX_BOARD_ROWS:
            lines.append(f"\n… dan {len(ordered) - MAX_BOARD_ROWS} tiket lagi.")

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
        if t["handling"]:
            return "🟢 Sedang diproses admin. Mohon tunggu sebentar ya 🙏"
        if t["position"] == 1:
            return ("🟡 Kamu berada di antrean **terdepan**. "
                    "Admin akan segera memproses pesananmu 🙏")
        return (f"🟡 Posisi antrean kamu: **ke-{t['position']}** "
                f"({t['ahead']} tiket di depanmu). Mohon ditunggu ya 🙏")

    def _card_embed(self, t, text):
        num = ticket_ui.format_number(t["ticket_number"])
        embed = discord.Embed(
            title=f"🎫 Antrean Tiket · #{num}",
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
        ordered = queuelib.build_queue(queuelib.collect_tickets(self.bot, guild))
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
        ordered = queuelib.build_queue(queuelib.collect_tickets(self.bot, guild))
        await self._update_board(guild, ordered)
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


async def setup(bot):
    await bot.add_cog(TicketQueue(bot))
