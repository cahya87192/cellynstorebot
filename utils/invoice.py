"""Helper struk/invoice digital — logika murni (tanpa discord / PIL).

Berisi format nomor invoice, format rupiah, dan format tanggal. Dipisah dari
cog supaya bisa diuji tanpa Discord.
"""

import datetime


def rupiah(n) -> str:
    """Format angka ke rupiah, mis. 1250000 -> 'Rp 1.250.000'."""
    try:
        return "Rp " + f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp 0"


def _coerce_dt(when) -> datetime.datetime:
    """Terima datetime / ISO string / None -> datetime (default: sekarang UTC)."""
    if isinstance(when, datetime.datetime):
        return when
    if isinstance(when, str) and when.strip():
        text = when.strip().replace("Z", "+00:00")
        try:
            return datetime.datetime.fromisoformat(text)
        except ValueError:
            # Coba ambil bagian tanggal saja (YYYY-MM-DD ...).
            try:
                return datetime.datetime.fromisoformat(text[:10])
            except ValueError:
                pass
    return datetime.datetime.now(datetime.timezone.utc)


def invoice_number(tx_id, when=None) -> str:
    """Nomor invoice deterministik dari id transaksi + tanggal.

    Contoh: invoice_number(42, '2026-06-08...') -> 'INV-20260608-00042'.
    """
    dt = _coerce_dt(when)
    try:
        n = int(tx_id)
    except (TypeError, ValueError):
        n = 0
    return f"INV-{dt.strftime('%Y%m%d')}-{n:05d}"


def format_date(when=None) -> str:
    """Tanggal ringkas untuk struk, mis. '08/06/2026 14:30'."""
    dt = _coerce_dt(when)
    return dt.strftime("%d/%m/%Y %H:%M")
