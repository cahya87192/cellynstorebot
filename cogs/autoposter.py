import os
import asyncio
import traceback
from datetime import datetime

import aiohttp
from discord.ext import commands, tasks

from utils.autoposter_settings import (
    get_autopost_tasks,
    update_autopost_last_post,
    log_autopost_history,
    init_autopost_tables,
)

LOOP_INTERVAL = 60          # detik antar pengecekan loop
MAX_SEND_RETRIES = 3        # percobaan ulang per channel (mis. saat rate-limit)
DISCORD_API = "https://discord.com/api/v9"


class AutoPosterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        init_autopost_tables()
        print("Cog AutoPoster siap.")
        self.autopost_loop.start()

    def cog_unload(self):
        self.autopost_loop.cancel()
        # Tutup session HTTP yang dipakai bersama (dijadwalkan di loop bot).
        if self.session and not self.session.closed:
            try:
                self.bot.loop.create_task(self.session.close())
            except Exception:
                pass

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Satu ClientSession dipakai ulang selama cog hidup (hemat resource)."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    @staticmethod
    def _resolve_token(task: dict) -> str:
        """Utamakan token dari environment saat runtime; fallback ke token
        tersimpan demi kompatibilitas data lama."""
        return os.environ.get("AUTOPOSTER_TOKEN", "") or task.get("user_token", "") or ""

    @staticmethod
    def _is_due(task: dict) -> bool:
        """Tentukan apakah task sudah waktunya post, berdasarkan
        last_post (atau created_at bila belum pernah) + interval.
        Pendekatan ini tahan-restart dan tidak bergantung akumulasi counter."""
        interval_sec = max(1, int(task.get("interval_minutes", 1))) * 60
        ref_raw = task.get("last_post") or task.get("created_at")
        if not ref_raw:
            return True
        try:
            ref = datetime.fromisoformat(ref_raw)
        except (ValueError, TypeError):
            return True
        return (datetime.now() - ref).total_seconds() >= interval_sec

    @tasks.loop(seconds=LOOP_INTERVAL)
    async def autopost_loop(self):
        try:
            tasks_list = get_autopost_tasks()
        except Exception:
            print("[AUTOPOST] Gagal membaca tasks:\n" + traceback.format_exc())
            return

        for task in tasks_list:
            # Bungkus tiap task agar satu error tak menjatuhkan task lain.
            try:
                if not task.get("is_active"):
                    continue
                if not (task.get("force_post") or self._is_due(task)):
                    continue

                token = self._resolve_token(task)
                channel_ids = [c.strip() for c in str(task["channel_id"]).split(",") if c.strip()]

                results = []
                all_success = True
                for cid in channel_ids:
                    ok, info = await self._post_to_channel(cid, task["message"], token)
                    results.append(f"#{cid}: {info}")
                    if not ok:
                        all_success = False

                detail = " | ".join(results) if results else "tidak ada channel valid"
                if not channel_ids:
                    all_success = False
                if not token:
                    all_success = False
                    detail = "AUTOPOSTER_TOKEN kosong"

                log_autopost_history(
                    task["id"], task["message"],
                    "success" if all_success else "failed",
                    detail,
                )
                # Selalu set last_post (dan bersihkan force_post) supaya timer
                # mundur satu interval penuh, baik sukses maupun gagal.
                update_autopost_last_post(task["id"])
            except Exception:
                print(f"[AUTOPOST] Error pada task {task.get('id')}:\n" + traceback.format_exc())

    @autopost_loop.before_loop
    async def before_autopost_loop(self):
        await self.bot.wait_until_ready()
        await self._ensure_session()
        print("[AUTOPOST] Loop ready...")

    @autopost_loop.error
    async def autopost_loop_error(self, error):
        # Cegah loop mati permanen: log lalu mulai ulang.
        print("[AUTOPOST] Loop crash, restart:\n" +
              "".join(traceback.format_exception(type(error), error, error.__traceback__)))
        if not self.autopost_loop.is_running():
            self.autopost_loop.restart()

    async def _post_to_channel(self, channel_id: str, message: str, user_token: str):
        """Kirim pesan ke channel. Mengembalikan (ok, info) di mana info berisi
        kode status / alasan error untuk dicatat ke history.
        Menangani rate-limit (HTTP 429) dengan menghormati retry_after."""
        if not user_token:
            return False, "no-token"

        session = await self._ensure_session()
        headers = {"Authorization": user_token, "Content-Type": "application/json"}
        payload = {"content": message}
        url = f"{DISCORD_API}/channels/{channel_id}/messages"

        for attempt in range(1, MAX_SEND_RETRIES + 1):
            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status in (200, 201):
                        return True, str(resp.status)
                    if resp.status == 429:
                        # Rate limited: tunggu sesuai retry_after lalu coba lagi.
                        retry_after = 1.0
                        try:
                            body = await resp.json()
                            retry_after = float(body.get("retry_after", 1.0))
                        except Exception:
                            hdr = resp.headers.get("Retry-After")
                            if hdr:
                                try:
                                    retry_after = float(hdr)
                                except ValueError:
                                    retry_after = 1.0
                        if attempt < MAX_SEND_RETRIES:
                            await asyncio.sleep(min(retry_after, 30) + 0.25)
                            continue
                        return False, "429 rate-limited"
                    # Error lain (403/404/401/dst): tidak usah retry.
                    return False, f"HTTP {resp.status}"
            except asyncio.TimeoutError:
                if attempt < MAX_SEND_RETRIES:
                    await asyncio.sleep(1.0)
                    continue
                return False, "timeout"
            except Exception as e:
                return False, f"err:{type(e).__name__}"
        return False, "gagal"


async def setup(bot):
    await bot.add_cog(AutoPosterCog(bot))
