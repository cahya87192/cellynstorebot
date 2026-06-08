"""Persistensi badge achievement yang SUDAH diumumkan per member (anti-dobel).

Disimpan di tabel `bot_state` dengan key `badges_announced_<user_id>`, berisi
nama badge yang dipisah '||'. Dipakai sistem notifikasi badge (cogs/reviews.py)
supaya tiap badge hanya diumumkan sekali walau pengecekan terjadi berkali-kali.

Hanya bergantung pada utils.db -> bisa diuji dengan fixture `db`.
"""

from utils.db import get_conn

_SEP = "||"


def _key(user_id) -> str:
    return f"badges_announced_{int(user_id)}"


def get_announced(user_id) -> set:
    """Set nama badge yang sudah pernah diumumkan ke member (kosong bila belum)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key=?", (_key(user_id),))
    row = c.fetchone()
    conn.close()
    if not row or not row["value"]:
        return set()
    return {n for n in row["value"].split(_SEP) if n}


def mark_announced(user_id, names) -> None:
    """Tandai badge `names` sudah diumumkan (digabung dengan yang sudah ada)."""
    names = [str(n) for n in (names or []) if str(n)]
    if not names:
        return
    current = get_announced(user_id)
    current.update(names)
    value = _SEP.join(sorted(current))
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?, ?)",
        (_key(user_id), value),
    )
    conn.commit()
    conn.close()
