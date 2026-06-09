"""Backup & restore database penuh (midman.db).

Berbeda dengan utils.text_backup (khusus teks editor), modul ini menangani SELURUH
file database SQLite: produk, stok, tiket, transaksi, rating, dst. Berguna untuk
cadangan menyeluruh / pindah server / jaga-jaga sebelum reset host.

Catatan: path DB diambil DINAMIS dari utils.db.DB_FILE (bukan di-cache) supaya
test yang me-monkeypatch DB_FILE tetap bekerja.
"""
import datetime
import os
import shutil

# Magic header file SQLite 3 (16 byte pertama) untuk validasi upload restore.
SQLITE_MAGIC = b"SQLite format 3\x00"


def db_path():
    """Path file DB aktif (dinamis dari utils.db.DB_FILE)."""
    import utils.db as realdb
    return realdb.DB_FILE


def db_size():
    """Ukuran file DB dalam byte (0 bila belum ada)."""
    p = db_path()
    try:
        return os.path.getsize(p)
    except OSError:
        return 0


def read_db_bytes():
    """Isi file DB sebagai bytes (untuk diunduh)."""
    with open(db_path(), "rb") as f:
        return f.read()


def is_sqlite_bytes(data):
    """True bila `data` kelihatan seperti file SQLite valid (cek magic header)."""
    return bool(data) and bytes(data[:16]) == SQLITE_MAGIC


def backup_copy():
    """Salin DB saat ini ke `<db>.bak-<timestamp>`. Return path salinan atau None."""
    src = db_path()
    if not os.path.exists(src):
        return None
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{src}.bak-{ts}"
    shutil.copy2(src, dst)
    return dst


def restore_from_bytes(data):
    """Ganti DB aktif dengan `data` (hasil upload).

    Validasi header SQLite dulu; bikin salinan cadangan DB lama sebelum menimpa.
    Return {'ok', 'backup', 'size'}. Raise ValueError bila data bukan SQLite.
    """
    if not is_sqlite_bytes(data):
        raise ValueError("File bukan database SQLite yang valid.")
    backup = backup_copy()
    dst = db_path()
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(data)
    return {"ok": True, "backup": backup, "size": len(data)}


def human_size(n):
    """Format ukuran byte jadi ramah dibaca (KB/MB)."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"
