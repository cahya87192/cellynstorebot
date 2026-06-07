"""Sticky message umum: jaga sebuah pesan tetap di paling bawah channel.

Mirip bot sticky-message pada umumnya: admin set sticky di sebuah channel, lalu
tiap kali ada pesan baru menumpuk, bot menghapus sticky lama dan mengirim ulang
di paling bawah (dengan debounce ketat supaya tidak spam / rate-limit).

Desain sengaja DISJOINT dari kartu sticky tiket (cogs/queue.py):
  - state sendiri di bot_state key `sticky_messages` (tidak menyentuh queue_*),
  - listener sendiri yang MENGABAIKAN pesan bot (jadi tidak ping-pong dengan
    kartu tiket), dan
  - GUARD: channel yang sedang punya kartu antrean tiket (queue_card_messages)
    tidak boleh dipasang sticky umum, supaya keduanya tidak rebutan posisi
    "paling bawah".

Satu sticky per channel. Mendukung teks dan/atau embed.
"""

import asyncio
import json
import time

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import ADMIN_ROLE_ID, STORE_NAME
from utils.db import get_conn
from utils import sticky as stickylib

STICKY_KEY = "sticky_messages"          # JSON {channel_id: {message_id, content, embed}}
QUEUE_CARDS_KEY = "queue_card_messages"  # dikelola cogs/queue.py (read-only di sini)

COLOR_DEFAULT = 0x5865F2


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


def _is_admin(member) -> bool:
    return any(r.id == ADMIN_ROLE_ID for r in getattr(member, "roles", []))


def _parse_color(text):
    """'#5865F2' / '5865F2' -> int. None/invalid -> COLOR_DEFAULT."""
    if not text:
        return COLOR_DEFAULT
    try:
        return int(str(text).lstrip("#"), 16)
    except (ValueError, TypeError):
        return COLOR_DEFAULT


class Sticky(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._msgcount = {}   # channel_id -> jumlah pesan sejak sticky terakhir
        self._last = {}       # channel_id -> monotonic ts re-stick terakhir
        self._lock = asyncio.Lock()

    # ── State helpers ───────────────────────────────────────────────────────────
    def _load_map(self):
        raw = _get_setting(STICKY_KEY)
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return {}
        if not isinstance(data, dict):
            return {}
        out = {}
        for k, v in data.items():
            try:
                out[int(k)] = v
            except (ValueError, TypeError):
                continue
        return out

    def _save_map(self, m):
        _set_setting(STICKY_KEY, json.dumps({str(k): v for k, v in m.items()}))

    def _channel_has_ticket_card(self, channel_id) -> bool:
        """True bila channel sedang punya kartu antrean tiket (anti-bentrok)."""
        raw = _get_setting(QUEUE_CARDS_KEY)
        if not raw:
            return False
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return False
        return isinstance(data, dict) and str(channel_id) in data

    def _build_embed(self, embed_dict):
        try:
            return discord.Embed.from_dict(embed_dict) if embed_dict else None
        except Exception:
            return None

    async def _send_sticky(self, channel, entry):
        """Kirim sticky di paling bawah; kembalikan message id baru (atau None)."""
        content, embed_dict = entry.get("content"), entry.get("embed")
        embed = self._build_embed(embed_dict)
        try:
            msg = await channel.send(content=content or None, embed=embed)
            return msg.id
        except Exception as e:
            print(f"[Sticky] send error ({channel.id}): {e}")
            return None

    # ── Listener: jaga sticky di bawah (debounce) ────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return
        ch_id = message.channel.id
        sticky_map = self._load_map()
        if ch_id not in sticky_map:
            return

        self._msgcount[ch_id] = self._msgcount.get(ch_id, 0) + 1
        if not stickylib.should_restick(
            self._msgcount[ch_id], self._last.get(ch_id), time.monotonic()
        ):
            return

        async with self._lock:
            if not stickylib.should_restick(
                self._msgcount.get(ch_id, 0), self._last.get(ch_id), time.monotonic()
            ):
                return
            self._last[ch_id] = time.monotonic()
            self._msgcount[ch_id] = 0
            try:
                await self._restick(message.channel)
            except Exception as e:
                print(f"[Sticky] restick error ({ch_id}): {e}")

    async def _restick(self, channel):
        sticky_map = self._load_map()
        entry = sticky_map.get(channel.id)
        if not entry:
            return
        old_id = entry.get("message_id")
        new_id = await self._send_sticky(channel, entry)
        if new_id is None:
            return
        entry["message_id"] = new_id
        sticky_map[channel.id] = entry
        self._save_map(sticky_map)
        if old_id and int(old_id) != new_id:
            try:
                await channel.get_partial_message(int(old_id)).delete()
            except Exception:
                pass

    # ── Slash commands ───────────────────────────────────────────────────────────
    @app_commands.command(name="stick_msg",
                          description="[ADMIN] Pasang sticky message di channel ini (teks dan/atau embed)")
    @app_commands.describe(
        message="Teks sticky (biarkan kosong bila hanya pakai embed)",
        embed_title="Judul embed (opsional)",
        embed_description="Isi embed (opsional)",
        embed_color="Warna embed hex, mis. #5865F2 (opsional)",
    )
    async def stick_msg(self, interaction: discord.Interaction,
                        message: str = None,
                        embed_title: str = None,
                        embed_description: str = None,
                        embed_color: str = None):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return

        # Anti-bentrok dengan kartu antrean tiket.
        if self._channel_has_ticket_card(interaction.channel_id):
            await interaction.response.send_message(
                "❌ Channel ini adalah channel tiket (punya kartu antrean). "
                "Sticky umum tidak dipasang di sini agar tidak bentrok dengan kartu antrean.",
                ephemeral=True,
            )
            return

        embed_dict = None
        if embed_title or embed_description:
            e = discord.Embed(
                title=embed_title or None,
                description=embed_description or None,
                color=_parse_color(embed_color),
            )
            e.set_footer(text=STORE_NAME)
            embed_dict = e.to_dict()

        if not stickylib.has_payload(message, embed_dict):
            await interaction.response.send_message(
                "❌ Isi minimal salah satu: `message` atau `embed_title`/`embed_description`.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        sticky_map = self._load_map()
        ch_id = interaction.channel_id
        # Hapus sticky lama bila ada (ganti dengan yang baru).
        old = sticky_map.get(ch_id)
        if old and old.get("message_id"):
            try:
                await interaction.channel.get_partial_message(int(old["message_id"])).delete()
            except Exception:
                pass

        entry = {"message_id": None, "content": message, "embed": embed_dict}
        new_id = await self._send_sticky(interaction.channel, entry)
        if new_id is None:
            await interaction.followup.send("❌ Gagal mengirim sticky (cek izin bot di channel ini).", ephemeral=True)
            return
        entry["message_id"] = new_id
        sticky_map[ch_id] = entry
        self._save_map(sticky_map)
        self._msgcount[ch_id] = 0
        self._last[ch_id] = time.monotonic()
        await interaction.followup.send("✅ Sticky message dipasang di channel ini.", ephemeral=True)

    @app_commands.command(name="undo_msg",
                          description="[ADMIN] Hapus sticky message dari channel ini")
    async def undo_msg(self, interaction: discord.Interaction):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        sticky_map = self._load_map()
        ch_id = interaction.channel_id
        entry = sticky_map.pop(ch_id, None)
        if not entry:
            await interaction.response.send_message(
                "ℹ️ Tidak ada sticky message di channel ini.", ephemeral=True)
            return
        self._save_map(sticky_map)
        self._msgcount.pop(ch_id, None)
        self._last.pop(ch_id, None)
        if entry.get("message_id"):
            try:
                await interaction.channel.get_partial_message(int(entry["message_id"])).delete()
            except Exception:
                pass
        await interaction.response.send_message("🗑️ Sticky message dihapus dari channel ini.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Sticky(bot))
    print("Cog Sticky siap.")
