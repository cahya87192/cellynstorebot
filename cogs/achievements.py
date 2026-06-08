"""Achievement / Badge member — /badges.

Menampilkan badge yang sudah & belum diraih member berdasarkan statistik
profil (utils.profile.get_member_profile). Logika penentuan badge murni ada di
utils/achievements.py (teruji terpisah, tanpa Discord).

Command:
  - /badges            : lihat badge sendiri
  - /badges member:@x  : (admin) lihat badge member lain
"""

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import ADMIN_ROLE_ID, STORE_NAME
from utils import profile as profilelib
from utils import achievements as achlib

COLOR_BADGE = 0xF1C40F  # emas
MAX_LOCKED = 6


def _is_admin(member) -> bool:
    return any(r.id == ADMIN_ROLE_ID for r in getattr(member, "roles", []))


def _fmt_badges(badges) -> str:
    return "\n".join(f"**{b['name']}** — {b['desc']}" for b in badges)


class Achievements(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="badges",
        description="Lihat badge/achievement yang sudah & belum kamu raih")
    @app_commands.describe(member="(Admin) lihat badge member lain")
    async def badges(self, interaction: discord.Interaction,
                     member: discord.Member = None):
        target = member or interaction.user
        # Hanya admin yang boleh melihat badge member lain.
        if (member is not None and member.id != interaction.user.id
                and not _is_admin(interaction.user)):
            await interaction.response.send_message(
                "❌ Kamu hanya bisa melihat badge-mu sendiri.", ephemeral=True)
            return

        await interaction.response.defer()
        data = profilelib.get_member_profile(target.id)
        result = achlib.compute_achievements(data)
        earned = result["earned"]
        locked = result["locked"][:MAX_LOCKED]

        embed = discord.Embed(
            title=f"🏅 Badge — {target.display_name}",
            color=COLOR_BADGE,
        )
        if earned:
            embed.add_field(
                name=f"✅ Sudah Diraih ({len(earned)})",
                value=_fmt_badges(earned),
                inline=False,
            )
        else:
            embed.add_field(
                name="✅ Sudah Diraih",
                value="_Belum ada badge. Yuk mulai dari transaksi pertamamu!_",
                inline=False,
            )
        if locked:
            embed.add_field(
                name="🔒 Belum Diraih",
                value=_fmt_badges(locked),
                inline=False,
            )
        try:
            embed.set_thumbnail(url=target.display_avatar.url)
        except Exception:
            pass
        embed.set_footer(text=STORE_NAME)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Achievements(bot))
    print("Cog Achievements siap.")
