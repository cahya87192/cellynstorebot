import os
import datetime
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from utils.config import (
    ADMIN_ROLE_ID, STORE_NAME,
    BOOST_ROLE_ID, CUSTOMER_ROLE_ID, GENERAL_CHANNEL_ID,
)
from utils.db import get_conn
from utils import welcome as welcomelib

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"
# Gambar khusus untuk DM sambutan member baru.
WELCOME_DM_THUMBNAIL = "https://i.imgur.com/4lpmtpL.png"
DATA_DIR = "data"
WELCOME_IMAGE_BASE = "welcome"
BOOST_IMAGE_BASE = "boost"
ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def _find_image(base: str):
    """Cari file gambar (welcome/boost) berdasarkan ekstensi yang didukung."""
    for ext in ALLOWED_IMAGE_EXTS:
        path = os.path.join(DATA_DIR, base + ext)
        if os.path.exists(path):
            return path
    return None


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


class WelcomeCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._welcome_channel_id = None
        self._welcome_image = _find_image(WELCOME_IMAGE_BASE)
        self._boost_image = _find_image(BOOST_IMAGE_BASE)

    async def cog_load(self):
        self.bot.loop.create_task(self._load_settings())

    async def _load_settings(self):
        await self.bot.wait_until_ready()
        try:
            ch_id = _get_setting("welcome_channel_id")
            if ch_id:
                self._welcome_channel_id = int(ch_id)
            self._welcome_image = _find_image(WELCOME_IMAGE_BASE)
            self._boost_image = _find_image(BOOST_IMAGE_BASE)
            print(f"[Welcome] Channel: {self._welcome_channel_id}, Image: {self._welcome_image}, BoostImage: {self._boost_image}")
        except Exception as e:
            print(f"[Welcome] Load settings error: {e}")

    async def _save_image(self, attachment: discord.Attachment, base: str):
        """Download & simpan gambar (PNG/JPG/dll) dengan ekstensi sesuai file upload.

        Mengembalikan path file yang tersimpan, atau None jika gagal / format tidak didukung.
        """
        ext = os.path.splitext(attachment.filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            return None
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            # Hapus gambar lama dengan base yang sama supaya tidak ada dobel format
            for old_ext in ALLOWED_IMAGE_EXTS:
                old_path = os.path.join(DATA_DIR, base + old_ext)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
            path = os.path.join(DATA_DIR, base + ext)
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status == 200:
                        with open(path, "wb") as f:
                            f.write(await resp.read())
                        return path
            return None
        except Exception as e:
            print(f"[Welcome] Download error: {e}")
            return None

    @app_commands.command(name="setwelcome", description="[ADMIN] Set channel & gambar welcome/boost (PNG/JPG)")
    @app_commands.describe(
        action="channel / image / boostimage / test / testboost / testdm / off",
        channel="Channel untuk pesan welcome",
        image="File gambar PNG/JPG (upload langsung)"
    )
    async def set_welcome(self, interaction: discord.Interaction, action: str,
                          channel: discord.TextChannel = None, image: discord.Attachment = None):
        await interaction.response.defer(ephemeral=True)
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.followup.send("❌ Admin only!", ephemeral=True)
            return
        action = action.lower().strip()
        if action == "channel":
            if not channel:
                await interaction.followup.send("Sertakan channel. Contoh: `/setwelcome action:channel channel:#welcome`", ephemeral=True)
                return
            self._welcome_channel_id = channel.id
            _set_setting("welcome_channel_id", str(channel.id))
            await interaction.followup.send(f"✅ Welcome channel diset ke {channel.mention}", ephemeral=True)
        elif action in ("image", "gif"):
            if not image:
                await interaction.followup.send("Sertakan file gambar (PNG/JPG) untuk welcome.", ephemeral=True)
                return
            path = await self._save_image(image, WELCOME_IMAGE_BASE)
            if path:
                self._welcome_image = path
                await interaction.followup.send("✅ Gambar welcome berhasil diupload!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Format tidak didukung. Gunakan PNG/JPG.", ephemeral=True)
        elif action in ("boostimage", "boostgif"):
            if not image:
                await interaction.followup.send("Sertakan file gambar (PNG/JPG) untuk boost.", ephemeral=True)
                return
            path = await self._save_image(image, BOOST_IMAGE_BASE)
            if path:
                self._boost_image = path
                await interaction.followup.send("✅ Gambar boost berhasil diupload!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Format tidak didukung. Gunakan PNG/JPG.", ephemeral=True)
        elif action == "test":
            await self._send_welcome(interaction.user, test=True, interaction=interaction)
        elif action == "testboost":
            await self._send_boost(interaction.user, test=True, interaction=interaction)
        elif action == "testdm":
            await self._send_welcome_dm(interaction.user, interaction=interaction)
        elif action == "off":
            self._welcome_channel_id = None
            _set_setting("welcome_channel_id", "")
            await interaction.followup.send("✅ Welcome message dinonaktifkan.", ephemeral=True)
        else:
            await interaction.followup.send(
                "Action tidak dikenal. Gunakan: `channel`, `image`, `boostimage`, `test`, `testboost`, `testdm`, `off`",
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Assign role Customer (human only)
        if not member.bot:
            try:
                role = member.guild.get_role(CUSTOMER_ROLE_ID)
                if role and role not in member.roles:
                    await member.add_roles(role, reason="Auto role: Customer")
            except Exception as e:
                print(f"[Welcome] Auto role error: {e}")
        await self._send_welcome(member)
        await self._send_general_greeting(member)
        if not member.bot:
            await self._send_welcome_dm(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not self._welcome_channel_id:
            return
        channel = self.bot.get_channel(self._welcome_channel_id)
        if not channel:
            return
        now = datetime.datetime.now(datetime.timezone.utc)
        joined = member.joined_at
        if joined:
            delta = now - joined
            days = delta.days
            if days < 1:
                hours = delta.seconds // 3600
                durasi_str = f"{hours} jam"
            elif days < 30:
                durasi_str = f"{days} hari"
            elif days < 365:
                months = days // 30
                durasi_str = f"{months} bulan"
            else:
                years = days // 365
                sisa = (days % 365) // 30
                durasi_str = f"{years} tahun {sisa} bulan" if sisa else f"{years} tahun"
        else:
            durasi_str = "tidak diketahui"
        leave_title, leave_desc = welcomelib.render_leave(
            member.display_name, STORE_NAME, durasi_str)
        embed = discord.Embed(title=leave_title, description=leave_desc, color=0x808080)
        try:
            embed.set_thumbnail(url=member.display_avatar.replace(size=256).url)
        except Exception:
            pass
        embed.set_footer(text=STORE_NAME)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not self._welcome_channel_id:
            return
        # Boost added
        if before.premium_since is None and after.premium_since is not None:
            try:
                role = after.guild.get_role(BOOST_ROLE_ID)
                if role and role not in after.roles:
                    await after.add_roles(role, reason="Auto role: server boost")
            except Exception as e:
                print(f"[Welcome] Boost role add error: {e}")
            await self._send_boost(after)
        # Boost removed
        elif before.premium_since is not None and after.premium_since is None:
            try:
                role = after.guild.get_role(BOOST_ROLE_ID)
                if role and role in after.roles:
                    await after.remove_roles(role, reason="Auto role removed: boost ended")
            except Exception as e:
                print(f"[Welcome] Boost role remove error: {e}")

    async def _send_welcome(self, member: discord.Member, test=False, interaction=None):
        if not self._welcome_channel_id:
            if interaction:
                await interaction.followup.send("Welcome channel belum diset. Gunakan `/setwelcome action:channel`.", ephemeral=True)
            return
        channel = self.bot.get_channel(self._welcome_channel_id)
        if not channel:
            return
        guild = member.guild
        member_count = sum(1 for m in guild.members if not m.bot)
        title, desc = welcomelib.render_welcome(member.display_name, STORE_NAME, member_count)
        embed = discord.Embed(title=title, description=desc, color=0x00BFFF)
        try:
            embed.set_thumbnail(url=member.display_avatar.replace(size=256).url)
        except Exception:
            pass
        embed.set_footer(text=STORE_NAME)
        if self._welcome_image and os.path.exists(self._welcome_image):
            fname = os.path.basename(self._welcome_image)
            file = discord.File(self._welcome_image, filename=fname)
            embed.set_image(url=f"attachment://{fname}")
            if test and interaction:
                await interaction.followup.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed, file=file)
        else:
            if test and interaction:
                await interaction.followup.send("Gambar belum diupload. Preview embed:", embed=embed)
            else:
                await channel.send(embed=embed)

    async def _send_boost(self, member: discord.Member, test=False, interaction=None):
        if not self._welcome_channel_id:
            if interaction:
                await interaction.followup.send("Welcome channel belum diset.", ephemeral=True)
            return
        channel = self.bot.get_channel(self._welcome_channel_id)
        if not channel:
            return
        boost_title, boost_desc = welcomelib.render_boost(member.mention, STORE_NAME)
        embed = discord.Embed(title=boost_title, description=boost_desc, color=0xFF73FA)
        try:
            embed.set_thumbnail(url=member.display_avatar.replace(size=256).url)
        except Exception:
            pass
        embed.set_footer(text=STORE_NAME)
        if self._boost_image and os.path.exists(self._boost_image):
            fname = os.path.basename(self._boost_image)
            file = discord.File(self._boost_image, filename=fname)
            embed.set_image(url=f"attachment://{fname}")
            if test and interaction:
                await interaction.followup.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed, file=file)
        else:
            if test and interaction:
                await interaction.followup.send("Gambar boost belum diupload. Preview embed:", embed=embed)
            else:
                await channel.send(embed=embed)


    async def _send_general_greeting(self, member: discord.Member):
        if member.bot:
            return
        channel = self.bot.get_channel(GENERAL_CHANNEL_ID)
        if not channel:
            return
        try:
            await channel.send(
                f"👋 𝗛𝗔𝗟𝗢, 𝗦𝗔𝗬𝗔 {member.mention} 𝗠𝗘𝗠𝗕𝗘𝗥 𝗕𝗔𝗥𝗨 𝗗𝗜 {STORE_NAME}!"
            )
        except Exception as e:
            print(f"[Welcome] General greeting error: {e}")

    async def _send_welcome_dm(self, member: discord.Member, interaction=None):
        """Kirim DM sambutan ke member baru: salam, penjelasan store, peraturan,
        dan penutup. Best-effort — kalau DM member tertutup, dilewati diam-diam.

        Bila dipanggil lewat `/setwelcome action:testdm`, preview dikirim ephemeral
        ke admin (lewat `interaction`) alih-alih ke DM member.
        """
        embed = discord.Embed(
            title=f"🤍 Selamat Datang di {STORE_NAME}!",
            description=(
                f"Hai **{member.display_name}**! 👋\n"
                f"Makasih banyak udah gabung ke **{STORE_NAME}** — tempat jual-beli "
                f"& top-up digital yang aman dan terpercaya. Biar kamu makin nyaman "
                f"belanja, baca info singkat di bawah ini ya 🙏"
            ),
            color=0x00BFFF,
        )
        embed.add_field(
            name="🏪 Tentang Kami",
            value=(
                f"{STORE_NAME} melayani kebutuhan game & akunmu dengan proses "
                f"**cepat**, harga **bersahabat**, dan admin yang **ramah**. "
                f"Setiap transaksi memakai sistem **tiket** + **garansi** supaya aman."
            ),
            inline=False,
        )
        embed.add_field(
            name="🛍️ Layanan Kami",
            value=(
                "• Top-up Mobile Legends & Free Fire\n"
                "• Robux (Store, Via Login, Gamepass)\n"
                "• Middleman Trade & Jual Beli\n"
                "• Cloud Phone & Discord Nitro\n"
                "• dan layanan lainnya!"
            ),
            inline=False,
        )
        embed.add_field(
            name="📜 Peraturan Singkat",
            value=(
                "**1.** Hormati semua member & admin — no toxic/SARA.\n"
                "**2.** Dilarang spam & promosi toko lain tanpa izin.\n"
                "**3.** Transaksi **WAJIB** lewat tiket & admin resmi — "
                "waspada admin palsu/penipu!\n"
                "**4.** Selalu simpan bukti pembayaranmu.\n"
                "**5.** Jangan lupa beri **rating** tiap selesai order — "
                "rating = garansimu aktif."
            ),
            inline=False,
        )
        embed.add_field(
            name="💬 Siap Order?",
            value=(
                "Buka tiket di channel layanan yang sesuai, admin kami siap bantu. "
                "Kalau ada pertanyaan, tanya aja langsung di server ya!"
            ),
            inline=False,
        )
        embed.set_thumbnail(url=WELCOME_DM_THUMBNAIL)
        embed.set_footer(text=f"{STORE_NAME} • Selamat berbelanja & semoga betah! 🤍")

        # Mode test: kirim preview ephemeral ke admin, jangan ke DM member.
        if interaction is not None:
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            print(f"[Welcome] DM sambutan ke {member.id} ditolak (DM tertutup).")
        except Exception as e:
            print(f"[Welcome] DM sambutan error {member.id}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
