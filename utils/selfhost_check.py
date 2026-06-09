"""Cek kesiapan self-host: status environment variable (logika murni).

Membantu owner yang men-deploy bot di server sendiri memastikan semua variabel
penting di .env sudah diisi. Logika inti `check_env` murni (menerima dict env)
sehingga mudah diuji & dipakai admin panel maupun CLI.

WAJIB = bot tidak berjalan / fitur inti rusak tanpa ini.
DISARANKAN = fitur opsional aktif bila diisi; aman bila kosong (punya default
atau otomatis nonaktif).

Daftar ini mengikuti utils/config.py + token bot (TOKEN) yang dibaca main.py.
"""

# (nama_env, deskripsi singkat)
REQUIRED_VARS = [
    ("TOKEN", "Token bot Discord (tanpa ini bot tidak bisa login)"),
    ("GUILD_ID", "ID server Discord utama"),
    ("MIDMAN_CHANNEL_ID", "Channel panel midman/transaksi"),
    ("TICKET_CATEGORY_ID", "Kategori tempat channel tiket dibuat"),
    ("ADMIN_ROLE_ID", "Role admin/CS"),
    ("TRANSCRIPT_CHANNEL_ID", "Channel arsip transcript tiket"),
    ("LOG_CHANNEL_ID", "Channel log transaksi"),
    ("BACKUP_CHANNEL_ID", "Channel backup database"),
    ("ERROR_LOG_CHANNEL_ID", "Channel log error bot"),
    ("ROBUX_CATALOG_CHANNEL_ID", "Channel katalog Robux"),
    ("ML_CATALOG_CHANNEL_ID", "Channel katalog Topup Diamond Game"),
]

# (nama_env, deskripsi, default_bila_kosong)
RECOMMENDED_VARS = [
    ("STORE_NAME", "Nama toko (branding semua embed)", "Cellyn Store"),
    ("TESTIMONI_CHANNEL_ID", "Channel publikasi ulasan/rating", "nonaktif"),
    ("FAQ_CHANNEL_ID", "Channel embed FAQ", "nonaktif"),
    ("AUTOCS_CHANNEL_ID", "Channel Auto-CS jawab pertanyaan", "ikuti FAQ/nonaktif"),
    ("FEEDBACK_CHANNEL_ID", "Channel tujuan /saran", "pakai LOG_CHANNEL_ID"),
    ("WARRANTY_CHANNEL_ID", "Channel panel klaim garansi", "nonaktif"),
    ("DAILY_REPORT_CHANNEL_ID", "Channel laporan harian", "default lama"),
    ("PUBLIC_QUEUE_CHANNEL_ID", "Channel papan antrian publik", "nonaktif"),
    ("GP_CATALOG_CHANNEL_ID", "Channel katalog Robux via Gamepass", "default lama"),
    ("VILOG_CATALOG_CHANNEL_ID", "Channel katalog Robux via Login", "default lama"),
    ("LAINNYA_CATALOG_CHANNEL_ID", "Channel katalog Layanan Lainnya", "default lama"),
    ("LAINNYA_AUTOREPLY_CHANNEL_ID", "Channel auto-reply layanan lainnya", "default lama"),
    ("ADMIN_STATS_CHANNEL_ID", "Channel statistik admin", "default lama"),
    ("OWO_STOK_CHANNEL_ID", "Channel stok OwO", "default lama"),
    ("STATUS_VOICE_CHANNEL_ID", "Voice channel status toko", "default lama"),
    ("GENERAL_CHANNEL_ID", "Channel umum (sambutan dll)", "default lama"),
    ("CUSTOMER_INSIGHT_CHANNEL_ID", "Channel insight pelanggan", "pakai LOG_CHANNEL_ID"),
    ("BOOST_ROLE_ID", "Role booster server", "default lama"),
    ("CUSTOMER_ROLE_ID", "Role customer", "default lama"),
    ("TOP_SPENDER_ROLE_ID", "Role top spender", "default lama"),
    ("REVIEWER_BADGE_ROLE_ID", "Role badge reviewer aktif", "nonaktif"),
    ("OWO_NOTIF_ROLE_ID", "Role notifikasi OwO", "default lama"),
    ("DANA_NUMBER", "Nomor DANA pembayaran", "-"),
    ("BCA_NUMBER", "Nomor BCA pembayaran", "-"),
    ("USE_CUSTOM_EMOJI", "Saklar global custom emoji (false utk server lain)", "true"),
    ("LAINNYA_USE_CUSTOM_EMOJI", "Custom emoji katalog lainnya", "ikuti USE_CUSTOM_EMOJI"),
    ("AUTOPOSTER_TOKEN", "Token autoposter (fitur opsional)", "nonaktif"),
]


def _is_set(env, name) -> bool:
    val = env.get(name)
    return val is not None and str(val).strip() != ""


def check_env(env) -> dict:
    """Periksa dict environment; kembalikan laporan kesiapan terstruktur.

    Hasil:
      {
        "required":   [{"name","desc","set"}],
        "recommended":[{"name","desc","set","default"}],
        "missing_required": [nama...],
        "required_total": int, "required_set": int,
        "recommended_total": int, "recommended_set": int,
        "ready": bool   # True bila semua WAJIB terisi
      }
    """
    if not isinstance(env, dict):
        env = {}
    required = [
        {"name": n, "desc": d, "set": _is_set(env, n)} for n, d in REQUIRED_VARS
    ]
    recommended = [
        {"name": n, "desc": d, "default": dv, "set": _is_set(env, n)}
        for n, d, dv in RECOMMENDED_VARS
    ]
    missing_required = [r["name"] for r in required if not r["set"]]
    return {
        "required": required,
        "recommended": recommended,
        "missing_required": missing_required,
        "required_total": len(required),
        "required_set": sum(1 for r in required if r["set"]),
        "recommended_total": len(recommended),
        "recommended_set": sum(1 for r in recommended if r["set"]),
        "ready": len(missing_required) == 0,
    }
