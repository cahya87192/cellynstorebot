"""Test cek kesiapan self-host (utils/selfhost_check.py) — logika murni."""
from utils import selfhost_check as shc


def _all_required_env():
    return {name: "123" for name, _ in shc.REQUIRED_VARS}


def test_ready_when_all_required_set():
    rep = shc.check_env(_all_required_env())
    assert rep["ready"] is True
    assert rep["missing_required"] == []
    assert rep["required_set"] == rep["required_total"] == len(shc.REQUIRED_VARS)


def test_not_ready_lists_missing():
    env = _all_required_env()
    del env["TOKEN"]
    del env["GUILD_ID"]
    rep = shc.check_env(env)
    assert rep["ready"] is False
    assert set(rep["missing_required"]) == {"TOKEN", "GUILD_ID"}
    assert rep["required_set"] == rep["required_total"] - 2


def test_blank_and_whitespace_counts_as_unset():
    env = _all_required_env()
    env["TOKEN"] = ""
    env["GUILD_ID"] = "   "
    rep = shc.check_env(env)
    assert "TOKEN" in rep["missing_required"]
    assert "GUILD_ID" in rep["missing_required"]


def test_recommended_tracked_separately():
    rep = shc.check_env(_all_required_env())
    # Tidak ada recommended diisi -> ready tetap True (recommended opsional).
    assert rep["ready"] is True
    assert rep["recommended_set"] == 0
    assert rep["recommended_total"] == len(shc.RECOMMENDED_VARS)
    # tiap entri recommended punya default untuk ditampilkan.
    assert all("default" in r for r in rep["recommended"])


def test_bad_input_safe():
    rep = shc.check_env(None)
    assert rep["ready"] is False
    assert rep["missing_required"] == [n for n, _ in shc.REQUIRED_VARS]


def test_required_includes_token_and_core_ids():
    names = {n for n, _ in shc.REQUIRED_VARS}
    assert "TOKEN" in names
    assert {"GUILD_ID", "ADMIN_ROLE_ID", "TICKET_CATEGORY_ID"} <= names
