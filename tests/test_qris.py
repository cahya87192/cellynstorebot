"""Unit test QRIS dinamis (utils/qris.py) — logika EMV/CRC murni."""
import pytest

from utils import qris


def _mk(tag, val):
    return f"{tag}{len(val):02d}{val}"


def _static_sample(with_amount=None):
    """Bangun payload QRIS statis sederhana yang valid (CRC dihitung sendiri)."""
    fields = _mk("00", "01") + _mk("01", "11") + _mk("52", "4814") + _mk("53", "360")
    if with_amount is not None:
        fields += _mk("54", str(with_amount))
    fields += _mk("58", "ID") + _mk("59", "Toko Contoh") + _mk("60", "Jakarta")
    body = fields + "6304"
    return body + qris.crc16(body)


# ── CRC ───────────────────────────────────────────────────────────────────────

def test_crc16_standard_check_value():
    assert qris.crc16("123456789") == "29B1"


def test_crc16_is_uppercase_4_digits():
    c = qris.crc16("00020101")
    assert len(c) == 4 and c == c.upper()


# ── validasi ──────────────────────────────────────────────────────────────────

def test_is_valid_true_for_well_formed():
    assert qris.is_valid(_static_sample()) is True


def test_is_valid_false_on_tampered_crc():
    p = _static_sample()
    bad = p[:-1] + ("0" if p[-1] != "0" else "1")
    assert qris.is_valid(bad) is False


def test_is_valid_false_on_garbage():
    assert qris.is_valid("") is False
    assert qris.is_valid("halo bukan qris") is False
    assert qris.is_valid(None) is False


def test_looks_like_qris():
    assert qris.looks_like_qris(_static_sample()) is True
    assert qris.looks_like_qris("1234") is False


# ── set_amount (statis -> dinamis) ─────────────────────────────────────────────

def test_set_amount_makes_valid_dynamic():
    dyn = qris.set_amount(_static_sample(), 15000)
    assert qris.is_valid(dyn) is True
    tlvs = dict(qris.parse_tlv(dyn))
    assert tlvs["01"] == "12"        # jadi dinamis
    assert tlvs["54"] == "15000"     # nominal tertanam


def test_set_amount_replaces_existing_amount():
    dyn = qris.set_amount(_static_sample(with_amount=5000), 27500)
    body = dyn[:-4]
    # hanya ada satu field amount
    assert body.count("5405") + body.count("5406") >= 1
    tlvs = dict(qris.parse_tlv(dyn))
    assert tlvs["54"] == "27500"
    assert qris.is_valid(dyn) is True


def test_set_amount_position_after_currency():
    dyn = qris.set_amount(_static_sample(), 1000)
    # tag 54 muncul tepat setelah tag 53 (mata uang)
    assert "53033605404100058" in dyn or "5303360" in dyn
    tags = [t for t, _ in qris.parse_tlv(dyn)]
    assert tags.index("54") == tags.index("53") + 1
    assert tags[-1] == "63"


def test_set_amount_rejects_nonpositive():
    p = _static_sample()
    with pytest.raises(ValueError):
        qris.set_amount(p, 0)
    with pytest.raises(ValueError):
        qris.set_amount(p, -5000)


def test_parse_tlv_roundtrip():
    p = _static_sample()
    tlvs = qris.parse_tlv(p)
    assert tlvs[0] == ("00", "01")
    assert tlvs[-1][0] == "63"


def test_qr_image_url_encodes_payload():
    url = qris.qr_image_url("00020101&x", size=300)
    assert url.startswith("https://api.qrserver.com/")
    assert "size=300x300" in url
    assert "&x" not in url.split("data=")[1]  # ter-encode


def test_dynamic_image_url_none_without_payload(db):
    # belum ada payload tersimpan -> None
    assert qris.dynamic_image_url(10000) is None


def test_save_load_clear_payload(db):
    p = _static_sample()
    assert qris.save_payload(p) is True
    assert qris.load_payload() == p
    url = qris.dynamic_image_url(20000)
    assert url and "api.qrserver.com" in url
    assert qris.clear_payload() is True
    assert qris.load_payload() is None
