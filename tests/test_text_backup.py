"""Unit test backup/restore teks bot (utils/text_backup.py)."""
from utils import text_backup as tb
from utils import afk as afklib
from utils import store_status as sslib
from utils import welcome as wl
from utils import lainnya_category as lc
from cogs import lainnya_catalog


def test_collect_keys_covers_modules():
    keys = tb.collect_keys()
    assert isinstance(keys, set) and len(keys) > 30
    # contoh kunci dari beberapa editor berbeda
    assert afklib.AFK_SPECS["set"]["key"] in keys
    assert sslib.OPEN_LABEL_KEY in keys and sslib.CLOSE_LABEL_KEY in keys
    assert wl.MSG_SPECS["welcome"]["title_key"] in keys
    for k in wl.DM_KEYS:
        assert k in keys


def test_export_empty_when_no_customization(db):
    data = tb.export_data()
    assert data["version"] == tb.BACKUP_VERSION
    assert data["bot_state"] == {}
    assert data["lainnya_category"] == []


def test_export_only_customized(db):
    afklib.save_text("set", text="{member} AFK custom")
    data = tb.export_data()
    assert data["bot_state"].get(afklib.AFK_SPECS["set"]["key"]) == "{member} AFK custom"
    # kunci lain yang belum diubah tidak ikut
    assert afklib.AFK_SPECS["back"]["key"] not in data["bot_state"]


def test_import_applies_known_keys(db):
    payload = {
        "bot_state": {
            sslib.OPEN_LABEL_KEY: "BUKA YA",
            afklib.AFK_SPECS["set"]["key"] : "{member} afk",
        },
    }
    res = tb.import_data(payload)
    assert res["applied"] == 2
    assert sslib.get_open_label() == "BUKA YA"
    assert afklib.load_text("set") == "{member} afk"


def test_import_skips_unknown_keys(db):
    res = tb.import_data({"bot_state": {"some_random_key_999": "x"}})
    assert res["applied"] == 0 and res["skipped"] == 1


def test_import_string_payload(db):
    import json
    raw = json.dumps({"bot_state": {sslib.CLOSE_LABEL_KEY: "TUTUP YA"}})
    res = tb.import_data(raw)
    assert res["applied"] == 1
    assert sslib.get_close_label() == "TUTUP YA"


def test_import_invalid_raises(db):
    import pytest
    with pytest.raises(ValueError):
        tb.import_data("{bukan json")
    with pytest.raises(ValueError):
        tb.import_data(123)


def test_roundtrip_export_import(db):
    afklib.save_text("set", text="custom set")
    sslib.set_open_label("OPEN!")
    snapshot = tb.export_data()
    # reset semua
    afklib.save_text("set", text="")
    sslib.set_open_label("")
    assert afklib.load_text("set") == afklib.AFK_SPECS["set"]["default"]
    # pulihkan
    tb.import_data(snapshot)
    assert afklib.load_text("set") == "custom set"
    assert sslib.get_open_label() == "OPEN!"


def test_lainnya_category_export_import(db):
    cat = next(iter(lainnya_catalog.CATEGORY_INFO.keys()))
    lc.save_info(cat, description="desk custom", terms="snk custom")
    data = tb.export_data()
    assert any(c["category"] == cat for c in data["lainnya_category"])
    # reset & restore
    lc.reset_info(cat)
    res = tb.import_data(data)
    assert res["categories"] >= 1
    assert lc.load_info(cat)["description"] == "desk custom"
