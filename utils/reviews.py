"""Data layer untuk sistem rating & ulasan (review) toko.

Sumber pemicu rating adalah tabel `transaction_log` (diisi semua layanan saat
tiket ditutup). Modul ini menyimpan rating/ulasan ke tabel `reviews` dan
melacak transaksi terakhir yang sudah diproses lewat `bot_state`.

Catatan desain:
- Satu rating per transaksi: kolom `tx_id` UNIQUE (anti-spam & anti-duplikat).
- `tx_id` boleh NULL untuk rating manual (mis. via command), tetap dibatasi
  oleh logika pemanggil bila perlu.
- Tidak meng-import discord; murni SQLite supaya gampang di-unit-test.
"""

import datetime

from utils.db import get_conn

# Kunci bot_state untuk melacak id transaction_log terakhir yang sudah diminta rating.
LAST_TX_KEY = "reviews_last_tx_id"

# Status review.
STATUS_PENDING = "pending"     # prompt sudah dikirim, menunggu rating member
STATUS_RATED = "rated"         # member sudah memberi rating
STATUS_PUBLISHED = "published" # ulasan sudah diposting ke channel testimoni
STATUS_EXPIRED = "expired"     # lewat 24 jam tanpa rating -> garansi hangus

VALID_RATINGS = (1, 2, 3, 4, 5)

# Batas waktu memberi rating sebelum garansi hangus.
RATING_DEADLINE_HOURS = 24


def init_reviews_db():
    """Buat tabel `reviews` bila belum ada. Idempoten."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id        INTEGER UNIQUE,
            user_id      INTEGER NOT NULL,
            layanan      TEXT,
            item         TEXT,
            nominal      INTEGER DEFAULT 0,
            rating       INTEGER,
            review_text  TEXT,
            status       TEXT NOT NULL DEFAULT 'pending',
            prompt_msg_id    INTEGER,
            published_msg_id INTEGER,
            created_at   TEXT NOT NULL,
            deadline_at  TEXT,
            rated_at     TEXT
        )
        """
    )
    # Migrasi: tambah kolom deadline_at bila DB lama belum punya.
    try:
        c.execute("ALTER TABLE reviews ADD COLUMN deadline_at TEXT")
    except Exception as e:
        if "duplicate column" not in str(e).lower():
            print(f"[Reviews] migrasi deadline_at: {e}")
    # Migrasi: kolom reminded_at (penanda pengingat rating sudah dikirim).
    try:
        c.execute("ALTER TABLE reviews ADD COLUMN reminded_at TEXT")
    except Exception as e:
        if "duplicate column" not in str(e).lower():
            print(f"[Reviews] migrasi reminded_at: {e}")
    # Migrasi: kolom warranty_days (override durasi garansi MANUAL via command).
    # NULL = pakai logika otomatis (durasi langganan / WARRANTY_DEFAULT_DAYS).
    try:
        c.execute("ALTER TABLE reviews ADD COLUMN warranty_days INTEGER")
    except Exception as e:
        if "duplicate column" not in str(e).lower():
            print(f"[Reviews] migrasi warranty_days: {e}")
    # Tabel "pending grant" garansi manual: di-set admin saat tiket masih kebuka
    # (sebelum transaksi tercatat), lalu dipasang ke baris review oleh poller saat
    # transaksi member yang cocok muncul di transaction_log.
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS warranty_pending (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            item        TEXT,
            days        INTEGER NOT NULL,
            note        TEXT,
            granted_by  INTEGER,
            created_at  TEXT NOT NULL,
            consumed_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _deadline_from(created: datetime.datetime) -> datetime.datetime:
    return created + datetime.timedelta(hours=RATING_DEADLINE_HOURS)


# ── Pelacakan transaksi (poller) ────────────────────────────────────────────────
def get_last_tx_id() -> int:
    """Ambil id transaction_log terakhir yang sudah diproses (0 bila belum ada)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (LAST_TX_KEY,))
    row = c.fetchone()
    conn.close()
    if not row:
        return 0
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return 0


def set_last_tx_id(tx_id: int):
    """Simpan id transaction_log terakhir yang sudah diproses."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?, ?)",
        (LAST_TX_KEY, str(int(tx_id))),
    )
    conn.commit()
    conn.close()


def current_max_tx_id() -> int:
    """id terbesar di transaction_log saat ini (0 bila kosong)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT MAX(id) AS m FROM transaction_log")
    row = c.fetchone()
    conn.close()
    return int(row["m"]) if row and row["m"] is not None else 0


def fetch_new_transactions(after_id: int, limit: int = 50) -> list[dict]:
    """Ambil transaksi dengan id > after_id yang punya user_id, urut id menaik."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, layanan, nominal, item, user_id, closed_at
        FROM transaction_log
        WHERE id > ? AND user_id IS NOT NULL
        ORDER BY id ASC
        LIMIT ?
        """,
        (after_id, limit),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── CRUD review ──────────────────────────────────────────────────────────────────
def create_pending(tx_id, user_id: int, layanan: str = None, item: str = None,
                   nominal: int = 0) -> int | None:
    """Buat baris review status 'pending'. Return review id, atau None bila
    tx_id sudah pernah dibuat (UNIQUE) — anti-duplikat."""
    conn = get_conn()
    c = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc)
    deadline = _deadline_from(now)
    try:
        c.execute(
            """
            INSERT INTO reviews (tx_id, user_id, layanan, item, nominal, status, created_at, deadline_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (tx_id, user_id, layanan, item, nominal or 0, STATUS_PENDING,
             now.isoformat(), deadline.isoformat()),
        )
        conn.commit()
        return c.lastrowid
    except Exception as e:
        # IntegrityError (tx_id UNIQUE) -> sudah ada, lewati.
        if "UNIQUE" in str(e).upper():
            return None
        raise
    finally:
        conn.close()


def set_prompt_msg_id(review_id: int, msg_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE reviews SET prompt_msg_id=? WHERE id=?", (msg_id, review_id))
    conn.commit()
    conn.close()


def get_review(review_id: int) -> dict | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM reviews WHERE id=?", (review_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def submit_rating(review_id: int, rating: int, review_text: str = None) -> bool:
    """Simpan rating (1-5) + ulasan opsional, set status 'rated'.

    Hanya berlaku bila review masih 'pending' (anti-double-submit). Return True
    bila tersimpan, False bila tidak valid / sudah dirating sebelumnya.
    """
    if rating not in VALID_RATINGS:
        return False
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        UPDATE reviews
        SET rating=?, review_text=?, status=?, rated_at=?
        WHERE id=? AND status=?
        """,
        (rating, review_text, STATUS_RATED, _now_iso(), review_id, STATUS_PENDING),
    )
    changed = c.rowcount
    conn.commit()
    conn.close()
    return changed > 0


def set_published(review_id: int, published_msg_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE reviews SET status=?, published_msg_id=? WHERE id=?",
        (STATUS_PUBLISHED, published_msg_id, review_id),
    )
    conn.commit()
    conn.close()


# ── Kedaluwarsa 24 jam ───────────────────────────────────────────────────────────
def fetch_expired_pending() -> list[dict]:
    """Ambil review 'pending' yang sudah lewat deadline_at (untuk diberi tahu hangus)."""
    now_iso = _now_iso()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT * FROM reviews
        WHERE status = ? AND deadline_at IS NOT NULL AND deadline_at <= ?
        ORDER BY id ASC
        """,
        (STATUS_PENDING, now_iso),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_expired(review_id: int) -> bool:
    """Tandai review pending menjadi 'expired' (garansi hangus). Hanya bila masih pending."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE reviews SET status=? WHERE id=? AND status=?",
        (STATUS_EXPIRED, review_id, STATUS_PENDING),
    )
    changed = c.rowcount
    conn.commit()
    conn.close()
    return changed > 0


# ── Pengingat rating (sebelum deadline) ───────────────────────────────────────────
# Kirim pengingat bila sisa waktu <= REMINDER_BEFORE_HOURS sebelum deadline.
REMINDER_BEFORE_HOURS = 6


def fetch_due_for_reminder() -> list[dict]:
    """Ambil review 'pending' yang mendekati deadline & belum pernah diingatkan.

    Kriteria: status pending, belum reminded_at, dan deadline_at berada dalam
    rentang (sekarang, sekarang + REMINDER_BEFORE_HOURS]. Tidak mengirim
    pengingat untuk yang sudah lewat deadline (itu ditangani expiry).
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    window_end = (now + datetime.timedelta(hours=REMINDER_BEFORE_HOURS)).isoformat()
    now_iso = now.isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT * FROM reviews
        WHERE status = ? AND reminded_at IS NULL
          AND deadline_at IS NOT NULL
          AND deadline_at > ? AND deadline_at <= ?
        ORDER BY id ASC
        """,
        (STATUS_PENDING, now_iso, window_end),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_reminded(review_id: int) -> bool:
    """Tandai bahwa pengingat sudah dikirim (hanya bila masih pending & belum reminded)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE reviews SET reminded_at=? WHERE id=? AND status=? AND reminded_at IS NULL",
        (_now_iso(), review_id, STATUS_PENDING),
    )
    changed = c.rowcount
    conn.commit()
    conn.close()
    return changed > 0


# ── Statistik & listing ──────────────────────────────────────────────────────────
def get_stats(layanan: str = None) -> dict:
    """Ringkasan rating: jumlah, rata-rata, dan sebaran bintang 1-5.

    Bila `layanan` diberikan, difilter untuk layanan itu (prefix match juga,
    mis. 'lainnya' mencakup 'lainnya:editing')."""
    conn = get_conn()
    c = conn.cursor()
    where = "rating IS NOT NULL"
    params: list = []
    if layanan:
        where += " AND (layanan = ? OR layanan LIKE ?)"
        params += [layanan, f"{layanan}:%"]
    c.execute(f"SELECT COUNT(*) AS n, AVG(rating) AS avg FROM reviews WHERE {where}", params)
    row = c.fetchone()
    n = row["n"] or 0
    avg = round(row["avg"], 2) if row["avg"] is not None else 0.0

    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    c.execute(
        f"SELECT rating, COUNT(*) AS cnt FROM reviews WHERE {where} GROUP BY rating",
        params,
    )
    for r in c.fetchall():
        if r["rating"] in dist:
            dist[r["rating"]] = r["cnt"]
    conn.close()
    return {"count": n, "average": avg, "distribution": dist}


def get_recent_reviews(limit: int = 5, layanan: str = None) -> list[dict]:
    """Ulasan terbaru yang sudah dirating (untuk ditampilkan di command stats)."""
    conn = get_conn()
    c = conn.cursor()
    where = "rating IS NOT NULL"
    params: list = []
    if layanan:
        where += " AND (layanan = ? OR layanan LIKE ?)"
        params += [layanan, f"{layanan}:%"]
    c.execute(
        f"SELECT * FROM reviews WHERE {where} ORDER BY rated_at DESC LIMIT ?",
        params + [limit],
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_reviewers(limit: int = 10) -> list[dict]:
    """Member yang paling banyak memberi rating, urut terbanyak.

    Return list {user_id, count, avg_rating}. Dipakai leaderboard reviewer & badge.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT user_id, COUNT(*) AS count, AVG(rating) AS avg_rating
        FROM reviews
        WHERE rating IS NOT NULL
        GROUP BY user_id
        ORDER BY count DESC, avg_rating DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = c.fetchall()
    conn.close()
    return [
        {"user_id": r["user_id"], "count": r["count"],
         "avg_rating": round(r["avg_rating"], 2) if r["avg_rating"] is not None else 0.0}
        for r in rows
    ]


def count_user_reviews(user_id: int) -> int:
    """Jumlah rating yang sudah diberikan seorang member (untuk badge)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) AS n FROM reviews WHERE user_id=? AND rating IS NOT NULL", (user_id,))
    row = c.fetchone()
    conn.close()
    return row["n"] or 0


def rating_line(layanan: str = None) -> str:
    """Baris ringkas rata-rata rating untuk ditempel di embed katalog (social proof).

    Mengembalikan '' bila belum ada rating, atau mis. '⭐ 4.8/5 · 120 ulasan'.
    Aman dipanggil tanpa Discord (murni SQLite)."""
    try:
        stats = get_stats(layanan)
    except Exception:
        return ""
    if not stats or not stats.get("count"):
        return ""
    avg = stats["average"]
    n = stats["count"]
    full = max(0, min(5, int(round(avg))))
    stars = "⭐" * full + "☆" * (5 - full)
    return f"{stars} **{avg:.1f}/5** · {n} ulasan"



# ── Riwayat order member (#4) ─────────────────────────────────────────────────────
def get_user_transactions(user_id: int, limit: int = 15) -> list[dict]:
    """Riwayat transaksi seorang member dari transaction_log, terbaru dulu.

    Tiap item dilengkapi status rating dari tabel reviews (via tx_id):
    'rated'/'published' (sudah rating), 'pending' (menunggu), 'expired'
    (lewat 24 jam, garansi hangus), atau None (tak ada baris review).
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT t.id, t.layanan, t.nominal, t.item, t.closed_at,
               r.status AS review_status, r.rating AS rating
        FROM transaction_log t
        LEFT JOIN reviews r ON r.tx_id = t.id
        WHERE t.user_id = ?
        ORDER BY t.id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_user_transactions(user_id: int) -> int:
    """Jumlah total transaksi seorang member (untuk ringkasan riwayat)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) AS n FROM transaction_log WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row["n"] or 0


# ── Garansi / klaim (#6) ───────────────────────────────────────────────────────────
# Garansi berlaku bila member sudah memberi rating (status 'rated' atau
# 'published') — yang hanya mungkin bila dilakukan dalam batas 24 jam.
WARRANTY_VALID_STATUSES = (STATUS_RATED, STATUS_PUBLISHED)


def get_warranty_transactions(user_id: int) -> list[dict]:
    """Transaksi member yang BERHAK garansi (sudah dirating dalam 24 jam).

    Return list {tx_id, layanan, item, nominal, rating, rated_at, closed_at},
    terbaru dulu. `closed_at` (dari transaction_log) dipakai menghitung sisa
    masa garansi; bisa None bila tx_id tidak punya pasangan di transaction_log.
    """
    conn = get_conn()
    c = conn.cursor()
    placeholders = ",".join("?" for _ in WARRANTY_VALID_STATUSES)
    c.execute(
        f"""
        SELECT r.tx_id AS tx_id, r.layanan AS layanan, r.item AS item,
               r.nominal AS nominal, r.rating AS rating, r.rated_at AS rated_at,
               r.warranty_days AS warranty_days,
               t.closed_at AS closed_at
        FROM reviews r
        LEFT JOIN transaction_log t ON t.id = r.tx_id
        WHERE r.user_id = ? AND r.status IN ({placeholders})
        ORDER BY r.id DESC
        """,
        (user_id, *WARRANTY_VALID_STATUSES),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def has_valid_warranty(user_id: int) -> bool:
    """True bila member punya minimal satu transaksi yang bergaransi (sudah rating)."""
    conn = get_conn()
    c = conn.cursor()
    placeholders = ",".join("?" for _ in WARRANTY_VALID_STATUSES)
    c.execute(
        f"SELECT 1 FROM reviews WHERE user_id = ? AND status IN ({placeholders}) LIMIT 1",
        (user_id, *WARRANTY_VALID_STATUSES),
    )
    row = c.fetchone()
    conn.close()
    return row is not None


# ── Garansi manual / pending-grant (di-set admin via command) ──────────────────────
# Admin men-"janjikan" durasi garansi untuk transaksi member SEBELUM tiket
# di-close (saat transaksi belum tercatat). Janji ini disimpan di
# `warranty_pending`, lalu dipasang ke baris `reviews.warranty_days` oleh poller
# saat transaksi member yang cocok muncul. Garansi baru AKTIF setelah member
# memberi rating (status rated/published) — konsisten dgn filosofi "rating=garansi".

def add_pending_warranty(user_id: int, days: int, item: str = None,
                         note: str = None, granted_by: int = None) -> int:
    """Catat pending-grant garansi manual untuk transaksi member berikutnya.

    Return id baris pending.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO warranty_pending (user_id, item, days, note, granted_by, created_at)
        VALUES (?,?,?,?,?,?)
        """,
        (user_id, item, int(days), note, granted_by, _now_iso()),
    )
    conn.commit()
    rowid = c.lastrowid
    conn.close()
    return rowid


def list_pending_warranty(user_id: int = None, include_consumed: bool = False) -> list[dict]:
    """Daftar pending-grant (default hanya yang BELUM dipakai).

    Filter per-member bila `user_id` diberikan; urut id menaik (FIFO).
    """
    conn = get_conn()
    c = conn.cursor()
    where = []
    params: list = []
    if user_id is not None:
        where.append("user_id = ?")
        params.append(user_id)
    if not include_consumed:
        where.append("consumed_at IS NULL")
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    c.execute(f"SELECT * FROM warranty_pending {clause} ORDER BY id ASC", params)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_pending_warranty(grant_id: int, user_id: int = None) -> bool:
    """Hapus pending-grant yang BELUM dipakai (pembatalan oleh admin).

    Bila `user_id` diberikan, hanya menghapus bila milik member itu (jaga-jaga).
    Return True bila ada baris terhapus.
    """
    conn = get_conn()
    c = conn.cursor()
    if user_id is not None:
        c.execute(
            "DELETE FROM warranty_pending WHERE id=? AND user_id=? AND consumed_at IS NULL",
            (grant_id, user_id),
        )
    else:
        c.execute(
            "DELETE FROM warranty_pending WHERE id=? AND consumed_at IS NULL",
            (grant_id,),
        )
    changed = c.rowcount
    conn.commit()
    conn.close()
    return changed > 0


def _item_matches(grant_item, tx_item) -> bool:
    """Cocokkan item grant dengan item transaksi (case-insensitive, substring 2 arah).

    grant_item kosong/None dianggap wildcard (cocok untuk transaksi apa pun).
    """
    gi = (grant_item or "").strip().lower()
    if not gi:
        return True
    ti = (tx_item or "").strip().lower()
    if not ti:
        return False
    return gi in ti or ti in gi


def pop_pending_warranty(user_id: int, item: str = None) -> dict | None:
    """Ambil & tandai-pakai satu pending-grant yang cocok untuk transaksi member.

    Prioritas: grant ber-item yang cocok (lebih spesifik) dulu, lalu grant
    wildcard (item kosong). Di antara yang setara, ambil terlama (FIFO).
    Return baris grant (dict) yang dipakai, atau None bila tak ada yang cocok.
    """
    candidates = list_pending_warranty(user_id, include_consumed=False)
    if not candidates:
        return None
    specific = [g for g in candidates
                if (g.get("item") or "").strip() and _item_matches(g.get("item"), item)]
    wildcard = [g for g in candidates if not (g.get("item") or "").strip()]
    chosen = specific or wildcard
    if not chosen:
        return None
    grant = chosen[0]  # FIFO (sudah urut id ASC)
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE warranty_pending SET consumed_at=? WHERE id=? AND consumed_at IS NULL",
        (_now_iso(), grant["id"]),
    )
    changed = c.rowcount
    conn.commit()
    conn.close()
    if changed == 0:
        return None  # sudah dipakai proses lain (race) -> jangan klaim ganda
    return grant


def set_review_warranty_days(review_id: int, days: int) -> bool:
    """Pasang override durasi garansi (hari) ke sebuah baris review."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE reviews SET warranty_days=? WHERE id=?", (int(days), review_id))
    changed = c.rowcount
    conn.commit()
    conn.close()
    return changed > 0


# ── Laporan harian (#7) ────────────────────────────────────────────────────────────
def get_daily_report(date_str: str) -> dict:
    """Ringkasan transaksi pada satu tanggal (UTC, format 'YYYY-MM-DD').

    Return {
      'date', 'total_tx', 'total_omzet',
      'per_layanan': [{layanan, count, omzet}...],
      'rating_count', 'rating_avg'
    }
    Berbasis transaction_log.closed_at (prefix tanggal) & reviews.rated_at.
    """
    conn = get_conn()
    c = conn.cursor()
    like = f"{date_str}%"

    c.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(nominal),0) AS omzet "
        "FROM transaction_log WHERE closed_at LIKE ?",
        (like,),
    )
    row = c.fetchone()
    total_tx = row["n"] or 0
    total_omzet = row["omzet"] or 0

    c.execute(
        """
        SELECT layanan, COUNT(*) AS count, COALESCE(SUM(nominal),0) AS omzet
        FROM transaction_log
        WHERE closed_at LIKE ?
        GROUP BY layanan
        ORDER BY omzet DESC
        """,
        (like,),
    )
    per_layanan = [
        {"layanan": r["layanan"], "count": r["count"], "omzet": r["omzet"] or 0}
        for r in c.fetchall()
    ]

    c.execute(
        "SELECT COUNT(*) AS n, AVG(rating) AS avg FROM reviews "
        "WHERE rating IS NOT NULL AND rated_at LIKE ?",
        (like,),
    )
    rr = c.fetchone()
    rating_count = rr["n"] or 0
    rating_avg = round(rr["avg"], 2) if rr["avg"] is not None else 0.0

    # Produk terlaris hari itu (berdasarkan jumlah transaksi item yang sama).
    c.execute(
        """
        SELECT item, COUNT(*) AS qty
        FROM transaction_log
        WHERE closed_at LIKE ? AND item IS NOT NULL AND item != ''
        GROUP BY item
        ORDER BY qty DESC, item ASC
        LIMIT 1
        """,
        (like,),
    )
    br = c.fetchone()
    best_item = br["item"] if br else None
    best_item_qty = br["qty"] if br else 0

    conn.close()
    return {
        "date": date_str,
        "total_tx": total_tx,
        "total_omzet": total_omzet,
        "per_layanan": per_layanan,
        "rating_count": rating_count,
        "rating_avg": rating_avg,
        "best_item": best_item,
        "best_item_qty": best_item_qty,
    }
