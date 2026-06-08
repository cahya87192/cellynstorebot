"""FAQ + Auto Customer Service + Saran/Masukan.

Tiga hal, satu knowledge base (utils.faq, dapat diedit via admin panel):
  1. FAQ embed terpajang di channel FAQ (auto-post + `!faqrefresh`).
  2. Auto-CS: jawab pertanyaan umum member otomatis dari knowledge base
     (berbasis kata kunci — gratis, offline, portabel; bukan LLM berbayar).
  3. `/saran`: member kirim saran/masukan/keluhan ke channel admin.

Semua channel diatur lewat .env (FAQ_CHANNEL_ID, AUTOCS_CHANNEL_ID,
FEEDBACK_CHANNEL_ID). Teks pakai placeholder {store} -> STORE_NAME.
"""

import time

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import (
    GUILD_ID, ADMIN_ROLE_ID, STORE_NAME,
    FAQ_CHANNEL_ID, AUTOCS_CHANNEL_ID, FEEDBACK_CHANNEL_ID, LOG_CHANNEL_ID,
)
from utils.db import get_conn
from utils import faq as faqlib

COLOR_FAQ = 0x5865F2
COLOR_CS = 0x2ECC71
COLOR_SARAN = 0xF0A500

FAQ_MSG_KEY = "faq_message_id"
# Debounce Auto-CS per user supaya tidak spam balasan.
AUTOCS_COOLDOWN = 8


def _get_setting(key):
    conn = get_conn()
    row = conn.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def _set_setting(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
                 (key, "" if value is None else str(value)))
    conn.commit()
    conn.close()


def _is_admin(member) -> bool:
    return any(r.id == ADMIN_ROLE_ID for r in getattr(member, "roles", []))


def build_faq_embeds():
    """Render daftar FAQ jadi 1+ embed (pecah bila kepanjangan)."""
    entries = faqlib.load_faq()
    embeds = []
    embed = discord.Embed(
        title=f"❓ FAQ — {STORE_NAME}",
        description=faqlib.render_text(
            "Pertanyaan umum seputar {store}. Masih bingung? Tanya di channel "
            "bantuan atau kirim **/saran**.", STORE_NAME),
        color=COLOR_FAQ,
    )
    count = 0
    for e in entries:
        if count >= 24:  # batas field per embed
            embeds.append(embed)
            embed = discord.Embed(title=f"❓ FAQ — {STORE_NAME} (lanjutan)", color=COLOR_FAQ)
            count = 0
        q = faqlib.render_text(e["q"], STORE_NAME)
        a = faqlib.render_text(e["a"], STORE_NAME)
        embed.add_field(name=f"▸ {q}"[:256], value=a[:1024], inline=False)
        count += 1
    embed.set_footer(text=f"{STORE_NAME} • diperbarui otomatis")
    embeds.append(embed)
    return embeds


class FAQ(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cs_cooldown = {}  # user_id -> last reply monotonic ts

    # ── FAQ embed terpajang ─────────────────────────────────────────────────
    async def _post_or_update_faq(self):
        if not FAQ_CHANNEL_ID:
            return
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        channel = guild.get_channel(FAQ_CHANNEL_ID)
        if not channel:
            return
        embeds = build_faq_embeds()
        msg_id = _get_setting(FAQ_MSG_KEY)
        # FAQ multi-embed: simpan hanya embed pertama sebagai pesan utama yang
        # di-edit; sisanya dikirim sekali. Untuk simpel & andal, bila >1 embed
        # kita kirim ulang semua (hapus pesan lama).
        if msg_id and str(msg_id).isdigit() and len(embeds) == 1:
            try:
                await channel.get_partial_message(int(msg_id)).edit(embed=embeds[0])
                return
            except discord.NotFound:
                pass
            except discord.HTTPException:
                return
        try:
            first = await channel.send(embed=embeds[0])
            _set_setting(FAQ_MSG_KEY, first.id)
            for extra in embeds[1:]:
                await channel.send(embed=extra)
        except Exception as e:
            print(f"[FAQ] post error: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await self._post_or_update_faq()
        except Exception as e:
            print(f"[FAQ] on_ready error: {e}")

    @commands.command(name="faqrefresh")
    async def faqrefresh(self, ctx):
        """Admin: perbarui/posting ulang embed FAQ di channel FAQ."""
        if not _is_admin(ctx.author):
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        _set_setting(FAQ_MSG_KEY, "")  # paksa kirim baru
        await self._post_or_update_faq()
        await ctx.send("✅ FAQ diperbarui.", delete_after=6)

    @app_commands.command(name="faq", description="Tampilkan FAQ toko")
    async def faq_slash(self, interaction: discord.Interaction):
        embeds = build_faq_embeds()
        await interaction.response.send_message(embeds=embeds[:10], ephemeral=True)

    # ── Auto Customer Service ────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        listen_ch = AUTOCS_CHANNEL_ID or FAQ_CHANNEL_ID
        if not listen_ch or message.channel.id != listen_ch:
            return
        content = (message.content or "").strip()
        if len(content) < 4:
            return
        # debounce per user
        now = time.monotonic()
        if now - self._cs_cooldown.get(message.author.id, 0.0) < AUTOCS_COOLDOWN:
            return

        entry = faqlib.match_question(content, faqlib.load_faq())
        if not entry:
            return
        self._cs_cooldown[message.author.id] = now
        embed = discord.Embed(
            title=f"💬 {faqlib.render_text(entry['q'], STORE_NAME)}",
            description=faqlib.render_text(entry["a"], STORE_NAME),
            color=COLOR_CS,
        )
        embed.set_footer(text=f"{STORE_NAME} • jawaban otomatis • ketik /saran bila perlu bantuan admin")
        try:
            await message.reply(embed=embed, mention_author=False)
        except Exception as e:
            print(f"[FAQ] autocs reply error: {e}")

    # ── Saran / Masukan ──────────────────────────────────────────────────────
    @app_commands.command(name="saran",
                          description="Kirim saran / masukan / keluhan ke admin")
    @app_commands.describe(pesan="Tulis saran, masukan, atau keluhanmu")
    async def saran(self, interaction: discord.Interaction, pesan: str):
        target_id = FEEDBACK_CHANNEL_ID or LOG_CHANNEL_ID
        channel = interaction.guild.get_channel(target_id) if interaction.guild else None
        if channel is None:
            await interaction.response.send_message(
                "⚠️ Channel saran belum dikonfigurasi. Hubungi admin.", ephemeral=True)
            return
        embed = discord.Embed(
            title="📨 Saran / Masukan Baru",
            description=pesan[:4000],
            color=COLOR_SARAN,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Dari", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.set_footer(text=STORE_NAME)
        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"[FAQ] saran send error: {e}")
            await interaction.response.send_message("❌ Gagal mengirim. Coba lagi nanti.", ephemeral=True)
            return
        await interaction.response.send_message(
            "✅ Terima kasih! Saran/masukanmu sudah dikirim ke admin. 🙏", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(FAQ(bot))
    print("Cog FAQ siap.")
