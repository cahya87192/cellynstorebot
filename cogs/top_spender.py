"""
Top Spender Monthly Leaderboard
- Auto update & edit embed tiap 30 menit
- Top 20 ditampilkan
- Role ID 1508950886251106517 diberikan ke top 1-10
- Reset pesan leaderboard tiap awal bulan (tanpa pengumuman pemenang)
"""

import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.config import ADMIN_ROLE_ID, STORE_NAME, TOP_SPENDER_BADGE, TOP_SPENDER_ROLE_ID
from utils.db import get_conn

TOP_SPENDER_TOP_N   = 10
LEADERBOARD_LIMIT   = 20

MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}


def _rupiah(n) -> str:
    """Format Rupiah gaya Indonesia: 1000000 -> 'Rp 1.000.000'."""
    try:
        return f"Rp {int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return f"Rp {n}"


# ─────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────
def _init_tables():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS manual_spending (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            nominal    INTEGER NOT NULL,
            note       TEXT,
            added_by   INTEGER,
            added_at   TEXT NOT NULL
        )
    ''')
    # Catatan: tabel bot_state sudah dibuat di utils/db.py init_db() yang dipanggil
    # main.init_database() sebelum cog di-load, jadi tidak perlu dibuat ulang di sini.
    conn.commit()
    conn.close()


def _get_setting(key):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row['value'] if row else None


def _set_setting(key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()


def get_top_spenders(year: int, month: int, limit: int = 20) -> list[dict]:
    conn = get_conn()
    c = conn.cursor()

    start = f"{year:04d}-{month:02d}-01"
    end   = f"{year+1:04d}-01-01" if month == 12 else f"{year:04d}-{month+1:02d}-01"

    c.execute('''
        SELECT user_id, SUM(nominal) as total
        FROM transaction_log
        WHERE user_id IS NOT NULL
          AND closed_at >= ? AND closed_at < ?
        GROUP BY user_id
    ''', (start, end))
    combined = {row['user_id']: row['total'] for row in c.fetchall()}

    c.execute('''
        SELECT user_id, SUM(nominal) as total
        FROM manual_spending
        WHERE added_at >= ? AND added_at < ?
        GROUP BY user_id
    ''', (start, end))
    for row in c.fetchall():
        combined[row['user_id']] = combined.get(row['user_id'], 0) + row['total']

    conn.close()

    sorted_list = sorted(combined.items(), key=lambda x: x[1], reverse=True)
    return [{"user_id": uid, "total": total} for uid, total in sorted_list[:limit]]


# ─────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────
class TopSpender(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _init_tables()
        self._channel_id = int(_get_setting("topspender_channel_id") or 0) or None
        self._message_id = int(_get_setting("topspender_message_id") or 0) or None
        self.update_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()

    # ── Loop tiap 30 menit ────────────────────
    @tasks.loop(minutes=30)
    async def update_loop(self):
        if not self._channel_id:
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        month_key = f"{now.year}-{now.month:02d}"

        # Awal bulan: reset pesan leaderboard supaya bulan baru pakai pesan baru.
        # Tidak ada pengumuman pemenang — Top Spender bukan ajang lomba, jadi
        # leaderboard cukup diperbarui diam-diam (silent).
        last_reset = _get_setting("topspender_last_reset")
        if last_reset != month_key and now.day == 1:
            _set_setting("topspender_last_reset", month_key)
            self._message_id = None
            _set_setting("topspender_message_id", "")

        await self._update_leaderboard(now.year, now.month)

    @update_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    # ── Update/edit embed ─────────────────────
    async def _update_leaderboard(self, year: int, month: int):
        channel = self.bot.get_channel(self._channel_id)
        if not channel:
            return

        spenders = get_top_spenders(year, month, LEADERBOARD_LIMIT)
        month_name = datetime.date(year, month, 1).strftime("%B %Y")
        embed = self._build_embed(spenders, month_name, channel.guild)

        try:
            if self._message_id:
                try:
                    msg = await channel.fetch_message(self._message_id)
                    await msg.edit(embed=embed)
                    await self._update_roles(spenders, channel.guild)
                    return
                except discord.NotFound:
                    self._message_id = None

            msg = await channel.send(embed=embed)
            self._message_id = msg.id
            _set_setting("topspender_message_id", str(msg.id))
            await self._update_roles(spenders, channel.guild)

        except Exception as e:
            print(f"[TopSpender] Update error: {e}")

    # ── Refresh segera (dipanggil setelah transaksi berhasil) ──
    async def refresh_now(self):
        """Update leaderboard bulan berjalan SEGERA, tanpa menunggu loop 30 menit.

        Dipanggil otomatis oleh cog layanan tiap kali ada transaksi berhasil
        (lihat helper modul `refresh_top_spender`). Aman bila channel leaderboard
        belum di-set (langsung no-op) maupun bila dipanggil beruntun.
        """
        if not self._channel_id:
            return
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            await self._update_leaderboard(now.year, now.month)
        except Exception as e:
            print(f"[TopSpender] refresh_now error: {e}")

    # ── Update role top 1-10 ──────────────────
    async def _update_roles(self, spenders: list[dict], guild: discord.Guild):
        top_role = guild.get_role(TOP_SPENDER_ROLE_ID)
        if not top_role:
            return

        entitled_ids = {s['user_id'] for s in spenders[:TOP_SPENDER_TOP_N]}

        # Hanya proses anggota yang relevan, bukan iterasi seluruh guild.members:
        #  - yang SAAT INI punya role (kandidat dicabut), via top_role.members
        #  - yang BERHAK punya role (kandidat ditambah), via entitled_ids
        current_holder_ids = {m.id for m in top_role.members}

        # Cabut role dari yang tidak lagi berhak.
        for member in top_role.members:
            if member.id not in entitled_ids:
                try:
                    await member.remove_roles(top_role, reason="Top Spender update")
                except Exception as e:
                    print(f"[TopSpender] Role remove error {member.id}: {e}")

        # Tambahkan role ke yang berhak tapi belum punya.
        for uid in entitled_ids - current_holder_ids:
            member = guild.get_member(uid)
            if member is None:
                continue
            try:
                await member.add_roles(top_role, reason="Top Spender update")
            except Exception as e:
                print(f"[TopSpender] Role add error {uid}: {e}")

    # ── Build embed ───────────────────────────
    def _build_embed(self, spenders: list[dict], month_name: str,
                     guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(
            title=f"🏆 Top Spender — {month_name}",
            description=f"Apresiasi untuk pelanggan setia {STORE_NAME} 💛\n*(diperbarui otomatis tiap ada transaksi)*",
            color=0xF0A500,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        if not spenders:
            embed.add_field(name="\u200b", value="Belum ada data transaksi bulan ini.", inline=False)
            embed.add_field(
                name="✨ Benefit Jadi Top Spender",
                value=(
                    "👑 Role eksklusif Top Spender (khusus Top 10)\n"
                    "⚡ Prioritas antrean — pesananmu didahulukan di semua layanan\n"
                    "🤝 Diutamakan admin saat tiket sedang ramai"
                ),
                inline=False,
            )
            embed.set_footer(text=f"{STORE_NAME} • Reset tiap awal bulan")
            return embed

        top_lines, rest_lines = [], []
        # Badge mahkota untuk baris Top-N. Pakai emoji server (TOP_SPENDER_BADGE)
        # bila di-set; jatuh ke 👑 unicode bila kosong. Custom emoji render normal
        # di VALUE field embed (beda dgn name/title yang tidak me-render).
        crown = TOP_SPENDER_BADGE or "👑"
        for i, s in enumerate(spenders, 1):
            member = guild.get_member(s['user_id'])
            name   = member.display_name if member else f"User {s['user_id']}"
            rupiah = _rupiah(s['total'])
            if i <= TOP_SPENDER_TOP_N:
                rank = MEDAL.get(i, f"`#{i:02d}`")
                top_lines.append(f"{rank} **{name}** {crown} — {rupiah}")
            else:
                rest_lines.append(f"`#{i:02d}` {name} — {rupiah}")

        embed.add_field(
            name=f"👑 Top {TOP_SPENDER_TOP_N} (dapat role spesial)",
            value="\n".join(top_lines)[:1024],
            inline=False,
        )
        if rest_lines:
            embed.add_field(
                name="Peringkat selanjutnya",
                value="\n".join(rest_lines)[:1024],
                inline=False,
            )

        total_all = sum(s['total'] for s in spenders)
        embed.add_field(
            name="✨ Benefit Jadi Top Spender",
            value=(
                "👑 Role eksklusif Top Spender (khusus Top 10)\n"
                "⚡ Prioritas antrean — pesananmu didahulukan di semua layanan\n"
                "🤝 Diutamakan admin saat tiket sedang ramai"
            ),
            inline=False,
        )
        embed.add_field(
            name="\u200b",
            value=f"────────────────────\n💰 **Total belanja Top {len(spenders)}** — {_rupiah(total_all)}",
            inline=False,
        )
        embed.set_footer(text=f"{STORE_NAME} • Reset tiap awal bulan")
        return embed

    # ── Slash commands ────────────────────────

    @app_commands.command(name="topspender", description="Lihat leaderboard top spender bulan ini")
    async def topspender(self, interaction: discord.Interaction):
        await interaction.response.defer()
        now = datetime.datetime.now(datetime.timezone.utc)
        spenders = get_top_spenders(now.year, now.month, LEADERBOARD_LIMIT)
        month_name = datetime.date(now.year, now.month, 1).strftime("%B %Y")
        embed = self._build_embed(spenders, month_name, interaction.guild)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="addspending", description="[ADMIN] Tambah manual spending untuk member")
    @app_commands.describe(member="Member yang ditambah spendingnya", nominal="Jumlah nominal (Rupiah)", note="Catatan (opsional)")
    async def addspending(self, interaction: discord.Interaction,
                          member: discord.Member, nominal: int, note: str = ""):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO manual_spending (user_id, nominal, note, added_by, added_at) VALUES (?,?,?,?,?)",
            (member.id, nominal, note, interaction.user.id,
             datetime.datetime.now(datetime.timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            f"✅ Ditambahkan spending **{_rupiah(nominal)}** untuk {member.mention}"
            + (f" — `{note}`" if note else ""),
            ephemeral=True
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        await self._update_leaderboard(now.year, now.month)

    @app_commands.command(name="subspend", description="[ADMIN] Kurangi spending manual member")
    @app_commands.describe(member="Member yang dikurangi spendingnya", nominal="Jumlah nominal untuk dikurangi (Rupiah)", note="Catatan (opsional)")
    async def subspend(self, interaction: discord.Interaction,
                       member: discord.Member, nominal: int, note: str = ""):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO manual_spending (user_id, nominal, note, added_by, added_at) VALUES (?,?,?,?,?)",
            (member.id, -nominal, note, interaction.user.id,
             datetime.datetime.now(datetime.timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            f"✅ Berhasil mengurangi spending **{_rupiah(nominal)}** dari {member.mention}"
            + (f" — `{note}`" if note else ""),
            ephemeral=True
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        await self._update_leaderboard(now.year, now.month)

    @app_commands.command(name="refreshspender", description="[ADMIN] Force update leaderboard sekarang")
    async def refreshspender(self, interaction: discord.Interaction):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        now = datetime.datetime.now(datetime.timezone.utc)
        await self._update_leaderboard(now.year, now.month)
        await interaction.followup.send("✅ Leaderboard diperbarui.", ephemeral=True)

    @app_commands.command(name="settopspenderchannel", description="[ADMIN] Set channel untuk leaderboard top spender")
    @app_commands.describe(channel="Channel tujuan leaderboard")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        self._channel_id = channel.id
        self._message_id = None
        _set_setting("topspender_channel_id", str(channel.id))
        _set_setting("topspender_message_id", "")
        await interaction.response.send_message(
            f"✅ Channel leaderboard diset ke {channel.mention}", ephemeral=True
        )

    @app_commands.command(name="forcereset", description="[ADMIN] Force post leaderboard bulan tertentu")
    @app_commands.describe(year="Tahun (misal: 2026)", month="Bulan (1-12)")
    async def forcereset(self, interaction: discord.Interaction, year: int, month: int):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self._post_leaderboard(year, month, auto=True)
        await interaction.followup.send(
            f"✅ Leaderboard {month:02d}/{year} berhasil dipost.", ephemeral=True
        )

    # Tetap ada untuk backward compat dengan forcereset
    async def _post_leaderboard(self, year: int, month: int, auto: bool = False,
                                 channel: discord.TextChannel = None):
        ch = channel or (self.bot.get_channel(self._channel_id) if self._channel_id else None)
        if not ch:
            return
        spenders = get_top_spenders(year, month, LEADERBOARD_LIMIT)
        month_name = datetime.date(year, month, 1).strftime("%B %Y")
        embed = self._build_embed(spenders, month_name, ch.guild)
        await ch.send(embed=embed)
        if auto:
            await self._update_roles(spenders, ch.guild)


async def refresh_top_spender(bot):
    """Trigger refresh leaderboard Top Spender dari cog manapun.

    Dipakai cog layanan setelah mencatat transaksi (log_transaction) supaya
    leaderboard langsung diperbarui tanpa menunggu loop 30 menit. Aman dipanggil
    walau cog TopSpender belum ter-load atau channel leaderboard belum di-set.
    """
    cog = bot.get_cog("TopSpender")
    if cog is not None:
        await cog.refresh_now()


def is_top_spender(user_id: int, when: datetime.datetime = None) -> bool:
    """True bila user_id termasuk Top-N spender bulan berjalan (berbasis DATA).

    Deteksi dari transaksi (bukan role), konsisten dengan prioritas antrian.
    Aman dipanggil dari mana saja; return False bila terjadi error/akses gagal.
    """
    if not user_id:
        return False
    try:
        now = when or datetime.datetime.now(datetime.timezone.utc)
        top = get_top_spenders(now.year, now.month, TOP_SPENDER_TOP_N)
        return any(s["user_id"] == user_id for s in top)
    except Exception as e:
        print(f"[TopSpender] is_top_spender error: {e}")
        return False


def top_spender_badge(user_id: int, when: datetime.datetime = None) -> str:
    """Kembalikan badge Top Spender (config.TOP_SPENDER_BADGE) bila user_id Top-N,
    selain itu string kosong. Dipakai untuk menempel badge di log transaksi.
    """
    if not TOP_SPENDER_BADGE:
        return ""
    return TOP_SPENDER_BADGE if is_top_spender(user_id, when) else ""


async def setup(bot: commands.Bot):
    await bot.add_cog(TopSpender(bot))
