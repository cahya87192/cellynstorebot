"""Konfigurasi terpusat (dibaca dari .env).

Untuk portabilitas multi-server (self-host), SEMUA nilai spesifik-server diambil
dari environment variables. Helper di bawah membuat bot:
  - TIDAK crash dengan traceback membingungkan saat ada var wajib yang kosong;
    sebagai gantinya var yang hilang dikumpulkan & dilaporkan rapi oleh
    validate_required() (dipanggil saat startup di main.py).
  - tetap berjalan apa adanya untuk server lama (default = nilai server semula).
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Dikumpulkan saat import; dilaporkan oleh validate_required() di startup.
MISSING_REQUIRED = []


def _int(name, default=0, required=False):
    """Ambil env var sebagai int dengan aman.

    - required=True: bila kosong/tidak ada, catat ke MISSING_REQUIRED & kembalikan
      default (TIDAK me-raise saat import, supaya validate_required bisa melapor
      semua yang kurang sekaligus dengan pesan ramah).
    - nilai non-numerik diperlakukan seperti kosong (dicatat bila required).
    """
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        if required:
            MISSING_REQUIRED.append(name)
        return default
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        if required:
            MISSING_REQUIRED.append(name)
        return default


def _str(name, default=""):
    val = os.getenv(name)
    return val if (val is not None and str(val).strip() != "") else default


def validate_required():
    """Kembalikan daftar nama env var WAJIB yang belum diisi (kosong = semua OK).

    Dipanggil di startup (main.py). Bila tidak kosong, bot menampilkan panduan
    lalu berhenti dengan rapi — bukan traceback.
    """
    return list(MISSING_REQUIRED)


# ── WAJIB (bot tidak berfungsi tanpa ini) ────────────────────────────────────
GUILD_ID = _int("GUILD_ID", required=True)
MIDMAN_CHANNEL_ID = _int("MIDMAN_CHANNEL_ID", required=True)
TICKET_CATEGORY_ID = _int("TICKET_CATEGORY_ID", required=True)
ADMIN_ROLE_ID = _int("ADMIN_ROLE_ID", required=True)
TRANSCRIPT_CHANNEL_ID = _int("TRANSCRIPT_CHANNEL_ID", required=True)
LOG_CHANNEL_ID = _int("LOG_CHANNEL_ID", required=True)
BACKUP_CHANNEL_ID = _int("BACKUP_CHANNEL_ID", required=True)
ERROR_LOG_CHANNEL_ID = _int("ERROR_LOG_CHANNEL_ID", required=True)
ROBUX_CATALOG_CHANNEL_ID = _int("ROBUX_CATALOG_CHANNEL_ID", required=True)
ML_CATALOG_CHANNEL_ID = _int("ML_CATALOG_CHANNEL_ID", required=True)

# Nama toko: dipakai di SEMUA embed/footer/transcript. Ganti via .env untuk
# rebranding penuh (tidak ada "Cellyn" yang hardcoded di kode).
STORE_NAME = _str("STORE_NAME", "Cellyn Store")

# ── Opsional (punya default aman) ────────────────────────────────────────────
VILOG_CHANNEL_ID = _int("VILOG_CHANNEL_ID", 0)
VILOG_CATALOG_CHANNEL_ID = _int("VILOG_CATALOG_CHANNEL_ID", 1493576431718895677)
DANA_NUMBER = _str("DANA_NUMBER", "-")
BCA_NUMBER = _str("BCA_NUMBER", "-")
# Channel auto-reply layanan "lainnya": member ketik kata kunci -> bot balas item.
LAINNYA_AUTOREPLY_CHANNEL_ID = _int("LAINNYA_AUTOREPLY_CHANNEL_ID", 1508564472141447389)
# Channel publikasi ulasan/rating member (dipakai sistem reviews).
TESTIMONI_CHANNEL_ID = _int("TESTIMONI_CHANNEL_ID", 0)
# Role badge reviewer aktif (0 = nonaktif).
REVIEWER_BADGE_ROLE_ID = _int("REVIEWER_BADGE_ROLE_ID", 0)
REVIEWER_BADGE_THRESHOLD = _int("REVIEWER_BADGE_THRESHOLD", 3)
# Channel panel klaim garansi (0 = nonaktif).
WARRANTY_CHANNEL_ID = _int("WARRANTY_CHANNEL_ID", 0)
# Channel laporan harian otomatis (0 = nonaktif).
DAILY_REPORT_CHANNEL_ID = _int("DAILY_REPORT_CHANNEL_ID", 1476351037412610048)

AUTOPOSTER_TOKEN = _str("AUTOPOSTER_TOKEN", "")

# Batas tiket AKTIF per member per layanan.
MAX_TICKETS_PER_SERVICE = _int("MAX_TICKETS_PER_SERVICE", 5)

# Masa garansi default (hari) untuk produk non-langganan.
WARRANTY_DEFAULT_DAYS = _int("WARRANTY_DEFAULT_DAYS", 7)

# Hari sebelum langganan habis bot kirim DM follow-up perpanjangan.
SUB_FOLLOWUP_LEAD_DAYS = _int("SUB_FOLLOWUP_LEAD_DAYS", 3)

# Channel ADMIN untuk insight pelanggan saat tiket dibuka (0 = pakai LOG_CHANNEL_ID).
CUSTOMER_INSIGHT_CHANNEL_ID = _int("CUSTOMER_INSIGHT_CHANNEL_ID", 0)

# Badge Top Spender pada log transaksi (emoji unicode / custom server). Kosong = nonaktif.
TOP_SPENDER_BADGE = _str("TOP_SPENDER_BADGE", "<a:GreenCrown:1480340921705959493>")

# Channel papan antrian publik (ringkas/anonim untuk member). 0 = nonaktif.
PUBLIC_QUEUE_CHANNEL_ID = _int("PUBLIC_QUEUE_CHANNEL_ID", 1513212206131449916)


# ─────────────────────────────────────────────────────────────────────────────
# PORTABILITAS: ID channel/role/emoji yang dulu hardcoded di tiap cog. Default =
# nilai server semula, jadi tanpa .env perilaku tidak berubah; server lain
# tinggal override. (Produk/katalog TIDAK di sini — itu data per-toko via panel.)
# ─────────────────────────────────────────────────────────────────────────────

# Channel
GENERAL_CHANNEL_ID = _int("GENERAL_CHANNEL_ID", 1476350394526339084)
GP_CATALOG_CHANNEL_ID = _int("GP_CATALOG_CHANNEL_ID", 1478917118715236603)
LAINNYA_CATALOG_CHANNEL_ID = _int("LAINNYA_CATALOG_CHANNEL_ID", 1476349829113315489)
OWO_STOK_CHANNEL_ID = _int("OWO_STOK_CHANNEL_ID", 1511134940643983371)
STATUS_VOICE_CHANNEL_ID = _int("STATUS_VOICE_CHANNEL_ID", 1476382504838500362)
ADMIN_STATS_CHANNEL_ID = _int("ADMIN_STATS_CHANNEL_ID", 1512224258565079130)

# Role
BOOST_ROLE_ID = _int("BOOST_ROLE_ID", 1476362606552809683)
CUSTOMER_ROLE_ID = _int("CUSTOMER_ROLE_ID", 1476360559048786083)
TOP_SPENDER_ROLE_ID = _int("TOP_SPENDER_ROLE_ID", 1508950886251106517)
OWO_NOTIF_ROLE_ID = _int("OWO_NOTIF_ROLE_ID", 1496781799211270194)
ROYAL_CUSTOMER_ROLE_NAME = _str("ROYAL_CUSTOMER_ROLE_NAME", "Royal Customer")

# Emoji server (boleh unicode juga). Kosongkan untuk fallback default di cog.
ROBUX_EMOJI = _str("ROBUX_EMOJI", "<:Robux:1480480351611654224>")
DIAMOND_EMOJI = _str("DIAMOND_EMOJI", "<:diamond:1510720539403096267>")
QUEUE_SERVICE_EMOJI = _str("QUEUE_SERVICE_EMOJI", "<:symbolcheck:1480599052109217892>")
QUEUE_HANDLED_EMOJI = _str("QUEUE_HANDLED_EMOJI", "<:emoji:1480573101753503896>")
