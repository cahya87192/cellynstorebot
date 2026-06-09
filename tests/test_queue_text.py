"""Unit test logika murni teks antrian customer (utils/queue_text.py).

Bagian Discord (cogs/queue.py) tidak diuji di sini; fokus pada substitusi
placeholder + simpan/muat teks (fallback default) lewat bot_state.
"""
from utils import queue_text as q


def test_specs_keys_and_defaults():
    assert set(q.QUEUE_SPECS) == {
        "public_info", "public_empty", "card_handling", "card_first", "card_waiting",
    }
    for spec in q.QUEUE_SPECS.values():
        assert spec["key"] and spec["default"]


def test_render_template_replaces_and_keeps_unknown():
    out = q.render_template("Posisi {position} dari {ahead} {x}", position=3, ahead=2)
    assert out == "Posisi 3 dari 2 {x}"
    assert q.render_template(None) == ""


def test_load_text_default_per_kind(db):
    for kind, spec in q.QUEUE_SPECS.items():
        assert q.load_text(kind) == spec["default"]


def test_save_and_load_text(db):
    q.save_text("public_info", text="Antrean real-time.")
    assert q.load_text("public_info") == "Antrean real-time."


def test_empty_resets_to_default(db):
    q.save_text("public_empty", text="custom")
    q.save_text("public_empty", text="")
    assert q.load_text("public_empty") == q.DEFAULT_PUBLIC_EMPTY


def test_save_isolated_per_kind(db):
    q.save_text("card_first", text="kamu terdepan!")
    assert q.load_text("card_first") == "kamu terdepan!"
    assert q.load_text("card_handling") == q.DEFAULT_CARD_HANDLING
    assert q.load_text("card_waiting") == q.DEFAULT_CARD_WAITING


def test_render_card_handling_admin(db):
    out = q.render_text("card_handling", admin="@Admin")
    assert "@Admin" in out and "{admin}" not in out


def test_render_card_waiting_substitution(db):
    out = q.render_text("card_waiting", position=4, ahead=3)
    assert "4" in out and "3" in out
    assert "{position}" not in out and "{ahead}" not in out


def test_render_card_waiting_custom(db):
    q.save_text("card_waiting", text="Posisi {position} ({ahead} di depan)")
    assert q.render_text("card_waiting", position=2, ahead=1) == "Posisi 2 (1 di depan)"
