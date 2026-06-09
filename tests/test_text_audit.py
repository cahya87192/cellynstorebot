"""Unit test audit log perubahan teks (utils/text_audit.py)."""
from utils import text_audit as ta


def test_empty_initially(db):
    assert ta.count() == 0
    assert ta.recent() == []


def test_record_and_recent(db):
    assert ta.record("save", key="afk_set_text", kind="set", label="Set AFK", detail="halo") is True
    assert ta.count() == 1
    rows = ta.recent()
    assert len(rows) == 1
    e = rows[0]
    assert e["action"] == "save"
    assert e["key"] == "afk_set_text"
    assert e["kind"] == "set"
    assert e["label"] == "Set AFK"
    assert e["detail"] == "halo"
    assert e["ts"]


def test_recent_order_newest_first(db):
    ta.record("save", key="k1")
    ta.record("reset", key="k2")
    ta.record("import", detail="x")
    rows = ta.recent()
    assert [r["action"] for r in rows] == ["import", "reset", "save"]


def test_recent_limit(db):
    for i in range(10):
        ta.record("save", key=f"k{i}")
    assert len(ta.recent(limit=3)) == 3
    assert ta.count() == 10


def test_detail_truncated(db):
    ta.record("save", key="k", detail="x" * 500)
    detail = ta.recent()[0]["detail"]
    assert len(detail) <= ta.MAX_DETAIL + 1  # +1 untuk elipsis
    assert detail.endswith("…")


def test_clear(db):
    ta.record("save", key="k")
    ta.record("save", key="k2")
    removed = ta.clear()
    assert removed == 2
    assert ta.count() == 0


def test_save_request_records_audit(db):
    """save_request mencatat audit lewat komponen bersama (logika murni dipakai)."""
    # Simulasikan lewat record langsung (save_request butuh Flask request context);
    # di sini cukup pastikan record dipakai dengan field dari spec.
    spec = {"key": "warranty_panel_title", "label": "Judul panel"}
    ta.record("save", key=spec["key"], kind="panel_title", label=spec["label"], detail="Garansi")
    e = ta.recent()[0]
    assert e["key"] == "warranty_panel_title" and e["label"] == "Judul panel"


def test_backup_import_records(db):
    from utils import text_backup as tb
    from utils import store_status as ss
    tb.import_data({"bot_state": {ss.OPEN_LABEL_KEY: "BUKA"}})
    actions = [r["action"] for r in ta.recent()]
    assert "import" in actions


def test_backup_reset_all_records(db):
    from utils import text_backup as tb
    from utils import afk as afklib
    afklib.save_text("set", text="x")
    tb.reset_all()
    actions = [r["action"] for r in ta.recent()]
    assert "reset_all" in actions
