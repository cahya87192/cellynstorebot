"""QRIS dinamis — sisipkan nominal otomatis ke payload QRIS statis.

QRIS memakai format EMVCo QR: rangkaian field TLV (Tag 2 digit, Length 2 digit,
Value sepanjang Length). Untuk mengubah QRIS *statis* (nominal diketik manual oleh
pembeli) menjadi *dinamis* (nominal sudah tertanam, aplikasi e-wallet pembeli
langsung terisi):

  1. Set tag 01 (Point of Initiation) = "12" (dinamis; "11" = statis).
  2. Sisipkan tag 54 (Transaction Amount) berisi nominal.
  3. Hitung ulang CRC tag 63 (CRC16/CCITT-FALSE) atas SELURUH payload termasuk
     "6304".

Logika EMV/CRC murni (tanpa DB/Flask) supaya gampang diuji. Helper load/save
payload pakai bot_state (best-effort), dipakai panel admin & cog pembayaran.
"""

STATE_KEY = "qris_payload"


def crc16(data: str) -> str:
    """CRC16/CCITT-FALSE (poly 0x1021, init 0xFFFF) -> 4 hex uppercase.

    Nilai uji standar: crc16("123456789") == "29B1".
    """
    crc = 0xFFFF
    for byte in data.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return format(crc, "04X")


def parse_tlv(payload: str):
    """Pecah payload jadi list [(tag, value), ...] di level atas.

    Raise ValueError bila struktur rusak (panjang tak cocok).
    """
    if not payload or not isinstance(payload, str):
        raise ValueError("payload kosong")
    out = []
    i, n = 0, len(payload)
    while i < n:
        if i + 4 > n:
            raise ValueError("TLV terpotong di header")
        tag = payload[i:i + 2]
        length_str = payload[i + 2:i + 4]
        if not length_str.isdigit():
            raise ValueError("length bukan angka")
        length = int(length_str)
        start = i + 4
        end = start + length
        if end > n:
            raise ValueError("value melebihi panjang payload")
        out.append((tag, payload[start:end]))
        i = end
    return out


def _emit(tlvs) -> str:
    parts = []
    for tag, val in tlvs:
        parts.append(f"{tag}{len(val):02d}{val}")
    return "".join(parts)


def is_valid(payload: str) -> bool:
    """True bila payload QRIS terstruktur benar & CRC-nya cocok."""
    if not payload or not isinstance(payload, str) or len(payload) < 8:
        return False
    try:
        tlvs = parse_tlv(payload)
    except ValueError:
        return False
    if not tlvs or tlvs[-1][0] != "63":
        return False
    body = payload[:-4]   # termasuk "6304"
    given = payload[-4:]
    return crc16(body).upper() == given.upper()


def looks_like_qris(payload: str) -> bool:
    """Heuristik ringan untuk validasi input admin (diawali tag 00 len 02)."""
    return bool(payload) and isinstance(payload, str) and payload.strip().startswith("0002")


def set_amount(payload: str, amount) -> str:
    """Kembalikan payload QRIS *dinamis* dengan `amount` (Rupiah) tertanam.

    - tag 01 -> "12" (dinamis)
    - tag 54 -> nominal (mengganti bila sudah ada), ditaruh setelah tag 53
      (mata uang) / sebelum tag 58 (negara) agar urutan EMV tetap wajar.
    - CRC (tag 63) dihitung ulang.

    Raise ValueError bila payload tidak valid atau amount <= 0.
    """
    amt = int(amount)
    if amt <= 0:
        raise ValueError("amount harus > 0")
    tlvs = parse_tlv(payload)
    # buang CRC & amount lama, set point-of-initiation jadi dinamis
    tlvs = [(t, v) for (t, v) in tlvs if t not in ("63", "54")]
    found01 = False
    for idx, (t, v) in enumerate(tlvs):
        if t == "01":
            tlvs[idx] = ("01", "12")
            found01 = True
            break
    if not found01:
        tlvs.insert(1 if tlvs else 0, ("01", "12"))

    amount_tlv = ("54", str(amt))
    # cari posisi sisip: setelah 53, kalau tidak ada sebelum 58/59/60/61/62
    insert_at = None
    for idx, (t, _v) in enumerate(tlvs):
        if t == "53":
            insert_at = idx + 1
            break
    if insert_at is None:
        for idx, (t, _v) in enumerate(tlvs):
            if t in ("58", "59", "60", "61", "62"):
                insert_at = idx
                break
    if insert_at is None:
        insert_at = len(tlvs)
    tlvs.insert(insert_at, amount_tlv)

    body = _emit(tlvs) + "6304"
    return body + crc16(body)


def qr_image_url(payload: str, size: int = 320) -> str:
    """URL gambar QR dari payload (pakai layanan render QR publik goqr.me)."""
    from urllib.parse import quote
    s = int(size)
    return (f"https://api.qrserver.com/v1/create-qr-code/"
            f"?size={s}x{s}&qzone=2&data={quote(payload, safe='')}")


# ── Penyimpanan payload (bot_state) — best-effort ─────────────────────────────

def load_payload():
    """Ambil payload QRIS statis tersimpan, atau None."""
    try:
        from utils.db import get_conn
        conn = get_conn()
        row = conn.execute(
            "SELECT value FROM bot_state WHERE key=?", (STATE_KEY,)
        ).fetchone()
        conn.close()
        if row and row["value"]:
            return row["value"]
    except Exception:
        pass
    return None


def save_payload(payload: str) -> bool:
    """Simpan payload QRIS (best-effort). Return True bila tersimpan."""
    try:
        from utils.db import get_conn
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
            (STATE_KEY, payload),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def clear_payload() -> bool:
    try:
        from utils.db import get_conn
        conn = get_conn()
        conn.execute("DELETE FROM bot_state WHERE key=?", (STATE_KEY,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def dynamic_image_url(amount, size: int = 320):
    """Gabungan praktis: ambil payload tersimpan -> QR dinamis untuk `amount`.

    Return URL gambar QR dinamis, atau None bila payload belum diset / invalid.
    """
    payload = load_payload()
    if not payload:
        return None
    try:
        return qr_image_url(set_amount(payload, amount), size=size)
    except Exception:
        return None
