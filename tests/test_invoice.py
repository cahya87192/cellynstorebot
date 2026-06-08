"""Test helper struk/invoice digital (utils/invoice.py). Logika murni."""
import datetime

from utils import invoice as inv


def test_rupiah():
    assert inv.rupiah(1250000) == "Rp 1.250.000"
    assert inv.rupiah(0) == "Rp 0"
    assert inv.rupiah(1000) == "Rp 1.000"
    # input tidak valid aman
    assert inv.rupiah(None) == "Rp 0"
    assert inv.rupiah("abc") == "Rp 0"


def test_invoice_number_from_datetime():
    when = datetime.datetime(2026, 6, 8, 14, 30, tzinfo=datetime.timezone.utc)
    assert inv.invoice_number(42, when) == "INV-20260608-00042"


def test_invoice_number_from_iso_string():
    assert inv.invoice_number(7, "2026-01-09T08:00:00+00:00") == "INV-20260109-00007"
    # string dengan Z
    assert inv.invoice_number(123, "2026-12-31T23:59:00Z") == "INV-20261231-00123"
    # tanggal saja
    assert inv.invoice_number(5, "2026-03-04") == "INV-20260304-00005"


def test_invoice_number_padding_large():
    assert inv.invoice_number(123456, "2026-06-08") == "INV-20260608-123456"


def test_invoice_number_invalid_tx_id():
    assert inv.invoice_number(None, "2026-06-08") == "INV-20260608-00000"
    assert inv.invoice_number("x", "2026-06-08") == "INV-20260608-00000"


def test_format_date():
    when = datetime.datetime(2026, 6, 8, 14, 30, tzinfo=datetime.timezone.utc)
    assert inv.format_date(when) == "08/06/2026 14:30"
    assert inv.format_date("2026-01-09T08:05:00") == "09/01/2026 08:05"


def test_format_date_none_is_now():
    # tidak crash, mengembalikan string tanggal valid
    out = inv.format_date(None)
    assert isinstance(out, str) and len(out) >= 10
