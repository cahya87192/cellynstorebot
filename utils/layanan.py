"""Label layanan terpusat (satu sumber kebenaran).

Memetakan kode `layanan` pada transaction_log menjadi nama ramah-tampilan,
dipakai konsisten oleh customer insight, sistem review, dan laporan harian.
Kode `layanan` bisa mengandung sub-grup setelah ':' (mis. 'lainnya:editing'
atau 'lainnya:custom').
"""

LAYANAN_LABEL = {
    "robux": "Robux",
    "vilog": "Robux Via Login",
    "gp": "Robux Gamepass",
    "gp_topup": "Robux Gamepass",
    "ml": "Mobile Legends",
    "ff": "Free Fire",
    "jualbeli": "Jual Beli",
    "midman": "Middleman",
    "lainnya": "Layanan Lainnya",
    "cloudphone": "Cloud Phone",
    "nitro": "Discord Nitro",
}


def pretty_layanan(layanan, *, default: str = "Order") -> str:
    """Ubah kode layanan -> nama ramah-tampilan.

    - None/kosong -> `default`.
    - Sub-grup setelah ':' ikut ditampilkan
      (mis. 'lainnya:editing' -> 'Layanan Lainnya · Editing',
      'lainnya:custom' -> 'Layanan Lainnya · Custom').
    """
    if not layanan:
        return default
    base = layanan.split(":", 1)[0]
    label = LAYANAN_LABEL.get(base, base.replace("_", " ").title())
    if ":" in layanan:
        sub = layanan.split(":", 1)[1]
        if sub == "custom":
            label += " · Custom"
        elif sub:
            label += f" · {sub.title()}"
    return label
