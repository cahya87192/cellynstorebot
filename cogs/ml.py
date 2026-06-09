import discord
import datetime
import asyncio
from discord.ext import commands
from utils.config import ADMIN_ROLE_ID, LOG_CHANNEL_ID, STORE_NAME, TICKET_CATEGORY_ID, TRANSCRIPT_CHANNEL_ID, GUILD_ID, DIAMOND_EMOJI, USE_CUSTOM_EMOJI
from utils.counter import next_ticket_number
from utils.transcript import generate as generate_transcript
from utils.db import get_conn
from utils.store_hours import is_store_open
from utils.paginator import PaginatedSelectView, with_price
from utils import ticket_ui
from utils import catalog_emoji
from utils import ml_text as mltext

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"

# ─── DB helpers ──────────────────────────────────────────────────────────────

def _migrate_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        color INTEGER DEFAULT 3407872,
        needs_server INTEGER DEFAULT 0,
        id_label TEXT DEFAULT 'Player ID',
        active INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS game_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_code TEXT NOT NULL,
        label TEXT NOT NULL,
        dm INTEGER NOT NULL DEFAULT 0,
        harga INTEGER NOT NULL,
        active INTEGER DEFAULT 1
    )""")
    conn.commit()
    if c.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 0:
        c.executemany(
            "INSERT OR IGNORE INTO games (code, name, color, needs_server, id_label) VALUES (?,?,?,?,?)",
            [
                ("ML",  "Mobile Legends",       0x3498DB, 1, "ID Mobile Legends"),
                ("WDP", "WDP (Mobile Legends)", 0x3498DB, 1, "ID Mobile Legends"),
                ("FF",  "Free Fire",            0xFF6B35, 0, "Player ID Free Fire"),
            ]
        )
        conn.commit()
    if c.execute("SELECT COUNT(*) FROM game_products WHERE game_code='ML'").fetchone()[0] == 0:
        try:
            rows = c.execute("SELECT dm, harga FROM ml_products ORDER BY dm").fetchall()
            for r in rows:
                c.execute("INSERT INTO game_products (game_code, label, dm, harga) VALUES (?,?,?,?)",
                          ("ML", f"{r['dm']} Diamond", r["dm"], r["harga"]))
            conn.commit()
        except Exception as e:
            print(f"[ML] Migrasi ml_products: {e}")
    if c.execute("SELECT COUNT(*) FROM game_products WHERE game_code='FF'").fetchone()[0] == 0:
        try:
            rows = c.execute("SELECT dm, harga FROM ff_products ORDER BY dm").fetchall()
            for r in rows:
                c.execute("INSERT INTO game_products (game_code, label, dm, harga) VALUES (?,?,?,?)",
                          ("FF", f"{r['dm']} Diamond", r["dm"], r["harga"]))
            conn.commit()
        except Exception as e:
            print(f"[ML] Migrasi ff_products: {e}")
    if c.execute("SELECT COUNT(*) FROM game_products WHERE game_code='WDP'").fetchone()[0] == 0:
        try:
            rows = c.execute("SELECT qty, label, harga FROM wdp_products ORDER BY qty").fetchall()
            for r in rows:
                c.execute("INSERT INTO game_products (game_code, label, dm, harga) VALUES (?,?,?,?)",
                          ("WDP", r["label"], r["qty"], r["harga"]))
            conn.commit()
        except Exception as e:
            print(f"[ML] Migrasi wdp_products: {e}")
    conn.close()


def _load_games():
    conn = get_conn()
    rows = conn.execute(
        "SELECT code, name, color, needs_server, id_label FROM games WHERE active=1 ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _load_products(game_code):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, label, dm, harga FROM game_products WHERE game_code=? AND active=1 ORDER BY dm, id",
        (game_code,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _get_game(code):
    conn = get_conn()
    row = conn.execute(
        "SELECT code, name, color, needs_server, id_label FROM games WHERE code=?", (code,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── ML Ticket DB ─────────────────────────────────────────────────────────────

def load_ml_tickets():
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE ml_tickets ADD COLUMN item_label TEXT")
        conn.commit()
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE ml_tickets ADD COLUMN ticket_number INTEGER")
        conn.commit()
    except Exception:
        pass
    c.execute("SELECT * FROM ml_tickets")
    rows = c.fetchall()
    conn.close()
    tickets = {}
    for row in rows:
        tickets[row["channel_id"]] = {
            "channel_id": row["channel_id"],
            "user_id": row["user_id"],
            "id_ml": row["id_ml"],
            "server_id": row["server_id"],
            "dm": row["dm"],
            "harga": row["harga"],
            "opened_at": row["opened_at"],
            "last_activity": row["opened_at"],
            "game": row["game"] if row["game"] else "ML",
            "warned": bool(row["warned"]) if row["warned"] is not None else False,
            "item_label": (row["item_label"] if "item_label" in row.keys() and row["item_label"] else f"{row['dm']} Diamond"),
            "ticket_number": (row["ticket_number"] if "ticket_number" in row.keys() and row["ticket_number"] is not None else 0),
        }
    return tickets


def save_ml_ticket(ticket):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE ml_tickets ADD COLUMN item_label TEXT")
        conn.commit()
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE ml_tickets ADD COLUMN ticket_number INTEGER")
        conn.commit()
    except Exception:
        pass
    c.execute("""
        INSERT OR REPLACE INTO ml_tickets
        (channel_id, user_id, id_ml, server_id, dm, harga, opened_at, game, warned, item_label, ticket_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket["channel_id"], ticket["user_id"], ticket["id_ml"], ticket["server_id"],
        ticket["dm"], ticket["harga"], ticket["opened_at"], ticket.get("game", "ML"),
        1 if ticket.get("warned") else 0,
        ticket.get("item_label", f"{ticket['dm']} Diamond"),
        ticket.get("ticket_number") or 0,
    ))
    conn.commit()
    conn.close()


def delete_ml_ticket(channel_id):
    conn = get_conn()
    conn.execute("DELETE FROM ml_tickets WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()


# ─── Views & Modals ───────────────────────────────────────────────────────────

class GameFormModal(discord.ui.Modal):
    player_id = discord.ui.TextInput(
        label="Player ID", placeholder="Masukkan ID kamu", required=True, max_length=30
    )
    server_id_input = discord.ui.TextInput(
        label="Server ID", placeholder="Contoh: 1234", required=False, max_length=10
    )

    def __init__(self, game: dict, product: dict):
        super().__init__(title=f"Topup {game['name']}")
        self.game = game
        self.product = product
        self.player_id.label = game.get("id_label", "Player ID")
        self.player_id.placeholder = f"Masukkan {game.get('id_label', 'Player ID')}"
        if not game.get("needs_server"):
            self.remove_item(self.server_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        game = self.game
        product = self.product
        cog = interaction.client.cogs.get("MLStore")
        from utils.config import MAX_TICKETS_PER_SERVICE
        _user_active = sum(
            1 for _cid, _t in cog.active_tickets.items()
            if _t.get("user_id") == user.id and guild.get_channel(_cid)
        )
        if _user_active >= MAX_TICKETS_PER_SERVICE:
            await interaction.response.send_message(
                f"Kamu sudah punya {_user_active} tiket aktif di layanan ini (maks {MAX_TICKETS_PER_SERVICE}). Selesaikan salah satunya dulu.",
                ephemeral=True
            )
            return
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        category = guild.get_channel(TICKET_CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        game_slug = game["code"].lower().replace(" ", "")
        ticket_number = next_ticket_number()
        channel = await guild.create_text_channel(
            name=ticket_ui.channel_name(game_slug, ticket_number, user.name), category=category, overwrites=overwrites
        )
        server_val = self.server_id_input.value.strip() if game.get("needs_server") else "-"
        ticket = {
            "channel_id": channel.id, "user_id": user.id,
            "id_ml": self.player_id.value.strip(), "server_id": server_val,
            "dm": product["dm"], "item_label": product["label"], "harga": product["harga"],
            "ticket_number": ticket_number,
            "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "last_activity": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "game": game["code"],
        }
        cog.active_tickets[channel.id] = ticket
        save_ml_ticket(ticket)
        id_label = game.get("id_label", "Player ID")
        _extra = [(id_label, f"`{self.player_id.value.strip()}`", True)]
        if game.get("needs_server") and server_val != "-":
            _extra.append(("Server ID", f"`{server_val}`", True))
        _extra.append(("Status", "Menunggu proses", False))
        _extra.append(("Perintah Admin", "**!mlselesai** — konfirmasi topup selesai\n**!mlbatal [alasan]** — batalkan tiket", False))
        from cogs.top_spender import is_top_spender
        embed = ticket_ui.open_ticket_embed(
            game_slug, ticket_number, user,
            item=product["label"],
            total=f"Rp {product['harga']:,}",
            payment="QRIS",
            is_priority=is_top_spender(user.id),
            extra_fields=_extra,
        )
        if admin_role:
            await channel.send(content=admin_role.mention, embed=embed)
        else:
            await channel.send(embed=embed)
        from utils.customer_insight import send_insight
        await send_insight(interaction.client, channel, user)
        await interaction.response.send_message(
            f"Tiket berhasil dibuat di {channel.mention}!", ephemeral=True
        )


class MLConfirmView(discord.ui.View):
    """Ditampilkan setelah member pilih produk — berisi info layanan + tombol Lanjutkan/Batal."""
    def __init__(self, game: dict, product: dict):
        super().__init__(timeout=120)
        self.game = game
        self.product = product

    @discord.ui.button(label="✅ Lanjutkan", style=discord.ButtonStyle.success, custom_id="ml_confirm_lanjut")
    async def lanjutkan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GameFormModal(game=self.game, product=self.product))

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.danger, custom_id="ml_confirm_batal")
    async def batal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Order dibatalkan.", embed=None, view=None)


# Emoji custom per game (berdasarkan kode) untuk dropdown katalog ML.
GAME_EMOJI = {
    "ML": "<:mole:1497007406415220857>",
    "WDP": "<:mole:1497007406415220857>",
    "FF": "<:Garena:1496829013967241388>",
}
# DIAMOND_EMOJI diimpor dari utils.config (bisa diatur via .env).

# Fallback unicode saat custom emoji server tidak tersedia (USE_CUSTOM_EMOJI=false),
# agar opsi dropdown tidak ditolak Discord di server self-host lain.
DIAMOND_EMOJI_FALLBACK = "\U0001F48E"  # 💎
GAME_EMOJI_FALLBACK = {
    "ML": "\U0001F3AE",   # 🎮
    "WDP": "\U0001F3AE",  # 🎮
    "FF": "\U0001F525",   # 🔥
}


def _diamond_emoji():
    """Emoji diamond yang aman lintas-server untuk komponen UI."""
    return catalog_emoji.safe_emoji(DIAMOND_EMOJI, DIAMOND_EMOJI_FALLBACK, USE_CUSTOM_EMOJI)


def _game_emoji(code):
    """Emoji game (ML/WDP/FF) yang aman lintas-server untuk dropdown."""
    return catalog_emoji.safe_emoji(
        GAME_EMOJI.get(code),
        GAME_EMOJI_FALLBACK.get(code, DIAMOND_EMOJI_FALLBACK),
        USE_CUSTOM_EMOJI,
    )


def _build_product_options(game: dict) -> list:
    """Bangun daftar lengkap SelectOption produk untuk sebuah game (tanpa batas 25)."""
    products = _load_products(game["code"])
    return [
        discord.SelectOption(
            label=with_price(p["label"], f"Rp {p['harga']:,}"),
            emoji=_diamond_emoji(),
            description=game["name"],
            value=str(p["id"]),
        ) for p in products
    ]


async def _ml_handle_product(interaction: discord.Interaction, game: dict, value: str):
    """Dipanggil saat member memilih produk dari dropdown (terpaginasi)."""
    pid = int(value)
    conn = get_conn()
    row = conn.execute(
        "SELECT id, label, dm, harga FROM game_products WHERE id=? AND active=1", (pid,)
    ).fetchone()
    conn.close()
    if not row:
        await interaction.response.send_message("Produk tidak ditemukan.", ephemeral=True)
        return
    product = dict(row)
    from utils.service_info import get_service_info, build_info_embed
    info = get_service_info("ml")
    color = game.get("color", 0x3498DB)
    has_info = any([info["description"], info["terms"], info["payment_info"]])
    if has_info:
        embed = build_info_embed(f"Topup {game['name']}", info, color)
        embed.add_field(
            name="🛒 Produk Dipilih",
            value=f"**{product['label']}** — Rp {product['harga']:,}",
            inline=False
        )
        view = MLConfirmView(game=game, product=product)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    else:
        await interaction.response.send_modal(GameFormModal(game=game, product=product))


class GameSelect(discord.ui.Select):
    def __init__(self):
        games = _load_games()
        options = [
            discord.SelectOption(
                label=g["name"], value=g["code"],
                emoji=_game_emoji(g["code"]),
                description=f"Topup {g['name']}",
            )
            for g in games[:25]
        ] or [discord.SelectOption(label="Tidak ada game aktif", value="none")]
        super().__init__(
            placeholder="Pilih game untuk topup...", options=options, custom_id="ml_game_select"
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Tidak ada game tersedia.", ephemeral=True)
            return
        game = _get_game(self.values[0])
        if not game:
            await interaction.response.send_message("Game tidak ditemukan.", ephemeral=True)
            return
        options = _build_product_options(game)
        if not options:
            await interaction.response.send_message(
                f"Belum ada produk aktif untuk **{game['name']}**.", ephemeral=True
            )
            return
        view = PaginatedSelectView(
            options,
            on_select=lambda i, v, g=game: _ml_handle_product(i, g, v),
            placeholder=f"Pilih produk {game['name']}",
            owner_id=interaction.user.id,
        )
        await interaction.response.send_message(
            f"Pilih produk **{game['name']}**:", view=view, ephemeral=True
        )


class MLBuyView(discord.ui.View):
    def __init__(self, store_open: bool | None = None):
        super().__init__(timeout=None)
        self.add_item(GameSelect())
        store_open = is_store_open() if store_open is None else store_open
        if not store_open:
            for child in self.children:
                child.disabled = True


# ─── Cog ─────────────────────────────────────────────────────────────────────

class MLStore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        _migrate_db()
        self.active_tickets = load_ml_tickets()
        self.catalog_message_id = None

    @commands.command(name="mlcatalog")
    async def mlcatalog(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        from utils.config import ML_CATALOG_CHANNEL_ID
        ch = ctx.guild.get_channel(ML_CATALOG_CHANNEL_ID)
        if not ch:
            await ctx.send("Channel ML catalog tidak ditemukan!", delete_after=5)
            return
        games = _load_games()
        game_list = "\n".join(f"• **{g['name']}**" for g in games) or "Belum ada game aktif."
        embed = discord.Embed(
            title=mltext.load_text("catalog_title"),
            description=mltext.render_text("catalog_desc", store=STORE_NAME, games=game_list),
            color=0x3498DB
        )
        from utils import catalog_settings
        _thumb = catalog_settings.get_thumbnail("ml")
        if _thumb:
            embed.set_thumbnail(url=_thumb)
        embed.set_footer(text=mltext.render_text("catalog_footer", store=STORE_NAME))
        if self.catalog_message_id:
            try:
                msg = await ch.fetch_message(self.catalog_message_id)
                await msg.edit(embed=embed, view=MLBuyView(store_open=is_store_open()))
                await ctx.send(f"Catalog ML diperbarui di {ch.mention}", delete_after=5)
                return
            except Exception:
                pass
        async for msg in ch.history(limit=20):
            if msg.author == ctx.guild.me:
                try:
                    await msg.delete()
                except Exception:
                    pass
        sent = await ch.send(embed=embed, view=MLBuyView(store_open=is_store_open()))
        self.catalog_message_id = sent.id
        await ctx.send(f"Catalog ML dikirim ke {ch.mention}", delete_after=5)

    async def refresh_catalog(self):
        """Refresh view catalog ML (enable/disable tombol) based on store open/close."""
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        from utils.config import ML_CATALOG_CHANNEL_ID
        ch = guild.get_channel(ML_CATALOG_CHANNEL_ID)
        if not ch:
            return
        if not self.catalog_message_id:
            # Try to find the last bot message in the catalog channel.
            async for msg in ch.history(limit=20):
                if msg.author == guild.me and msg.embeds:
                    self.catalog_message_id = msg.id
                    break
        if not self.catalog_message_id:
            return
        try:
            msg = await ch.fetch_message(self.catalog_message_id)
        except Exception:
            return
        games = _load_games()
        game_list = "\n".join(f"• **{g['name']}**" for g in games) or "Belum ada game aktif."
        embed = discord.Embed(
            title=mltext.load_text("catalog_title"),
            description=mltext.render_text("catalog_desc", store=STORE_NAME, games=game_list),
            color=0x3498DB
        )
        from utils import catalog_settings
        _thumb = catalog_settings.get_thumbnail("ml")
        if _thumb:
            embed.set_thumbnail(url=_thumb)
        embed.set_footer(text=mltext.render_text("catalog_footer", store=STORE_NAME))
        await msg.edit(embed=embed, view=MLBuyView(store_open=is_store_open()))

    @commands.command(name="mlselesai")
    async def mlselesai(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket ML aktif.", delete_after=5)
            return
        ticket = self.active_tickets[channel_id]
        member = ctx.guild.get_member(ticket["user_id"])
        closed_at = datetime.datetime.now(datetime.timezone.utc)
        await ctx.send(
            content=member.mention if member else None,
            embed=ticket_ui.ticket_success_embed(
                mltext.render_text("done_success", store=STORE_NAME)
            ),
        )
        await asyncio.sleep(5)
        transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
        transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            try:
                await transcript_ch.send(
                    content=f"Transcript {ticket.get('game','ML')} — {ctx.channel.name}",
                    file=transcript_file
                )
            except Exception as e:
                print(f"[WARNING] Gagal kirim transcript ML: {e}")
        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        item_str = ticket.get("item_label", f"{ticket.get('dm', 0)} Diamond")
        from utils.db import log_transaction, set_transaction_log_message
        from utils.config import TESTIMONI_CHANNEL_ID
        tx_id = None
        try:
            opened_at_dt = datetime.datetime.fromisoformat(ticket["opened_at"]) if ticket.get("opened_at") else None
            durasi = int((closed_at - opened_at_dt).total_seconds()) if opened_at_dt else 0
            tx_id = log_transaction(
                layanan=ticket.get("game", "ML").lower(), nominal=ticket.get("harga", 0) or 0,
                item=item_str,
                admin_id=ctx.author.id, user_id=ticket.get("user_id"),
                closed_at=closed_at, durasi_detik=durasi, qty=1,
            )
        except Exception as e:
            print(f"[LOG] Gagal log transaksi ml: {e}")
        if log_ch:
            from cogs.top_spender import top_spender_badge
            text = ticket_ui.success_log_text(
                seller=ctx.author.mention,
                buyer=member.mention if member else f"<@{ticket['user_id']}>",
                product=item_str,
                qty=1,
                harga=ticket.get("harga", 0) or 0,
                rating=None,
                rating_channel_id=TESTIMONI_CHANNEL_ID,
                buyer_badge=top_spender_badge(ticket.get("user_id")),
            )
            try:
                msg = await log_ch.send(text)
                if tx_id:
                    set_transaction_log_message(tx_id, log_ch.id, msg.id)
            except Exception as e:
                print(f"[ML] Gagal kirim log: {e}")

        # Refresh leaderboard Top Spender (transaksi baru tercatat)
        try:
            from cogs.top_spender import refresh_top_spender
            await refresh_top_spender(self.bot)
        except Exception as e:
            print(f"[TopSpender] refresh error (ML): {e}")

        try:
            royal_role = discord.utils.get(ctx.guild.roles, name="Royal Customer")
            if royal_role and member:
                m = ctx.guild.get_member(ticket.get("user_id"))
                if m and royal_role not in m.roles:
                    await m.add_roles(royal_role)
        except Exception as e:
            print(f"[ROLE] Gagal assign Royal Customer: {e}")
        delete_ml_ticket(channel_id)
        del self.active_tickets[channel_id]
        await ctx.channel.delete()

    @commands.command(name="mlbatal")
    async def mlbatal(self, ctx, *, alasan: str = "Tidak ada alasan diberikan."):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket ML aktif.", delete_after=5)
            return
        embed = ticket_ui.ticket_cancel_embed(
            by_mention=ctx.author.mention, reason=alasan, title=mltext.load_text("cancel_title")
        )
        await ctx.send(embed=embed)
        await asyncio.sleep(5)
        delete_ml_ticket(channel_id)
        del self.active_tickets[channel_id]
        await ctx.channel.delete()


async def setup(bot):
    await bot.add_cog(MLStore(bot))
    bot.add_view(MLBuyView())
    print("Cog MLStore siap.")
