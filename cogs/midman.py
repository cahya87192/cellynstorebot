import time
import discord
from discord.ext import commands
import asyncio
import datetime
from utils.fee import hitung_fee, format_nominal
from utils.tickets import save_tickets, load_tickets
from utils.transcript import generate as generate_transcript
from utils.config import (
    GUILD_ID, MIDMAN_CHANNEL_ID, ADMIN_ROLE_ID,
    TRANSCRIPT_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME, BACKUP_CHANNEL_ID, ERROR_LOG_CHANNEL_ID
)
from cogs.views import MidmanMainView, AdminSetupView, TradeFinishView
from utils.backup import do_backup, do_restore
from discord.ext import tasks
from utils.db import get_conn
from utils.store_hours import is_store_open
from utils import ticket_ui


def _get_setting(key: str) -> str | None:
    conn = get_conn()
    row = conn.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def _set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
        (key, value),
    )
    conn.commit()
    conn.close()


class Midman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tickets = {}
        self.restored = False
        self.ticket_timeout_check.start()
        self.auto_backup.start()

    def cog_unload(self):
        self.ticket_timeout_check.cancel()
        self.auto_backup.cancel()

    @tasks.loop(hours=6)
    async def auto_backup(self):
        await do_backup(self.bot, BACKUP_CHANNEL_ID)

    @auto_backup.before_loop
    async def before_auto_backup(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(6 * 3600)  # skip backup saat startup, tunggu 6 jam dulu

    @tasks.loop(minutes=10)
    async def ticket_timeout_check(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        for ch_id, ticket in list(self.active_tickets.items()):
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                continue
            channel = guild.get_channel(ch_id)
            if not channel:
                continue
            last_msg_time = None
            async for msg in channel.history(limit=1):
                last_msg_time = msg.created_at
            check_time = last_msg_time or ticket.get("opened_at")
            if not check_time:
                continue
            if isinstance(check_time, str):
                check_time = datetime.datetime.fromisoformat(check_time)
            if check_time.tzinfo is None:
                check_time = check_time.replace(tzinfo=datetime.timezone.utc)
            delta = (now - check_time).total_seconds()
            if delta >= 7200:
                try:
                    await channel.send(
                        "Tiket ini otomatis ditutup karena tidak ada aktivitas selama 2 jam. "
                        "Transaksi dianggap batal. Channel akan dihapus dalam 10 detik."
                    )
                    await asyncio.sleep(10)
                    await channel.delete()
                except Exception:
                    pass
                del self.active_tickets[ch_id]
                save_tickets(self.active_tickets)
            elif delta >= 3600 and not ticket.get("warned"):
                try:
                    old_warn_id = ticket.get("warn_message_id")
                    if old_warn_id:
                        try:
                            old_msg = await channel.fetch_message(old_warn_id)
                            await old_msg.delete()
                        except Exception:
                            pass
                    warn_embed = discord.Embed(title="PERINGATAN TIKET", color=0xFFA500)
                    warn_embed.add_field(name="\u200b", value=(
                        "Tiket tidak ada aktivitas selama **1 jam**.\n\n"
                        "Segera ketik `!acc` jika selesai, atau `!batal` jika dibatalkan.\n\n"
                        "Tiket akan otomatis ditutup dalam **1 jam lagi** (<t:" + str(int(time.time()) + 3600) + ":R>)."
                    ), inline=False)
                    warn_embed.set_footer(text=STORE_NAME)
                    _p1 = ticket.get("pihak1")
                    _p2 = ticket.get("pihak2")
                    _adm = ticket.get("admin")
                    _mn = " ".join(filter(None, [
                        _p1.mention if _p1 else None,
                        _p2.mention if _p2 else None,
                        _adm.mention if _adm else None,
                    ]))
                    warn_msg = await channel.send(content=_mn, embed=warn_embed)
                    ticket["warn_message_id"] = warn_msg.id
                except Exception:
                    pass
                ticket["warned"] = True
                save_tickets(self.active_tickets)

    @ticket_timeout_check.before_loop
    async def before_timeout_check(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRole):
            return
        if isinstance(error, commands.CommandNotFound):
            return
        err_ch = ctx.guild.get_channel(ERROR_LOG_CHANNEL_ID)
        if err_ch:
            await err_ch.send(
                f"ERROR LOG\n"
                f"Error pada command `{ctx.command}` oleh {ctx.author.mention}:\n"
                f"`{error}`"
            )
        print(f"[ERROR] {ctx.command}: {error}")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.restored:
            await do_restore(self.bot, BACKUP_CHANNEL_ID)
            from utils.db import init_db
            init_db()
            self.restored = True

        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            await load_tickets(guild, self.active_tickets)
        self.bot.add_view(MidmanMainView())
        self.bot.add_view(AdminSetupView())
        self.bot.add_view(TradeFinishView())
        self.bot.start_time = datetime.datetime.now(datetime.timezone.utc)
        print("Cog Midman siap.")

    @commands.command(name="open")
    async def open_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        try:
            await ctx.message.delete()
        except Exception as e:
            print(f"[WARNING] cogs/midman.py: {e}")
            pass
        ch = ctx.guild.get_channel(MIDMAN_CHANNEL_ID)

        # Hapus semua pesan bot lama di channel
        async for msg in ch.history(limit=50):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception as e:
                    print(f"[WARNING] cogs/midman.py: {e}")
                    pass

        embed = discord.Embed(
            title=f"MIDMAN TRADE — {STORE_NAME}",
            description=(
                "Jasa perantara transaksi item game dengan aman bersama Cellyn Store.\n\n"
                "⚔️ **Midman Trade** — Tukar item/akun antar dua pihak\n"
                "Cara pakai: Klik tombol **Midman Trade** → isi form → tunggu admin bergabung\n\n"
                "🛒 **Midman Jual Beli** — Jual/beli item dengan admin sebagai perantara dana\n"
                "Cara pakai: Klik tombol **Midman Jual Beli** → isi form → tunggu admin setup"
            ),
            color=0x2ECC71
        )
        embed.add_field(
            name="📋 Daftar Fee Midman",
            value=(
                "```"
                "Nominal Trade        Fee\n"
                "─────────────────────────\n"
                "< Rp 10.000          Rp 1.500\n"
                "Rp 10.000 – 49.000   Rp 2.500\n"
                "Rp 50.000 – 99.000   Rp 4.500\n"
                "Rp 100.000 – 199.000 Rp 6.500\n"
                "Rp 200.000 – 499.000 Rp 10.000\n"
                "Rp 500.000 – 1 jt    Rp 15.000\n"
                "> Rp 1.000.000       Rp 20.000"
                "```"
            ),
            inline=False
        )
        embed.set_footer(text=STORE_NAME)
        msg = await ch.send(embed=embed, view=MidmanMainView(store_open=is_store_open()))
        _set_setting("midman_catalog_message_id", str(msg.id))
        await ctx.send(f"Embed dikirim ke {ch.mention}", delete_after=5)

    async def refresh_open_embed(self):
        """Enable/disable midman catalog buttons based on store open/close."""
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        ch = guild.get_channel(MIDMAN_CHANNEL_ID)
        if not ch:
            return
        msg_id_raw = _get_setting("midman_catalog_message_id") or ""
        msg = None
        if msg_id_raw.isdigit():
            try:
                msg = await ch.fetch_message(int(msg_id_raw))
            except Exception:
                msg = None
        if not msg:
            async for m in ch.history(limit=25):
                if m.author == guild.me and m.embeds:
                    title = (m.embeds[0].title or "").upper()
                    if "MIDMAN" in title:
                        msg = m
                        break
        if not msg:
            return
        try:
            await msg.edit(view=MidmanMainView(store_open=is_store_open()))
        except Exception:
            pass

    @commands.command(name="acc")
    async def acc(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        ticket = self.active_tickets.get(ctx.channel.id)
        if not ticket:
            await ctx.message.delete()
            return
        try:
            await ctx.message.delete()
        except Exception as e:
            print(f"[WARNING] cogs/midman.py: {e}")
            pass
        ticket["closed_at"] = datetime.datetime.now(datetime.timezone.utc)
        p1 = ticket.get("pihak1")
        p2 = ticket.get("pihak2")
        adm = ticket.get("admin")
        if not p2 or not adm:
            await ctx.send("Tiket belum di-setup penuh oleh admin. Tidak bisa dikonfirmasi.", ephemeral=False)
            return
        ticket_num = str(ticket.get("ticket_number", 0)).zfill(4)
        opened_at = ticket.get("opened_at")
        closed_at = ticket.get("closed_at")
        durasi = "-"
        if opened_at and closed_at:
            delta = closed_at - opened_at
            total = int(delta.total_seconds())
            jam = total // 3600
            menit = (total % 3600) // 60
            detik = total % 60
            if jam > 0:
                durasi = f"{jam} jam {menit} menit"
            elif menit > 0:
                durasi = f"{menit} menit {detik} detik"
            else:
                durasi = f"{detik} detik"
        opened_at.strftime("%d %b %Y, %H:%M UTC") if opened_at else "-"
        closed_at.strftime("%d %b %Y, %H:%M UTC") if closed_at else "-"
        ticket.get("verified_by")
        _midman_item = f"{ticket.get('item_p1', '-')} ↔ {ticket.get('item_p2', '-')}"
        await ctx.send(embed=ticket_ui.ticket_success_embed(
            "Admin telah mengkonfirmasi trade selesai & kedua pihak menerima item masing-masing."
        ))
        await asyncio.sleep(5)
        transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
        # Log transaksi (flat text + auto-update garansi setelah rating)
        from utils.db import log_transaction, set_transaction_log_message
        from utils.config import TESTIMONI_CHANNEL_ID
        opened_at_dt = datetime.datetime.fromisoformat(ticket["opened_at"]) if ticket.get("opened_at") else None
        durasi = int((closed_at - opened_at_dt).total_seconds()) if opened_at_dt and closed_at else 0
        tx_id = None
        try:
            tx_id = log_transaction(
                layanan="midman",
                nominal=ticket.get("fee_final", 0) or 0,
                item=_midman_item,
                admin_id=ctx.author.id,
                user_id=ticket.get("pihak1_id"),
                closed_at=closed_at,
                durasi_detik=durasi,
                qty=1,
            )
        except Exception:
            pass
        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            text = ticket_ui.success_log_text(
                seller=p1.mention if p1 else "-",
                buyer=p2.mention if p2 else "-",
                product=_midman_item,
                qty=1,
                harga=ticket.get("fee_final", 0) or 0,
                rating=None,
                rating_channel_id=TESTIMONI_CHANNEL_ID,
            )
            try:
                msg = await log_ch.send(text)
                if tx_id:
                    set_transaction_log_message(tx_id, log_ch.id, msg.id)
            except Exception as e:
                print(f"[Midman] Gagal kirim log: {e}")

        # Refresh leaderboard Top Spender (transaksi baru tercatat)
        try:
            from cogs.top_spender import refresh_top_spender
            await refresh_top_spender(self.bot)
        except Exception as e:
            print(f"[TopSpender] refresh error (Midman): {e}")

        transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            await transcript_ch.send(
                content=f"Transcript #{ticket_num} — {ctx.channel.name}",
                file=transcript_file
            )
        del self.active_tickets[ctx.channel.id]
        save_tickets(self.active_tickets)
        await ctx.channel.delete()

    @commands.command(name="batal")
    async def cancel(self, ctx, *, alasan: str = "Tidak ada alasan diberikan."):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        ticket = self.active_tickets.get(ctx.channel.id)
        if not ticket:
            await ctx.send("Channel ini bukan tiket aktif.", delete_after=5)
            return
        embed = ticket_ui.ticket_cancel_embed(
            by_mention=ctx.author.mention, reason=alasan
        )
        p1 = ticket.get("pihak1")
        p2 = ticket.get("pihak2")
        mentions = " ".join(filter(None, [
            p1.mention if p1 else None,
            p2.mention if p2 else None
        ]))
        await ctx.send(content=mentions if mentions else None, embed=embed)
        await asyncio.sleep(5)
        if ctx.channel.id in self.active_tickets:
            del self.active_tickets[ctx.channel.id]
            save_tickets(self.active_tickets)
        await ctx.channel.delete()

    @commands.command(name="ping")
    async def ping(self, ctx):
        await ctx.message.delete()
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! Latency: {latency}ms")

    @commands.command(name="fee")
    async def fee(self, ctx, nominal: str):
        try:
            await ctx.message.delete()
        except Exception as e:
            print(f"[WARNING] cogs/midman.py: {e}")
            pass
        try:
            angka = int(nominal.replace(".", "").replace(",", "").replace("k", "000").replace("K", "000"))
        except ValueError:
            await ctx.send("Format salah. Contoh: !fee 50000 atau !fee 50k")
            return
        result = hitung_fee(angka)
        if result is None:
            await ctx.send("Nominal terlalu kecil. Minimal Rp 1.000.")
            return
        embed = discord.Embed(title="Kalkulator Fee Midman", color=0x2ECC71)
        embed.add_field(name="Nominal", value=format_nominal(angka), inline=True)
        embed.add_field(name="Fee", value=format_nominal(result), inline=True)
        embed.add_field(name="Total Bayar", value=format_nominal(angka + result), inline=True)
        embed.set_footer(text=STORE_NAME)
        await ctx.send(embed=embed, delete_after=30)

    @commands.command(name="cmd")
    async def cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        embed = discord.Embed(
            title=f"PREFIX GUIDE — {STORE_NAME}",
            color=0x2ECC71
        )
        embed.add_field(
            name="MIDMAN TRADE",
            value=(
                "`!open` — kirim embed catalog\n"
                "`!acc` — konfirmasi trade selesai\n"
                "`!batal` — batalkan tiket\n"
                "`!fee <nominal>` — hitung fee midman"
            ),
            inline=False
        )
        embed.add_field(
            name="GP TOPUP",
            value=(
                "`!gpcatalog` — kirim embed catalog GP Topup\n"
                "`!gprate <angka>` — set rate GP\n"
                "`!gplink <link>` — kirim/atur link gamepass\n"
                "`!gpdone` — konfirmasi gamepass sudah dibeli\n"
                "`!gpbatal [alasan]` — batalkan tiket GP"
            ),
            inline=False
        )
        embed.add_field(
            name="ROBUX STORE",
            value=(
                "`!catalog` — kirim embed catalog robux\n"
                "`!rate <angka>` — set rate Robux\n"
                "`!stock` — lihat stock robux\n"
                "`!stockset <robux>` — set stock tersedia\n"
                "`!stockadd <robux>` — tambah stock tersedia\n"
                "`!stockoutadd <robux>` — tambah robux keluar (total)\n"
                "`!stockoutship <robux>` — robux keluar + kurangi stock\n"
                "`!gift` — konfirmasi gift item selesai\n"
                "`!tolak [alasan]` — batalkan tiket robux"
            ),
            inline=False
        )
        embed.add_field(
            name="ROBUX VIA LOGIN (VILOG)",
            value=(
                "`!vilogcatalog` — kirim/refresh embed Vilog\n"
                "`!ratevilog <angka>` — set rate Vilog\n"
                "`!vilogdone` — konfirmasi Vilog selesai\n"
                "`!vilogbatal [alasan]` — batalkan tiket Vilog"
            ),
            inline=False
        )
        embed.add_field(
            name="TOPUP MOBILE LEGENDS",
            value=(
                "`!mlcatalog` — kirim embed catalog ML\n"
                "`!mlselesai` — konfirmasi topup selesai\n"
                "`!mlbatal [alasan]` — batalkan tiket ML"
            ),
            inline=False
        )
        embed.add_field(
            name="MIDMAN JUAL BELI",
            value=(
                "`!jbuang` — konfirmasi uang dari pembeli diterima\n"
                "`!jbselesai` — release dana ke penjual\n"
                "`!jbbatal [alasan]` — batalkan tiket jual beli"
            ),
            inline=False
        )
        embed.add_field(
            name="CLOUD PHONE & DISCORD NITRO",
            value=(
                "`!lainnya` — kirim katalog Cloud Phone & Nitro\n"
                "`!done` — tutup tiket sukses\n"
                "`!cancel [alasan]` — batalkan tiket"
            ),
            inline=False
        )
        embed.add_field(
            name="LAINNYA",
            value=(
                "`!relay <on/off/status>` — toggle relay webhook"
            ),
            inline=False
        )
        embed.add_field(
            name="ANTRIAN TIKET",
            value=(
                "`!antrianboard` — jadikan channel ini Papan Antrian\n"
                "`!antrianrefresh` — paksa perbarui antrian sekarang\n"
                "`!antriancards <on/off>` — kartu posisi antrean customer\n"
                "`!antrianoff` — nonaktifkan papan antrian\n"
                "`!pay` — tandai tiket ini sedang diproses (di channel tiket)\n"
                "`!unpay` — batalkan tanda 'sedang diproses' (undo !pay)"
            ),
            inline=False
        )
        embed.add_field(
            name="GARANSI",
            value=(
                "`!garansi` — pasang panel klaim garansi\n"
                "`!garansiclose` — tutup tiket klaim garansi"
            ),
            inline=False
        )
        embed.add_field(
            name="LAPORAN & STATISTIK",
            value=(
                "`!laporan [YYYY-MM-DD]` — kirim laporan harian (default: kemarin)"
            ),
            inline=False
        )
        embed.add_field(
            name="UTILITAS",
            value=(
                "`!cmd` — tampilkan panduan prefix ini\n"
                "`!afk [alasan]` — set status AFK\n"
                "`!ping` — cek latency bot"
            ),
            inline=False
        )
        embed.add_field(
            name="INFO GAME GRATIS",
            value=(
                "`!freegames` (`!fg`) — cek game gratis PC (Epic/Steam/GOG/Ubisoft)\n"
                "`!mobilegames` (`!mg`) — cek game gratis Android & iOS\n"
                "`!genshin` (`!gi`) — info Genshin: `events`, `banners`, `codes`"
            ),
            inline=False
        )
        embed.set_footer(text=f"{STORE_NAME} • Pesan ini akan hilang dalam 60 detik")
        await ctx.send(embed=embed, delete_after=60)

async def setup(bot):
    await bot.add_cog(Midman(bot))
