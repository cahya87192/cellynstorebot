"""cogs/member_sync.py - Sinkronisasi nama member Discord ke cache DB.

Mengisi tabel `member_names` (utils.member_names) supaya admin panel bisa
menampilkan NAMA member/admin, bukan ID mentah. Panel tidak punya akses gateway
Discord, jadi bot yang meng-update cache:
  - sinkron penuh saat online & periodik tiap 6 jam,
  - update saat member join / ganti nama tampilan.

Semua best-effort (dibungkus try/except) — tidak boleh mengganggu bot.
"""
import discord
from discord.ext import commands, tasks

from utils import member_names


class MemberSync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._sync_loop.start()

    def cog_unload(self):
        self._sync_loop.cancel()

    async def _sync_all(self):
        mapping = {}
        try:
            for guild in self.bot.guilds:
                for m in guild.members:
                    if m.display_name:
                        mapping[m.id] = m.display_name
        except Exception as e:
            print(f"[MemberSync] kumpul member error: {e}")
        if mapping:
            member_names.bulk_set(mapping)

    @tasks.loop(hours=6)
    async def _sync_loop(self):
        await self._sync_all()

    @_sync_loop.before_loop
    async def _before_sync(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        member_names.set_name(member.id, member.display_name)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.display_name != after.display_name:
            member_names.set_name(after.id, after.display_name)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        # Nama global / username berubah.
        if getattr(before, "name", None) != getattr(after, "name", None):
            name = getattr(after, "display_name", None) or getattr(after, "name", None)
            if name:
                member_names.set_name(after.id, name)


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberSync(bot))
