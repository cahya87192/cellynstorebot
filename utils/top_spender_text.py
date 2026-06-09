"""Logika murni teks papan Top Spender (cogs/top_spender.py).

Cog `cogs/top_spender.py` menampilkan leaderboard pelanggan dengan total belanja
terbanyak bulan ini. Modul ini membuat PROSA papan (judul, deskripsi, footer,
benefit, state kosong) editable dari panel admin TANPA edit kode. Daftar peringkat
& nominal tetap dihitung cog.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store} -> nama toko (STORE_NAME)
  {month} -> nama bulan papan (mis. "Juni 2026")

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_TITLE = "🏆 Top Spender — {month}"
DEFAULT_DESC = (
    "Apresiasi untuk pelanggan setia {store} 💛\n"
    "*(diperbarui otomatis tiap ada transaksi)*"
)
DEFAULT_EMPTY = "Belum ada data transaksi bulan ini."
DEFAULT_BENEFIT = (
    "👑 Role eksklusif Top Spender (khusus Top 10)\n"
    "⚡ Prioritas antrean — pesananmu didahulukan di semua layanan\n"
    "🤝 Diutamakan admin saat tiket sedang ramai"
)
DEFAULT_FOOTER = "{store} • Reset tiap awal bulan"

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
TOP_SPENDER_SPECS = {
    "title": {
        "label": "Papan Top Spender — judul",
        "key": "top_spender_title",
        "default": DEFAULT_TITLE,
        "placeholders": ("{month}",),
    },
    "description": {
        "label": "Papan Top Spender — deskripsi",
        "key": "top_spender_desc",
        "default": DEFAULT_DESC,
        "placeholders": ("{store}",),
    },
    "empty": {
        "label": "Papan Top Spender — saat belum ada data",
        "key": "top_spender_empty",
        "default": DEFAULT_EMPTY,
        "placeholders": (),
    },
    "benefit": {
        "label": "Papan Top Spender — benefit",
        "key": "top_spender_benefit",
        "default": DEFAULT_BENEFIT,
        "placeholders": (),
    },
    "footer": {
        "label": "Papan Top Spender — footer",
        "key": "top_spender_footer",
        "default": DEFAULT_FOOTER,
        "placeholders": ("{store}",),
    },
}


def render_template(text, **values):
    """Substitusi placeholder secara aman (str.replace, bukan str.format)."""
    out = text if text is not None else ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def load_text(kind):
    """Ambil teks untuk `kind` (TOP_SPENDER_SPECS) dari DB; fallback default."""
    spec = TOP_SPENDER_SPECS[kind]
    from utils.db import get_conn
    value = None
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM bot_state WHERE key=?", (spec["key"],)
        ).fetchone()
        value = row["value"] if row else None
    except Exception:
        pass
    conn.close()
    if not (value and value.strip()):
        value = spec["default"]
    return value


def save_text(kind, text=None):
    """Simpan teks untuk `kind`. None -> tak diubah; kosong -> reset default."""
    spec = TOP_SPENDER_SPECS[kind]
    if text is None:
        return
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    if text.strip() == "":
        c.execute("DELETE FROM bot_state WHERE key=?", (spec["key"],))
    else:
        c.execute(
            "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
            (spec["key"], text),
        )
    conn.commit()
    conn.close()


def render_text(kind, **values):
    """Teks `kind` dengan placeholder tersubstitusi."""
    return render_template(load_text(kind), **values)
