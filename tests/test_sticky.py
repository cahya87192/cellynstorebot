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
