"""Logika murni teks DM pengingat perpanjangan langganan (cogs/sub_followup.py).

Cog `cogs/sub_followup.py` mengirim DM personal ke member beberapa hari sebelum
langganannya habis. Modul ini membuat teks DM tersebut editable dari panel admin
TANPA edit kode. Bila belum dikustomisasi, dipakai teks default (sama persis
dengan perilaku sebelumnya).

Placeholder yang didukung (diganti otomatis saat dikirim):
  {store} -> nama toko (STORE_NAME)
  {item}  -> nama produk langganan
  {waktu} -> kapan langganan habis (mis. "hari ini" / "besok" / "dalam 3 hari lagi")

Modul ini self-contained dan hanya menyentuh SQLite (bot_state) -> gampang diuji,
tanpa butuh discord.
"""

# ── Default teks (sama persis dgn versi hardcoded sebelumnya) ────────────────────
DEFAULT_TITLE = "🔔 Langgananmu Sebentar Lagi Habis"
DEFAULT_DESC = (
    "Halo! Langgananmu di **{store}** akan berakhir **{waktu}**.\n\n"
    "**Produk:** {item}\n\n"
    "Mau perpanjang biar nggak putus di tengah jalan? Tinggal klik tombol "
    "di bawah ya. Makasih sudah jadi pelanggan setia kami 🤍"
)
DEFAULT_FOOTER = "{store} · pengingat perpanjangan"
DEFAULT_BUTTON = "🛒 Perpanjang / Order Lagi"

# Registry tiap jenis teks: kunci DB + default + placeholder relevan + label.
SUB_FOLLOWUP_SPECS = {
    "title": {
        "label": "DM pengingat — judul",
        "key": "sub_followup_title",
        "default": DEFAULT_TITLE,
        "placeholders": (),
    },
    "description": {
        "label": "DM pengingat — isi pesan",
        "key": "sub_followup_desc",
        "default": DEFAULT_DESC,
        "placeholders": ("{store}", "{item}", "{waktu}"),
    },
    "footer": {
        "label": "DM pengingat — footer",
        "key": "sub_followup_footer",
        "default": DEFAULT_FOOTER,
        "placeholders": ("{store}",),
    },
    "button_label": {
        "label": "DM pengingat — label tombol",
        "key": "sub_followup_button",
        "default": DEFAULT_BUTTON,
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
    """Ambil teks untuk `kind` (SUB_FOLLOWUP_SPECS) dari DB; fallback default."""
    spec = SUB_FOLLOWUP_SPECS[kind]
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
    spec = SUB_FOLLOWUP_SPECS[kind]
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
