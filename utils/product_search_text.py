"""Logika murni teks balasan pencarian produk (cogs/product_search.py).

Cog `cogs/product_search.py` membalas member di channel pencarian dengan embed
hasil / saran. Modul ini membuat PROSA pembungkusnya (judul, footer, placeholder
dropdown, pesan error) editable dari panel admin TANPA edit kode. Daftar produk &
harga tetap dibangun cog.

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store} -> nama toko (STORE_NAME)
  {query} -> kata kunci pencarian member (judul hasil)

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_RESULTS_TITLE = "\u2726  Hasil pencarian \u201c{query}\u201d"
DEFAULT_RESULTS_FOOTER = (
    "\u2727 {store} \u00b7 pilih produk di bawah untuk buka tiket / lihat katalog"
)
DEFAULT_SUGGEST_TITLE = "\u2726  Belum ketemu yang persis\u2026"
DEFAULT_SUGGEST_INTRO = "Mungkin maksud kamu:"
DEFAULT_SUGGEST_FOOTER = "\u2727 Coba ketik nama produk yang lebih spesifik"
DEFAULT_SELECT_PLACEHOLDER = "Pilih produk untuk buka tiket\u2026"
DEFAULT_TICKET_ERROR = "Maaf, gagal membuka tiket. Coba lewat katalog ya."

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
PRODUCT_SEARCH_SPECS = {
    "results_title": {
        "label": "Hasil pencarian \u2014 judul",
        "key": "psearch_results_title",
        "default": DEFAULT_RESULTS_TITLE,
        "placeholders": ("{query}",),
    },
    "results_footer": {
        "label": "Hasil pencarian \u2014 footer",
        "key": "psearch_results_footer",
        "default": DEFAULT_RESULTS_FOOTER,
        "placeholders": ("{store}",),
    },
    "suggest_title": {
        "label": "Saran (tidak ketemu) \u2014 judul",
        "key": "psearch_suggest_title",
        "default": DEFAULT_SUGGEST_TITLE,
        "placeholders": (),
    },
    "suggest_intro": {
        "label": "Saran (tidak ketemu) \u2014 kalimat pembuka",
        "key": "psearch_suggest_intro",
        "default": DEFAULT_SUGGEST_INTRO,
        "placeholders": (),
    },
    "suggest_footer": {
        "label": "Saran (tidak ketemu) \u2014 footer",
        "key": "psearch_suggest_footer",
        "default": DEFAULT_SUGGEST_FOOTER,
        "placeholders": (),
    },
    "select_placeholder": {
        "label": "Dropdown buka tiket \u2014 placeholder",
        "key": "psearch_select_placeholder",
        "default": DEFAULT_SELECT_PLACEHOLDER,
        "placeholders": (),
    },
    "ticket_error": {
        "label": "Pesan gagal buka tiket",
        "key": "psearch_ticket_error",
        "default": DEFAULT_TICKET_ERROR,
        "placeholders": (),
    },
}


def render_template(text, **values):
    """Substitusi placeholder secara aman (str.replace, bukan str.format)."""
    out = text if text is not None else ""
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def load_text(kind):
    """Ambil teks untuk `kind` (PRODUCT_SEARCH_SPECS) dari DB; fallback default."""
    spec = PRODUCT_SEARCH_SPECS[kind]
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
    spec = PRODUCT_SEARCH_SPECS[kind]
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
