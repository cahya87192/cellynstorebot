"""Regresi: path DB harus ABSOLUT & konsisten lintas modul.

Bot dan admin panel bisa dijalankan dari working directory berbeda (lihat
start.sh). Bila DB_FILE relatif, editor panel (tema profil/badge, thumbnail &
emoji katalog) menulis ke file DB berbeda dari yang dibaca bot -> perubahan
seolah tidak berpengaruh. Test ini memastikan semua modul memakai path absolut
ke satu file midman.db yang sama di root repo.
"""
import os


def test_utils_db_path_absolute_repo_anchored():
    from utils import db as realdb
    expected = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(realdb.__file__))), "midman.db"
    )
    assert os.path.isabs(expected)
    assert os.path.basename(expected) == "midman.db"
    # Direktori DB = root repo (induk folder utils/).
    assert os.path.dirname(expected) == os.path.dirname(
        os.path.dirname(os.path.abspath(realdb.__file__))
    )


def test_db_paths_consistent_across_modules():
    # Modul-modul ini punya konstanta DB_FILE sendiri; harus absolut & sama,
    # serta sama dengan path yang dipakai admin panel (root_repo/midman.db).
    from utils import db, backup, autoposter_settings

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(db.__file__)))
    expected = os.path.join(repo_root, "midman.db")

    assert os.path.isabs(backup.DB_FILE)
    assert os.path.isabs(autoposter_settings.DB_FILE)
    assert backup.DB_FILE == expected
    assert autoposter_settings.DB_FILE == expected
