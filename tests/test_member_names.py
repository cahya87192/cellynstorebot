"""Unit test cache nama member (utils/member_names.py)."""
from utils import member_names as mn


def test_empty_initially(db):
    assert mn.count() == 0
    assert mn.get_name(123) is None
    assert mn.name_map([123, 456]) == {}


def test_set_and_get(db):
    assert mn.set_name(123, "Andi") is True
    assert mn.get_name(123) == "Andi"
    assert mn.get_name("123") == "Andi"  # id sebagai string juga cocok
    assert mn.count() == 1


def test_set_ignores_empty(db):
    assert mn.set_name(None, "x") is False
    assert mn.set_name(1, "") is False
    assert mn.count() == 0


def test_upsert_overwrites(db):
    mn.set_name(1, "Lama")
    mn.set_name(1, "Baru")
    assert mn.get_name(1) == "Baru"
    assert mn.count() == 1


def test_bulk_set_and_name_map(db):
    n = mn.bulk_set({1: "A", 2: "B", 3: "C"})
    assert n == 3
    m = mn.name_map([1, 2, 99])
    assert m == {"1": "A", "2": "B"}  # 99 belum ada -> tidak muncul


def test_bulk_set_skips_empty(db):
    n = mn.bulk_set({1: "A", 2: "", None: "X"})
    assert n == 1
    assert mn.get_name(1) == "A"


def test_display_fallback(db):
    assert mn.display(123) == "123"            # belum ada -> id
    assert mn.display(123, default="-") == "-"
    mn.set_name(123, "Andi")
    assert mn.display(123) == "Andi"


def test_name_map_mixed_types(db):
    mn.bulk_set({111: "Satu"})
    m = mn.name_map([111, "111", None, ""])
    assert m == {"111": "Satu"}
