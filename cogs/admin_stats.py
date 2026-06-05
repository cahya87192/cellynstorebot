"""Statistik performa admin (PUBLIK, all-time).

Menampilkan satu kartu embed per admin (gaya kartu rating) yang nempel &
auto-update di channel publik: nama admin, foto profil, rating yang ia peroleh
dari pembeli, dan total transaksi yang ia tangani — akumulasi SEPANJANG MASA.

Sesuai keputusan: TIDAK menampilkan waktu proses maupun omzet (itu data
operasional internal, kurang pas untuk konsumsi publik). Rating per admin
dihitung dari tabel `reviews` yang dihubungkan ke `transaction_log.admin_id`
lewat `tx_id`.
"""

import json

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.config import ADMIN_ROLE_ID, STORE_NAME
from utils.db import get_conn

# Channel publik tempat kartu performa admin dipajang (bisa di-override via
# /setadminstatschannel; nilai ini jadi default).
DEFAULT_ADMIN_STATS_CHANNEL_ID = 1512224258565079130

COLOR_ADMIN_STATS = 0x5865F2
UPDATE_INTERVAL_MINUTES = 15
EMBEDS_PER_MESSAGE = 10  # batas embed per pesan Discord

_CHANNEL_KEY = "admin_stats_channel_id"
_MSG_IDS_KEY = "admin_stats_message_ids"


# ── bot_state helpers ─────────────────────────────────────────────
def _get_setting(key):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else None


def _set_setting(key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()


# ── Data ──────────────────────────────────────────────────────────
def get_admin_stats(admin_id: int) -> dict:
    """Statistik all-time seorang admin: total transaksi + rating yang diperoleh.

    Return {'total_tx', 'rating_avg', 'rating_count'}. Aman bila tabel reviews
    belum ada / admin belum punya transaksi (nilai 0).
    """
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) AS n FROM transaction_log WHERE admin_id = ?", (admin_id,))
    total_tx = c.fetchone()["n"] or 0

    rating_avg = 0.0
    rating_count = 0
    try:
        c.execute(
            """
            SELECT COUNT(*) AS n, AVG(r.rating) AS avg
            FROM reviews r
            JOIN transaction_log t ON t.id = r.tx_id
            WHERE t.admin_id = ? AND r.rating IS NOT NULL
            """,
            (admin_id,),
        )
        row = c.fetchone()
        rating_count = row["n"] or 0
        rating_avg = round(row["avg"], 2) if row["avg"] is not None else 0.0
    except Exception:
        pass

    conn.close()
    return {"total_tx": total_tx, "rating_avg": rating_avg, "rating_count": rating_count}


def build_admin_embed(member: discord.Member, stats: dict) -> discord.Embed:
    """Kartu performa satu admin (gaya kartu rating). Foto profil jadi thumbnail."""
    rating_avg = stats.get("rating_avg", 0.0)
    rating_count = stats.get("rating_count", 0)
    full = max(0, min(5, int(round(rating_avg))))
    star_line = "⭐" * full + "☆" * (5 - full)

    if rating_count:
        rating_text = f"**{star_line}**  ·  {rating_avg:.2f}/5  ({rating_count} rating)"
    else:
        rating_text = f"**{star_line}**  ·  _belum ada rating_"

    embed = discord.Embed(
        title="⟡ KINERJA ADMIN",
        description=f"**{member.display_name}**\n{rating_text}",
        color=COLOR_ADMIN_STATS,
    )
    embed.add_field(name="◈ Total Transaksi", value=f"{stats.get('total_tx', 0)}x", inline=True)
    try:
        embed.set_thumbnail(url=member.display_avatar.url)
    except Exception:
        pass
    embed.set_footer(text=f"{STORE_NAME} · statistik sepanjang masa")
    return embed


def build_header_embed() -> discord.Embed:
    return discord.Embed(
        title=f"📊 Tim Admin Terpercaya — {STORE_NAME}",
        description=(
            "Statistik pelayanan tiap admin (akumulasi sepanjang masa).\n"
            "Transparansi untuk kenyamanan & kepercayaan kamu saat berbelanja. 🤝"
        ),
        color=COLOR_ADMIN_STATS,
    )


# ── COG ───────────────────────────────────────────────────────────
class AdminStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._channel_id = int(_get_setting(_CHANNEL_KEY) or DEFAULT_ADMIN_STATS_CHANNEL_ID)
        self.update_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()

    @tasks.loop(minutes=UPDATE_INTERVAL_MINUTES)
    async def update_loop(self):
        try:
            await self._update()
        except Exception as e:
            print(f"[AdminStats] update loop error: {e}")

    @update_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    def _admin_members(self, guild: discord.Guild):
        role = guild.get_role(ADMIN_ROLE_ID)
        if role is None:
            return []
        return [m for m in role.members if not m.bot]

    def _build_payloads(self, guild: discord.Guild):
        """Susun daftar pesan: [header] lalu kartu admin (maks 10 embed/pesan)."""
        admins = self._admin_members(guild)
        enriched = [(m, get_admin_stats(m.id)) for m in admins]
        # Urut: transaksi terbanyak dulu, lalu rating tertinggi.
        enriched.sort(key=lambda x: (x[1]["total_tx"], x[1]["rating_avg"]), reverse=True)
        cards = [build_admin_embed(m, s) for m, s in enriched]

        payloads = [[build_header_embed()]]
        for i in range(0, len(cards), EMBEDS_PER_MESSAGE):
            payloads.append(cards[i:i + EMBEDS_PER_MESSAGE])
        return payloads

    async def _update(self):
        if not self._channel_id:
            return
        channel = self.bot.get_channel(self._channel_id)
        if channel is None:
            return

        payloads = self._build_payloads(channel.guild)

        raw = _get_setting(_MSG_IDS_KEY)
        try:
            msg_ids = json.loads(raw) if raw else []
        except Exception:
            msg_ids = []

        new_ids = []
        for i, embeds in enumerate(payloads):
            edited = False
            if i < len(msg_ids):
                try:
                    msg = await channel.fetch_message(msg_ids[i])
                    await msg.edit(embeds=embeds)
                    new_ids.append(msg.id)
                    edited = True
                except discord.NotFound:
                    edited = False
                except Exception as e:
                    print(f"[AdminStats] edit msg error: {e}")
                    edited = True
                    new_ids.append(msg_ids[i])
            if not edited:
                try:
                    msg = await channel.send(embeds=embeds)
                    new_ids.append(msg.id)
                except Exception as e:
                    print(f"[AdminStats] send msg error: {e}")

        # Hapus pesan sisa (mis. jumlah admin berkurang -> butuh lebih sedikit pesan).
        for extra_id in msg_ids[len(payloads):]:
            try:
                m = await channel.fetch_message(extra_id)
                await m.delete()
            except Exception:
                pass

        _set_setting(_MSG_IDS_KEY, json.dumps(new_ids))

    # ── Slash commands (admin) ────────────────────
    @app_commands.command(name="refreshadminstats", description="[ADMIN] Perbarui kartu performa admin sekarang")
    async def refresh_cmd(self, interaction: discord.Interaction):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self._update()
        await interaction.followup.send("✅ Kartu performa admin diperbarui.", ephemeral=True)

    @app_commands.command(name="setadminstatschannel", description="[ADMIN] Set channel kartu performa admin")
    @app_commands.describe(channel="Channel tujuan")
    async def set_channel_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        self._channel_id = channel.id
        _set_setting(_CHANNEL_KEY, str(channel.id))
        _set_setting(_MSG_IDS_KEY, "")  # reset pesan lama, akan dibuat ulang di channel baru
        await interaction.response.defer(ephemeral=True)
        await self._update()
        await interaction.followup.send(
            f"✅ Channel performa admin diset ke {channel.mention} & kartu dibuat.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminStats(bot))
    print("Cog AdminStats siap.")
