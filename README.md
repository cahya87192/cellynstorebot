# Midman Bot — Cellyn Store Community

Bot Discord untuk operasional toko digital. Menangani transaksi middleman trade, middleman jual beli, robux store, topup Mobile Legends & Free Fire, Cloud Phone, Discord Nitro, welcome, dan admin panel berbasis web.

---

## Fitur

- **Midman Trade** — tiket perantara tukar item antar dua pihak
- **Midman Jual Beli** — tiket perantara jual beli, admin tahan uang pembeli sampai item konfirmasi oke
- **Robux Store** — katalog item Roblox per kategori dengan rate dinamis
- **Robux Via Login (Vilog)** — topup Robux via login akun Roblox (kelipatan 500)
- **Stock Robux** — tampilkan stock tersedia + total robux keluar di catalog (auto update saat transaksi selesai)
- **ML & FF Topup** — topup diamond Mobile Legends, Free Fire, dan Weekly Diamond Pass (WDP)
- **Cloud Phone & Discord Nitro** — order Redfinger cloud phone dan Discord Nitro via tiket
- **Welcome** — welcome/leave/boost notif dengan GIF, auto-assign role Customer saat member join
- **Auto React** — auto react emoji ke pesan di channel tertentu atau semua pesan admin
- **Server Stats** — voice channel nama otomatis update jumlah member
- **Status Toko (Open/Close)** — voice status otomatis + tombol catalog padam saat toko tutup
- **AutoPost** — auto-post pesan ke channel Discord via user token, support multiple channel, interval persisten
- **Admin Panel Web** — kelola produk ML/FF/WDP/Robux/Lainnya dan statistik transaksi via browser
- **Statistik Transaksi** — dashboard grafik 7 hari dan 30 hari, produk terlaris, jam tersibuk per layanan
- **Royal Customer** — auto-assign role setelah transaksi sukses di semua layanan
- **Antrian Tiket** — papan antrian admin + papan publik ringkas untuk member, kartu posisi per tiket, prioritas Top Spender, command `!pay`/`!unpay`
- **Top Spender** — leaderboard bulanan + prioritas antrean & badge untuk Top-N pembeli
- **Kartu Profil Member** — `/profil` render kartu PNG (level/XP, tier, badge) yang bisa dikustomisasi penuh via admin panel (Editor Profil)
- **Sticky Message** — `/stick_msg` menjaga pesan tetap di bawah channel
- **Auto-restart** — bot restart otomatis jika crash (max 5x)
- **Notifikasi URL Admin** — URL Cloudflare Tunnel dikirim ke channel admin setiap bot online

---

## Persyaratan

- Python 3.12+
- Termux (Android) atau Linux
- Akun Discord + Bot Token
- User token Discord untuk AutoPost (opsional)

---

## Setup Awal (Perangkat Baru)

### 1. Clone repo
```bash
git clone https://github.com/EqualityDev/midman.git
cd midman
```

### 2. Buat virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup .env
```bash
cp .env.example .env
nano .env  # isi semua variabel
```

### 5. Jalankan
```bash
bash start.sh
```

`start.sh` otomatis melakukan:
- Cek & pull update terbaru dari GitHub
- Init database SQLite
- Seed data produk default jika DB kosong
- Jalankan admin panel di port 5000
- Install cloudflared jika belum ada
- Jalankan Cloudflare Tunnel (URL dikirim ke Discord)
- Jalankan bot dengan auto-restart

---

## Environment Variables

Salin `.env.example` ke `.env` dan isi semua variabel:

| Variable | Keterangan |
|---|---|
| `TOKEN` | Token bot Discord |
| `GUILD_ID` | ID server Discord |
| `STORE_NAME` | Nama store (tampil di embed) |
| `ADMIN_ROLE_ID` | ID role admin |
| `TICKET_CATEGORY_ID` | ID kategori channel tiket |
| `LOG_CHANNEL_ID` | ID channel log transaksi |
| `TRANSCRIPT_CHANNEL_ID` | ID channel transcript tiket |
| `BACKUP_CHANNEL_ID` | ID channel backup |
| `ERROR_LOG_CHANNEL_ID` | ID channel log error + notifikasi admin panel |
| `MIDMAN_CHANNEL_ID` | ID channel midman |
| `ROBUX_CATALOG_CHANNEL_ID` | ID channel catalog robux |
| `ML_CATALOG_CHANNEL_ID` | ID channel catalog ML/FF |
| `DANA_NUMBER` | Nomor DANA |
| `BCA_NUMBER` | Nomor BCA |
| `TESTIMONI_CHANNEL_ID` | ID channel testimoni |
| `VILOG_CHANNEL_ID` | ID channel log untuk Vilog (opsional) |
| `VILOG_CATALOG_CHANNEL_ID` | ID channel layanan/catalog Vilog |
| `AUTOPOSTER_TOKEN` | User token Discord untuk AutoPost (opsional) |
| `RELAY_SOURCE_CHANNEL_ID` | Source channel relay (opsional) |
| `RELAY_WEBHOOK_URL` | Webhook URL relay (opsional) |

### Opsional (Admin Panel)
| Variable | Default | Keterangan |
|---|---|---|
| `ADMIN_PASSWORD` | `cellyn123` | Password login admin panel |
| `ADMIN_SECRET` | *(auto)* | Secret key Flask session |
| `ADMIN_PORT` | `5000` | Port admin panel |

### Portabilitas multi-server (opsional)

Semua key di bawah **punya default** (nilai server Cellyn), jadi bot tetap jalan
tanpa mengisinya. Server lain cukup meng-override yang relevan di `.env` — **tidak
perlu mengubah kode**.

| Variable | Keterangan |
|---|---|
| `GENERAL_CHANNEL_ID` | Channel umum (sapaan, dll) |
| `GP_CATALOG_CHANNEL_ID` | Channel katalog GP |
| `LAINNYA_CATALOG_CHANNEL_ID` | Channel katalog "Lainnya" |
| `OWO_STOK_CHANNEL_ID` | Channel embed stok OWO |
| `STATUS_VOICE_CHANNEL_ID` | Voice channel status toko (Open/Close) |
| `ADMIN_STATS_CHANNEL_ID` | Channel kartu performa admin |
| `PUBLIC_QUEUE_CHANNEL_ID` | Channel papan antrian publik (member) |
| `BOOST_ROLE_ID` | Role booster |
| `CUSTOMER_ROLE_ID` | Role customer (auto-assign saat join) |
| `TOP_SPENDER_ROLE_ID` | Role Top Spender (Top-N) |
| `OWO_NOTIF_ROLE_ID` | Role ping notif stok OWO |
| `ROYAL_CUSTOMER_ROLE_NAME` | Nama role Royal Customer (default `Royal Customer`) |
| `ROBUX_EMOJI` / `DIAMOND_EMOJI` | Emoji custom server untuk katalog |
| `QUEUE_SERVICE_EMOJI` / `QUEUE_HANDLED_EMOJI` | Emoji papan antrian |
| `TOP_SPENDER_BADGE` | Emoji mahkota Top Spender |

> **Catatan multi-server:** bot ini **single-tenant** (1 instance = 1 server = 1
> `midman.db` = 1 admin panel). Untuk dipakai di server lain, model yang didukung
> adalah **self-host**: tiap pemilik server menjalankan salinan bot & panelnya
> sendiri di VPS/hosting masing-masing (token, `.env`, database, dan panel
> terpisah total — data antar-toko tidak tercampur). **Produk/katalog diatur
> sendiri oleh tiap toko lewat admin panel**, tidak diambil dari server lain.

---

## Admin Panel

Admin panel otomatis jalan saat `bash start.sh`. URL Cloudflare Tunnel dikirim ke `ERROR_LOG_CHANNEL` via embed setiap kali bot online.

Akses: buka URL yang dikirim bot di channel error log → login dengan `ADMIN_PASSWORD`

**Fitur:**
- **Dashboard** — ringkasan produk aktif + update rate Robux
- **ML** — tambah, edit, hapus produk Mobile Legends + Weekly Diamond Pass (WDP)
- **FF** — tambah, edit, hapus produk Free Fire
- **Robux** — tambah, edit, nonaktifkan/aktifkan, hapus item + tambah kategori baru
- **GP Store** — atur rate Garena Point
- **Lainnya** — tambah, edit, nonaktifkan/aktifkan, hapus produk Cloud Phone & Discord Nitro + tambah kategori baru
- **QRIS** — atur rekening QRIS
- **Statistik** — grafik transaksi 7 hari dan 30 hari, produk terlaris, jam tersibuk per layanan
- **AutoPost** — atur auto-post pesan ke channel Discord
- **Info Layanan** — kelola info layanan yang ditampilkan sebelum buka tiket

Perubahan produk via web langsung berlaku ke bot tanpa restart.

---

## Command Reference

### Midman Trade
| Command | Fungsi |
|---|---|
| `!open` | Kirim embed catalog midman |
| `!acc` | Konfirmasi trade selesai |
| `!batal [alasan]` | Batalkan tiket midman |
| `!fee [nominal]` | Hitung fee midman |

### Midman Jual Beli
| Command | Fungsi |
|---|---|
| `!jbuang` | Konfirmasi uang dari pembeli diterima |
| `!jbselesai` | Release dana ke penjual (setelah pembeli konfirmasi item) |
| `!jbbatal [alasan]` | Batalkan tiket jual beli |

### Robux Store
| Command | Fungsi |
|---|---|
| `!catalog` | Kirim embed catalog robux |
| `!rate [angka]` | Set rate Robux |
| `!stock` | Lihat stock robux (tersedia + total keluar) |
| `!stockset [robux]` | Set stock robux tersedia |
| `!stockadd [robux]` | Tambah stock robux tersedia |
| `!stockoutadd [robux]` | Tambah robux keluar (total) tanpa mengurangi stock |
| `!stockoutship [robux]` | Robux keluar + kurangi stock (koreksi manual) |
| `!gift` | Konfirmasi gift item selesai |
| `!tolak [alasan]` | Batalkan tiket robux |

### Robux Via Login (Vilog)
| Command | Fungsi |
|---|---|
| `!vilogcatalog` | Kirim/refresh embed layanan Vilog |
| `!ratevilog [angka]` | Set rate Vilog |
| `!vilogdone` | Konfirmasi Vilog selesai |
| `!vilogbatal [alasan]` | Batalkan tiket Vilog |

### GP Topup (Gamepass)
| Command | Fungsi |
|---|---|
| `!gpcatalog` | Kirim embed catalog GP Topup |
| `!gprate [angka]` | Set rate GP |
| `!gplink [url]` | Kirim link gamepass (opsional) |
| `!gpdone` | Konfirmasi gamepass sudah dibeli (selesai) |
| `!gpbatal [alasan]` | Batalkan tiket GP |

### ML & FF Topup
| Command | Fungsi |
|---|---|
| `!mlcatalog` | Kirim embed catalog ML/FF/WDP |
| `!mlselesai` | Konfirmasi topup selesai |
| `!mlbatal [alasan]` | Batalkan tiket ML/FF |

### Cloud Phone & Discord Nitro
| Command | Fungsi |
|---|---|
| `!lainnya` | Kirim embed katalog Cloud Phone & Nitro |
| `!done` | Tutup tiket sukses |
| `!cancel [alasan]` | Batalkan tiket |

### AutoPost
| Command | Fungsi |
|---|---|
| `!autopost add [#channel] [interval_menit] [pesan]` | Tambah autopost task |
| `!autopost list` | Lihat daftar task |
| `!autopost toggle [id]` | Toggle on/off |
| `!autopost delete [id]` | Hapus task |

### Welcome & Tools
| Command | Fungsi |
|---|---|
| `/setwelcome` | Atur channel/GIF welcome, boost notif, atau nonaktifkan |
| `/setreact` | Set auto react di channel untuk pesan admin |
| `/setreactall` | Set auto react untuk semua user di channel |
| `/reactlist` | Lihat daftar channel auto react |
| `/setstatschannel` | Set voice channel untuk stats member |
| `/unsetstatschannel` | Nonaktifkan stats channel |

### Lainnya
| Command | Fungsi |
|---|---|
| `!cmd` | Tampilkan prefix guide (auto-hapus 10 detik) |
| `!ping` | Cek latency |

> Semua command prefix kecuali `!open` hanya bisa digunakan oleh role admin.

---

## Alur Tiket

### Midman Trade
1. Member klik tombol **⚔️ Midman Trade** di channel midman
2. Isi form: item pihak 1 + item yang diminta
3. Admin bergabung, setup pihak 2 + fee
4. Fee dibayar, admin konfirmasi → trade berlangsung
5. Admin ketik `!acc` untuk tutup tiket

### Midman Jual Beli
1. Penjual klik tombol **🛒 Midman Jual Beli** di channel midman
2. Isi form: deskripsi item + harga
3. Admin setup: tambah pembeli, set fee + penanggung fee
4. Pembeli transfer ke admin sesuai nominal
5. Admin ketik `!jbuang` → konfirmasi uang diterima, serahkan item ke pembeli
6. Pembeli klik **✅ Item Diterima & Sesuai**
7. Admin ketik `!jbselesai` → dana direlease ke penjual, tiket ditutup

### Robux Store
1. Member klik kategori di channel catalog robux
2. Pilih item dari dropdown
3. Transfer sesuai nominal + kirim bukti bayar
4. Admin cek bukti bayar (manual), gift item via Roblox
5. Admin ketik `!gift` untuk tutup tiket

### Robux Via Login (Vilog)
1. Member klik **Order** di channel catalog Vilog
2. Isi form (jumlah robux kelipatan 500, email, password, kode backup, premium)
3. Bayar sesuai instruksi admin + kirim bukti bayar
4. Admin proses topup via login
5. Admin ketik `!vilogdone` untuk tutup tiket

### ML & FF Topup
1. Member pilih diamond / WDP di channel catalog ML
2. Isi form: ID ML + Server ID (untuk ML) atau Player ID (untuk FF)
3. Bayar via QRIS
4. Admin proses topup, ketik `!mlselesai`

### Cloud Phone & Discord Nitro
1. Member klik kategori di channel lainnya
2. Pilih item dari dropdown
3. Tiket terbuka, member ketik **1/2/3** untuk pilih metode bayar
4. Bayar sesuai nominal, kirim bukti transfer
5. Admin proses, ketik `!done` untuk tutup tiket

---

## Struktur File

```
midman/
├── main.py               # Entry point bot + notifikasi URL tunnel
├── admin.py              # Flask admin panel (port 5000)
├── admin_embed.py        # Blueprint untuk embed builder
├── seed.py               # Seed data produk default ke DB
├── start.sh              # Auto-start semua service
├── requirements.txt
├── .env.example
├── utils/
│   ├── config.py              # Semua env variable
│   ├── db.py                  # init_db() + semua tabel SQLite + log_transaction()
│   ├── env_check.py           # Self-check variabel .env saat startup
│   ├── counter.py             # Auto-increment nomor tiket
│   ├── tickets.py             # CRUD tiket midman trade
│   ├── robux_db.py            # CRUD tiket robux + bot_state
│   ├── robux_stock.py         # Stock robux (tersedia + total keluar)
│   ├── gp_db.py               # CRUD GP (gamepass) topup
│   ├── vilog_db.py            # CRUD tiket Vilog (Robux via login)
│   ├── fee.py                 # Kalkulator fee midman
│   ├── transcript.py          # Generate HTML transcript
│   ├── backup.py              # Backup DB berkala ke channel Discord
│   ├── store_hours.py         # Jam operasional (WIB) open/close
│   ├── autoposter_settings.py # CRUD autopost tasks
│   ├── reviews.py             # Data layer rating & ulasan
│   ├── subscription.py        # Parse durasi langganan & hitung kedaluwarsa
│   ├── customer_insight.py    # Insight pelanggan untuk admin saat tiket dibuka
│   ├── layanan.py             # Label layanan terpusat (kode -> nama tampilan)
│   ├── service_info.py        # Baca/simpan info layanan (deskripsi, S&K, bayar)
│   ├── queue.py               # Logika murni antrian tiket (tanpa discord)
│   ├── ticket_ui.py           # Helper tampilan tiket (nama channel, warna, embed)
│   └── paginator.py           # Select menu dengan pagination (reusable)
└── cogs/
    ├── midman.py              # Midman trade
    ├── jualbeli.py            # Midman jual beli
    ├── robux.py               # Robux store
    ├── vilog.py               # Robux via login (Vilog)
    ├── gp.py                  # Topup Robux via Gamepass
    ├── ml.py                  # Topup ML, FF & WDP
    ├── lainnya.py             # Cloud Phone & Discord Nitro
    ├── lainnya_catalog.py     # Data katalog produk "lainnya" (murni data)
    ├── orders.py              # Shared !done & !cancel
    ├── modals.py              # Modal form bersama (buka tiket, setup trade)
    ├── queue.py               # Sistem antrian tiket (papan + posisi)
    ├── store_status.py        # Voice status open/close + refresh catalog
    ├── reviews.py             # Sistem rating & ulasan customer
    ├── warranty.py            # Sistem klaim garansi
    ├── sub_followup.py        # Auto follow-up perpanjangan langganan (DM)
    ├── product_search.py      # Pencarian produk lintas-toko via auto-reply
    ├── admin_stats.py         # Statistik performa admin (kartu publik auto-update)
    ├── top_spender.py         # Leaderboard top spender bulanan
    ├── daily_report.py        # Laporan harian otomatis (omzet & rating)
    ├── server_stats.py        # Voice channel stats member count
    ├── free_game_notifier.py  # Notif game gratis PC (Epic/Steam/GOG/Ubisoft)
    ├── mobile_game_notifier.py # Notif game gratis Android/iOS (GamerPower)
    ├── genshin_notifier.py    # Notif event/banner/redeem code Genshin
    ├── welcome.py             # Welcome/leave/boost notif + auto role Customer
    ├── auto_react.py          # Auto react emoji per channel
    ├── autoposter.py          # Auto-post pesan ke channel via user token
    ├── embed_builder.py       # Custom embed builder
    ├── qr.py                  # QRIS management
    ├── afk.py                 # AFK system
    ├── relay.py               # Relay webhook forwarder
    ├── owo_stok.py            # Kelola stok OWO Cash (/owostok)
    └── views.py               # Shared Discord UI views
```

---

## Database

SQLite (`midman.db`) tidak di-push ke GitHub. Di-generate otomatis saat `bash start.sh`.

**Tabel produk:**
- `ml_products` — produk Mobile Legends
- `wdp_products` — paket Weekly Diamond Pass
- `ff_products` — produk Free Fire
- `robux_products` — item Robux per kategori
- `lainnya_products` — produk Cloud Phone & Discord Nitro

**Tabel transaksi:**
- `tickets` — midman trade
- `jb_tickets` — midman jual beli
- `robux_tickets` — tiket robux
- `gp_tickets` — tiket topup Robux via gamepass
- `vilog_tickets` — tiket topup Robux via login (Vilog)
- `ml_tickets` — tiket ML & FF
- `lainnya_tickets` — tiket Cloud Phone & Nitro
- `transaction_log` — log semua transaksi sukses (untuk statistik)
- `robux_rate` — rate Robux saat ini

**Tabel lainnya:**
- `auto_react` — channel auto react
- `bot_state` — state bot (embed message ID catalog, welcome settings, dll)
- `autopost_tasks` — task autopost (channel, message, interval, user_token, loop_counter)
- `autopost_history` — history posting autopost

---

## Workflow Development

```
Dev → GitHub → Deploy ke hosting
```

Perubahan kode di-push ke GitHub, lalu di-deploy ke hosting production (pull/redeploy di server).

**Catatan:** Folder `data/` (GIF welcome/boost) dan `midman.db` tidak di-track Git. Backup secara berkala.
