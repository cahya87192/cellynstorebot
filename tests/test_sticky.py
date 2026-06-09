"""Unit test logika murni sticky message (utils/sticky.py).

Fokus: keputusan debounce (should_restick) & (de)serialisasi payload.
Bagian Discord (cogs/sticky.py) tidak diuji di sini.
"""
from utils import sticky as s


def test_should_restick_needs_min_messages():
    # Belum cukup pesan -> jangan re-stick walau cooldown lewat.
    assert s.should_restick(0, 0.0, 1000.0, min_messages=3, cooldown=20) is False
    assert s.should_restick(2, 0.0, 1000.0, min_messages=3, cooldown=20) is False
    # Cukup pesan + cooldown lewat -> re-stick.
    assert s.should_restick(3, 0.0, 1000.0, min_messages=3, cooldown=20) is True


def test_should_restick_respects_cooldown():
    # Cukup pesan tapi masih dalam cooldown -> jangan.
    assert s.should_restick(5, 1000.0, 1010.0, min_messages=3, cooldown=20) is False
    # Setelah cooldown lewat -> boleh.
    assert s.should_restick(5, 1000.0, 1021.0, min_messages=3, cooldown=20) is True


def test_should_restick_last_ts_none_means_never():
    # last_ts None dianggap 0 -> butuh now_ts >= cooldown agar lolos.
    assert s.should_restick(3, None, 25.0, min_messages=3, cooldown=20) is True
    # now_ts masih < cooldown -> belum boleh.
    assert s.should_restick(3, None, 5.0, min_messages=3, cooldown=20) is False


def test_payload_round_trip_text_only():
    raw = s.serialize_payload(content="Halo sticky", embed_dict=None)
    content, embed = s.deserialize_payload(raw)
    assert content == "Halo sticky"
    assert embed is None


def test_payload_round_trip_with_embed():
    embed = {"title": "Aturan", "description": "Baca dulu ya", "color": 5793266}
    raw = s.serialize_payload(content=None, embed_dict=embed)
    content, got = s.deserialize_payload(raw)
    assert content is None
    assert got["title"] == "Aturan"
    assert got["color"] == 5793266


def test_deserialize_bad_input():
    assert s.deserialize_payload("") == (None, None)
    assert s.deserialize_payload("not-json") == (None, None)
    assert s.deserialize_payload("[1,2,3]") == (None, None)


def test_has_payload():
    assert s.has_payload("teks", None) is True
    assert s.has_payload(None, {"title": "x"}) is True
    assert s.has_payload("   ", None) is False
    assert s.has_payload(None, None) is False
    assert s.has_payload("", {}) is False



# ── Kelola map sticky (helper admin panel) ──────────────────────────────────────

def test_parse_sticky_map_ok_and_tolerant():
    raw = s.serialize_sticky_map({123: {"content": "hi", "embed": None, "message_id": 9}})
    m = s.parse_sticky_map(raw)
    assert m == {123: {"content": "hi", "embed": None, "message_id": 9}}
    # toleran: input rusak / bukan dict -> {}
    assert s.parse_sticky_map("") == {}
    assert s.parse_sticky_map("not-json") == {}
    assert s.parse_sticky_map("[1,2]") == {}
    # key non-int & value non-dict diabaikan
    assert s.parse_sticky_map('{"abc": {"content":"x"}, "5": 7}') == {}


def test_color_hex_round_trip():
    assert s.parse_color_hex("#5865F2") == 0x5865F2
    assert s.parse_color_hex("5865F2") == 0x5865F2
    assert s.parse_color_hex(None) == s.COLOR_DEFAULT
    assert s.parse_color_hex("zzz") == s.COLOR_DEFAULT
    assert s.color_to_hex(0x5865F2) == "#5865F2"
    assert s.color_to_hex("bad") == s.color_to_hex(s.COLOR_DEFAULT)


def test_make_entry_text_and_embed():
    entry, ok = s.make_entry("Halo", message_id=10)
    assert ok and entry["content"] == "Halo" and entry["embed"] is None
    assert entry["message_id"] == 10

    entry, ok = s.make_entry(None, title="Judul", description="Isi",
                             color_hex="#FF0000", footer="Toko")
    assert ok and entry["content"] is None
    assert entry["embed"]["title"] == "Judul"
    assert entry["embed"]["color"] == 0xFF0000
    assert entry["embed"]["footer"] == {"text": "Toko"}

    # tanpa payload apa pun -> ok=False
    entry, ok = s.make_entry("   ", title="", description="")
    assert ok is False and entry is None


def test_entry_fields_round_trip():
    entry, _ = s.make_entry(None, title="J", description="D", color_hex="#00FF00",
                            footer="Toko", message_id=42)
    f = s.entry_fields(entry)
    assert f["title"] == "J" and f["description"] == "D"
    assert f["color_hex"] == "#00FF00" and f["message_id"] == 42
    assert f["has_embed"] is True
    # entry teks biasa
    f2 = s.entry_fields({"content": "teks", "embed": None})
    assert f2["content"] == "teks" and f2["has_embed"] is False


def test_entry_summary_truncates():
    assert s.entry_summary({"content": "halo dunia"}) == "halo dunia"
    long = {"content": "x" * 200}
    out = s.entry_summary(long, limit=20)
    assert len(out) == 20 and out.endswith("…")
    # fallback ke judul embed bila tak ada teks
    assert s.entry_summary({"content": "", "embed": {"title": "Aturan"}}) == "Aturan"


def test_update_entry_content_preserves_message_id():
    m = {7: {"content": "lama", "embed": None, "message_id": 99}}
    m, ok = s.update_entry_content(m, 7, content="baru")
    assert ok and m[7]["content"] == "baru" and m[7]["message_id"] == 99
    # channel tak ada -> ok False, map tak berubah
    m, ok = s.update_entry_content(m, 12345, content="x")
    assert ok is False and 12345 not in m
    # payload kosong -> ok False
    m, ok = s.update_entry_content(m, 7, content="   ")
    assert ok is False and m[7]["content"] == "baru"


def test_remove_entry():
    m = {1: {"content": "a"}, 2: {"content": "b"}}
    m, removed = s.remove_entry(m, "1")
    assert removed == {"content": "a"} and 1 not in m and 2 in m
    m, removed = s.remove_entry(m, 999)
    assert removed is None
