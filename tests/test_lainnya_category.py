"""Unit test logika murni info kategori Lainnya (utils/lainnya_category.py).

Bagian Discord (cogs/lainnya.py) tidak diuji di sini; fokus pada CRUD info
kategori (deskripsi & S&K) di tabel lainnya_category_info + fallback default.
"""
from cogs import lainnya_catalog
from utils import lainnya_category as lc

# Ambil satu kategori yang punya default statis untuk diuji.
_SAMPLE_CAT = next(iter(lainnya_catalog.CATEGORY_INFO.keys()))


def test_list_categories_includes_static(db):
    cats = lc.list_categories()
    assert _SAMPLE_CAT in cats
    # urut alfabet & unik
    assert cats == sorted(set(cats))


def test_default_info_matches_catalog():
    assert lc.default_info(_SAMPLE_CAT) == lainnya_catalog.get_category_info(_SAMPLE_CAT)


def test_load_info_falls_back_to_default(db):
    # belum ada baris DB -> default statis
    assert lc.load_info(_SAMPLE_CAT) == lc.default_info(_SAMPLE_CAT)


def test_load_info_unknown_category_empty(db):
    assert lc.load_info("KATEGORI TIDAK ADA 123") == {"description": "", "terms": ""}


def test_save_and_load_info(db):
    lc.save_info("TEST CAT", description="Deskripsi baru", terms="S&K baru")
    info = lc.load_info("TEST CAT")
    assert info["description"] == "Deskripsi baru"
    assert info["terms"] == "S&K baru"


def test_save_appears_in_list(db):
    lc.save_info("KATEGORI UNIK XYZ", description="d", terms="t")
    assert "KATEGORI UNIK XYZ" in lc.list_categories()


def test_save_none_becomes_empty(db):
    lc.save_info("CAT KOSONG", description="ada", terms=None)
    info = lc.load_info("CAT KOSONG")
    assert info["description"] == "ada"
    assert info["terms"] == ""


def test_reset_restores_default(db):
    lc.save_info(_SAMPLE_CAT, description="ubahan", terms="ubahan terms")
    assert lc.load_info(_SAMPLE_CAT)["description"] == "ubahan"
    out = lc.reset_info(_SAMPLE_CAT)
    # setelah reset -> kembali ke default statis
    assert out == lc.default_info(_SAMPLE_CAT)
    assert lc.load_info(_SAMPLE_CAT) == lc.default_info(_SAMPLE_CAT)


def test_overwrite_existing(db):
    lc.save_info("CAT OW", description="v1", terms="t1")
    lc.save_info("CAT OW", description="v2", terms="t2")
    info = lc.load_info("CAT OW")
    assert info["description"] == "v2" and info["terms"] == "t2"
