"""Unit test logika murni label status toko (utils/store_status.py).

Bagian Discord (cogs/store_status.py) tidak diuji di sini; fokus pada simpan/muat
label buka/tutup (fallback default) lewat bot_state.
"""
from utils import store_status as s


def test_default_labels(db):
    assert s.get_open_label() == s.DEFAULT_OPEN_LABEL
    assert s.get_close_label() == s.DEFAULT_CLOSE_LABEL


def test_save_and_load_open_label(db):
    s.set_open_label("🟢 Toko Buka")
    assert s.get_open_label() == "🟢 Toko Buka"
    # label tutup tetap default
    assert s.get_close_label() == s.DEFAULT_CLOSE_LABEL


def test_save_and_load_close_label(db):
    s.set_close_label("● Toko Tutup")
    assert s.get_close_label() == "● Toko Tutup"
    assert s.get_open_label() == s.DEFAULT_OPEN_LABEL


def test_empty_string_resets_to_default(db):
    s.set_open_label("custom buka")
    s.set_close_label("custom tutup")
    s.set_open_label("")
    s.set_close_label("")
    assert s.get_open_label() == s.DEFAULT_OPEN_LABEL
    assert s.get_close_label() == s.DEFAULT_CLOSE_LABEL


def test_none_keeps_existing(db):
    s.set_open_label("tetap")
    s.set_open_label(None)
    assert s.get_open_label() == "tetap"


def test_get_label_by_status(db):
    assert s.get_label(True) == s.DEFAULT_OPEN_LABEL
    assert s.get_label(False) == s.DEFAULT_CLOSE_LABEL
    s.set_open_label("BUKA")
    s.set_close_label("TUTUP")
    assert s.get_label(True) == "BUKA"
    assert s.get_label(False) == "TUTUP"
