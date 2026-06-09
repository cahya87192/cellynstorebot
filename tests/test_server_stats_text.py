"""Unit test logika murni format nama channel statistik (utils/server_stats_text.py)."""
from utils import server_stats_text as s


def test_specs_keys_and_defaults():
    assert set(s.SERVER_STATS_SPECS) == {"members_format"}
    for spec in s.SERVER_STATS_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = s.render_template("Members {count} {x}", count=10)
    assert out == "Members 10 {x}"
    assert s.render_template(None) == ""


def test_load_text_default(db):
    assert s.load_text("members_format") == s.DEFAULT_MEMBERS_FORMAT


def test_save_and_load_text(db):
    s.save_text("members_format", text="👥 {count} member")
    assert s.load_text("members_format") == "👥 {count} member"


def test_empty_resets_to_default(db):
    s.save_text("members_format", text="custom")
    s.save_text("members_format", text="")
    assert s.load_text("members_format") == s.DEFAULT_MEMBERS_FORMAT


def test_members_name_default(db):
    assert s.members_name(42) == "🌐 Members: 42"
    assert "{count}" not in s.members_name(42)


def test_members_name_custom(db):
    s.save_text("members_format", text="👥 Total: {count} orang")
    assert s.members_name(7) == "👥 Total: 7 orang"


def test_backup_registry_includes_server_stats():
    from utils import text_backup as tb
    assert s.SERVER_STATS_SPECS["members_format"]["key"] in tb.collect_keys()
