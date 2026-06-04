import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_conn
from utils.config import ADMIN_ROLE_ID, GUILD_ID

# ── CONSTANTS ──────────────────────────────────────────────────────────────────
OWO_STOK_CHANNEL_ID  = 1511134940643983371   # channel embed stok
OWO_NOTIF_ROLE_ID    = 1496781799211270194   # role yang di-ping & bisa di-toggle
THUMBNAIL_URL        = "https://i.imgur.com/rFFnhZW.png"

COLOR_ADA    = 0x39FF14   # hijau neon
COLOR_HABIS  = 0xFF073A   # merah neon

DB_KEY_STATUS  = "owo_stok_status"       # "ada" | "habis"
DB_KEY_MSG_ID      = "owo_stok_message_id"    # message id embed
DB_KEY_PING_MSG_ID = "owo_stok_ping_msg_id"   # message id pesan ping terakhir


# ── DATABASE ───────────────────────────────────────────────────────────────────
def _init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_state (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()


def _get_state(key: str) -> str | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else None


def _set_state(key: str, value: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()


# ── EMBED BUILDER ──────────────────────────────────────────────────────────────
def _build_embed(status: str) -> discord.Embed:
    if status == "ada":
        color       = COLOR_ADA
        status_text = "🟢  TERSEDIA"
        desc        = (
            "Stok sedang **tersedia**!\n"
            "Segera buka tiket **Custom Order** sebelum kehabisan."
        )
    else:
        color       = COLOR_HABIS
        status_text = "🔴  HABIS"
        desc        = (
            "Stok sedang **kosong**.\n"
            "Pantau terus channel ini — kamu akan di-ping saat stok kembali tersedia."
        )

    embed = discord.Embed(
        title="⚠️ Status Stok — Item khusus",
        description=f"## {status_text}\n\n{desc}",
        color=color,
    )
    embed.set_thumbnail(url=THUMBNAIL_URL)
    embed.add_field(
        name="🔔  Notifikasi",
        value=(
            f"Klik tombol di bawah untuk **mengambil atau melepas** <@&{OWO_NOTIF_ROLE_ID}>.\n"
            f"Kamu akan di-ping otomatis saat stok tersedia."
        ),
        inline=False,
    )
    embed.set_footer(text="Cellyn Store  •  Status diperbarui otomatis")

    import datetime
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

    return embed


# ── TOGGLE ROLE VIEW ───────────────────────────────────────────────────────────
class NotifRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔔  Ambil / Lepas Notif",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_stok:toggle_role",
    )
    async def toggle_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(OWO_NOTIF_ROLE_ID)
        if role is None:
            await interaction.response.send_message(
                "❌ Role tidak ditemukan, hubungi admin.", ephemeral=True
            )
            return

        member = interaction.user
        if role in member.roles:
            await member.remove_roles(role, reason="OWO Stok: opt-out via tombol")
            await interaction.response.send_message(
                f"🔕 Role **{role.name}** berhasil **dilepas**.\n"
                "Kamu tidak akan menerima notif stok lagi.",
                ephemeral=True,
            )
        else:
            await member.add_roles(role, reason="OWO Stok: opt-in via tombol")
            await interaction.response.send_message(
                f"🔔 Role **{role.name}** berhasil **didapat**!\n"
                "Kamu akan di-ping saat stok tersedia.",
                ephemeral=True,
            )


# ── COG ────────────────────────────────────────────────────────────────────────
class OwoStok(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _init_db()

    # Persistent view harus didaftarkan ulang setiap bot start
    async def cog_load(self):
        self.bot.add_view(NotifRoleView())

    # ── Helper: ambil pesan embed ──────────────────────────────────────────────
    async def _get_embed_message(self) -> discord.Message | None:
        msg_id = _get_state(DB_KEY_MSG_ID)
        if not msg_id:
            return None
        channel = self.bot.get_channel(OWO_STOK_CHANNEL_ID)
        if channel is None:
            return None
        try:
            return await channel.fetch_message(int(msg_id))
        except (discord.NotFound, discord.HTTPException):
            return None

    # ── Helper: hapus pesan ping terakhir ────────────────────────────────────
    async def _delete_last_ping(self):
        ping_msg_id = _get_state(DB_KEY_PING_MSG_ID)
        if not ping_msg_id:
            return
        channel = self.bot.get_channel(OWO_STOK_CHANNEL_ID)
        if channel is None:
            return
        try:
            old_ping = await channel.fetch_message(int(ping_msg_id))
            await old_ping.delete()
        except (discord.NotFound, discord.HTTPException):
            pass
        finally:
            _set_state(DB_KEY_PING_MSG_ID, "")

    # ── /owostok setup ─────────────────────────────────────────────────────────
    @app_commands.command(name="owostok", description="Kelola stok OWO Cash")
    @app_commands.describe(action="Pilih aksi: setup / ada / habis / status")
    @app_commands.choices(action=[
        app_commands.Choice(name="setup",  value="setup"),
        app_commands.Choice(name="ada",    value="ada"),
        app_commands.Choice(name="habis",  value="habis"),
        app_commands.Choice(name="status", value="status"),
    ])
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def owostok(self, interaction: discord.Interaction, action: str):
        # Cek permission admin
        admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
        if admin_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Kamu tidak punya izin untuk command ini.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        # ── SETUP ──────────────────────────────────────────────────────────────
        if action == "setup":
            existing = await self._get_embed_message()
            if existing:
                await interaction.followup.send(
                    "⚠️ Embed stok sudah ada. Hapus manual dulu kalau mau reset.",
                    ephemeral=True,
                )
                return

            channel = self.bot.get_channel(OWO_STOK_CHANNEL_ID)
            if channel is None:
                await interaction.followup.send("❌ Channel tidak ditemukan.", ephemeral=True)
                return

            status = _get_state(DB_KEY_STATUS) or "habis"
            embed  = _build_embed(status)
            msg    = await channel.send(embed=embed, view=NotifRoleView())
            _set_state(DB_KEY_MSG_ID, str(msg.id))
            _set_state(DB_KEY_STATUS, status)

            await interaction.followup.send("✅ Embed stok berhasil dibuat!", ephemeral=True)

        # ── ADA ────────────────────────────────────────────────────────────────
        elif action == "ada":
            msg = await self._get_embed_message()
            if msg is None:
                await interaction.followup.send(
                    "❌ Embed belum dibuat. Jalankan `/owostok setup` dulu.", ephemeral=True
                )
                return

            _set_state(DB_KEY_STATUS, "ada")
            await msg.edit(embed=_build_embed("ada"), view=NotifRoleView())

            # Hapus pesan ping sebelumnya, lalu kirim ping baru
            await self._delete_last_ping()
            channel = self.bot.get_channel(OWO_STOK_CHANNEL_ID)
            if channel:
                ping_msg = await channel.send(
                    f"<@&{OWO_NOTIF_ROLE_ID}> 📦 Stok **Item Spesial** tersedia sekarang! "
                    f"Segera buka tiket Custom Order sebelum kehabisan."
                )
                _set_state(DB_KEY_PING_MSG_ID, str(ping_msg.id))

            await interaction.followup.send("✅ Stok diset **ADA** & role sudah di-ping.", ephemeral=True)

        # ── HABIS ──────────────────────────────────────────────────────────────
        elif action == "habis":
            msg = await self._get_embed_message()
            if msg is None:
                await interaction.followup.send(
                    "❌ Embed belum dibuat. Jalankan `/owostok setup` dulu.", ephemeral=True
                )
                return

            _set_state(DB_KEY_STATUS, "habis")
            await msg.edit(embed=_build_embed("habis"), view=NotifRoleView())

            # Hapus pesan ping sebelumnya, lalu kirim ping habis
            await self._delete_last_ping()
            channel = self.bot.get_channel(OWO_STOK_CHANNEL_ID)
            if channel:
                ping_msg = await channel.send(
                    f"<@&{OWO_NOTIF_ROLE_ID}> ⚠️ Stok **Item Spesial** telah **habis**."
                )
                _set_state(DB_KEY_PING_MSG_ID, str(ping_msg.id))

            await interaction.followup.send("✅ Stok diset **HABIS** & role sudah di-ping.", ephemeral=True)

        # ── STATUS ─────────────────────────────────────────────────────────────
        elif action == "status":
            status = _get_state(DB_KEY_STATUS) or "habis"
            msg_id = _get_state(DB_KEY_MSG_ID) or "Belum di-setup"
            await interaction.followup.send(
                f"📊 **Status stok saat ini:** `{status.upper()}`\n"
                f"📌 **Message ID embed:** `{msg_id}`",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(OwoStok(bot))
