"""Unit test backup/restore database penuh (utils/db_backup.py)."""
import os

from utils import db_backup as dbk


def test_is_sqlite_bytes():
    assert dbk.is_sqlite_bytes(b"SQLite format 3\x00rest of file") is True
    assert dbk.is_sqlite_bytes(b"bukan sqlite") is False
    assert dbk.is_sqlite_bytes(b"") is False
    assert dbk.is_sqlite_bytes(None) is False


def test_human_size():
    assert dbk.human_size(0) == "0 B"
    assert dbk.human_size(500) == "500 B"
    assert dbk.human_size(2048) == "2.0 KB"
    assert dbk.human_size(5 * 1024 * 1024) == "5.0 MB"


def test_db_path_follows_fixture(db):
    assert dbk.db_path() == db.DB_FILE


def test_db_size_and_read(db):
    # fixture sudah init_db -> file ada & berisi
    assert dbk.db_size() > 0
    data = dbk.read_db_bytes()
    assert dbk.is_sqlite_bytes(data)


def test_backup_copy_creates_file(db):
    path = dbk.backup_copy()
    assert path and os.path.exists(path)
    assert path.startswith(db.DB_FILE + ".bak-")
    # isi salinan = isi DB asli
    with open(path, "rb") as f:
        assert dbk.is_sqlite_bytes(f.read())


def test_restore_rejects_non_sqlite(db):
    import pytest
    with pytest.raises(ValueError):
        dbk.restore_from_bytes(b"file sampah bukan db")


def test_restore_roundtrip(db):
    # ambil snapshot DB sekarang, ubah DB, lalu restore -> kembali.
    snapshot = dbk.read_db_bytes()
    conn = db.get_conn()
    conn.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES ('marker','X')")
    conn.commit()
    conn.close()
    # pastikan marker ada
    conn = db.get_conn()
    assert conn.execute("SELECT value FROM bot_state WHERE key='marker'").fetchone()["value"] == "X"
    conn.close()
    # restore ke snapshot lama (tanpa marker)
    res = dbk.restore_from_bytes(snapshot)
    assert res["ok"] is True and res["backup"]
    conn = db.get_conn()
    row = conn.execute("SELECT value FROM bot_state WHERE key='marker'").fetchone()
    conn.close()
    assert row is None  # marker hilang karena DB dikembalikan ke snapshot
