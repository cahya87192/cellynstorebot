"""Panduan slash command (/help).

Melengkapi `!cmd` (yang khusus prefix command) dengan daftar SLASH command.
Pesan dikirim biasa lalu auto-hilang dalam 60 detik supaya tidak menumpuk di
channel.
"""

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import ADMIN_ROLE_ID, STORE_NAME

AUTO_DELETE_SECONDS = 60
COLOR_HELP = 0x5865F2

# Slash command untuk MEMBER (umum).
MEMBER_COMMANDS = [
    ("/profil", "Lihat kartu profil kamu (level, XP, badge, statistik)"),
    ("/badges", "Lihat badge/achievement yang sudah & belum kamu raih"),
    ("/faq", "Tampilkan FAQ toko (pertanyaan umum)"),
    ("/saran", "Kirim saran / masukan / keluhan ke admin"),
    ("/rating", "Lihat statistik rating & ulasan toko"),
    ("/topreviewer", "Lihat member paling rajin memberi rating"),
    ("/topspender", "Lihat leaderboard top spender bulan ini"),
    ("/riwayat", "Lihat riwayat transaksimu (khusus Royal Customer)"),
    ("/struk", "Lihat ulang struk/invoice transaksi terakhirmu"),
]

# Slash command khusus ADMIN.
ADMIN_COMMANDS = [
    ("/stick_msg", "Pasang sticky message di channel ini (form)"),
    ("/undo_msg", "Hapus sticky message dari channel ini"),
    ("/setprofilbg", "Set background kartu profil per tier"),
    ("/setbadgebg", "Set background kartu badge 'Achievement' per tier"),
    ("/addspending", "Tambah manual spending untuk member"),
    ("/subspend", "Kurangi spending manual member"),
    ("/refreshspender", "Force update leaderboard top spender"),
    ("/settopspenderchannel", "Set channel leaderboard top spender"),
    ("/forcereset", "Force post leaderboard bulan tertentu"),
    ("/setwelcome", "Set channel & gambar welcome/boost"),
    ("/setstatschannel", "Set voice channel statistik member"),
    ("/unsetstatschannel", "Matikan fitur stats channel"),
    ("/setadminstatschannel", "Set channel kartu performa admin"),
    ("/refreshadminstats", "Perbarui kartu performa admin"),
    ("/setreact", "Auto-react di channel ini (pesan admin)"),
    ("/setreactall", "Auto-react untuk SEMUA pesan di channel ini"),
    ("/reactlist", "Lihat daftar channel auto-react"),
    ("/owostok", "Kelola stok OWO Cash"),
    ("/embed_list", "List semua embed dari builder"),
    ("/embed_delete", "Hapus embed yang dikirim bot"),
]


def _is_admin(member) -> bool:
    return any(r.id == ADMIN_ROLE_ID for r in getattr(member, "roles", []))


def _fmt(rows):
    return "\n".join(f"`{name}` — {desc}" for name, desc in rows)


class HelpSlash(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help",
                          description="Daftar slash command yang tersedia")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Panduan Slash Command",
            description="Untuk command prefix (`!...`), admin bisa pakai `!cmd`.",
            color=COLOR_HELP,
        )
        embed.add_field(name="👥 Untuk Member", value=_fmt(MEMBER_COMMANDS), inline=False)
        if _is_admin(interaction.user):
            embed.add_field(name="🛠️ Admin", value=_fmt(ADMIN_COMMANDS), inline=False)
        embed.set_footer(text=f"{STORE_NAME} • pesan ini hilang dalam {AUTO_DELETE_SECONDS} detik")
        await interaction.response.send_message(embed=embed, delete_after=AUTO_DELETE_SECONDS)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpSlash(bot))
    print("Cog HelpSlash siap.")
