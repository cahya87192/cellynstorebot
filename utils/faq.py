"""Knowledge base FAQ (logika murni, tanpa discord/PIL).

Satu sumber data dipakai oleh dua fitur:
  1. FAQ embed terpajang (cogs/faq.py meng-render & auto-post ke channel FAQ).
  2. Auto-CS: mencocokkan pertanyaan member ke entri FAQ via kata kunci.

Konten disimpan sebagai JSON di tabel `bot_state` (key `faq_entries`) sehingga
bisa diedit lewat admin panel tanpa ubah kode. Teks memakai placeholder
`{store}` yang diganti STORE_NAME saat render (biar portabel antar-server).

Tiap entri: {id, q (pertanyaan/judul), a (jawaban), keywords: [..]}.
"""

import json
import re

from utils.db import get_conn

FAQ_KEY = "faq_entries"

# FAQ default. {store} diganti nama toko saat render. Bisa diedit via panel.
DEFAULT_FAQ = [
    {
        "id": "identitas",
        "q": "Apa itu {store}?",
        "a": ("{store} adalah **toko sekaligus komunitas** untuk gamer & member. "
              "Selain jual-beli kebutuhan gaming, kami tempat nongkrong, event, "
              "dan ngobrol bareng komunitas."),
        "keywords": ["apa itu", "tentang", "identitas", "toko apa", "store apa", "komunitas"],
    },
    {
        "id": "produk",
        "q": "Apa saja yang dijual?",
        "a": ("- 🪙 **Robux** — via Gamepass & via Login\n"
              "- 🎮 **Topup Game** — Mobile Legends, Free Fire, dll\n"
              "- 🎟️ **Gamepass Robux**\n"
              "- 🤝 **Middleman (Midman)** — jasa perantara transaksi antar member\n"
              "- 🛍️ **Jual Beli** — jual/beli item/akun dengan jasa perantara\n"
              "- ☁️ **Layanan Lainnya** — langganan (Spotify, Netflix, Nitro, Canva, "
              "dll) & custom order"),
        "keywords": ["jual apa", "produk", "barang", "menyediakan", "ada apa aja",
                     "katalog", "layanan", "robux", "topup", "diamond", "nitro",
                     "langganan", "gamepass"],
    },
    {
        "id": "cara_order",
        "q": "Cara order gimana?",
        "a": ("1. Buka channel katalog layanan yang kamu mau.\n"
              "2. Klik tombol/menu produk → isi form → tiket otomatis dibuat.\n"
              "3. Bayar sesuai instruksi di tiket, lalu kirim bukti.\n"
              "4. Admin memproses pesananmu. Pantau giliran di papan antrian."),
        "keywords": ["cara order", "cara beli", "cara pesan", "gimana order",
                     "gimana beli", "mau beli", "mau order", "checkout", "pesan"],
    },
    {
        "id": "pembayaran",
        "q": "Metode pembayaran apa saja?",
        "a": "Pembayaran via **QRIS, DANA, atau BCA** (sesuai yang tertera di tiketmu).",
        "keywords": ["bayar", "pembayaran", "metode", "qris", "dana", "bca",
                     "transfer", "payment"],
    },
    {
        "id": "garansi",
        "q": "Bagaimana soal garansi?",
        "a": ("Setiap transaksi sukses dapat garansi. **Wajib beri rating dalam "
              "24 jam** di channel rating agar garansi aktif. Klaim garansi lewat "
              "panel/tiket garansi."),
        "keywords": ["garansi", "warranty", "rating", "klaim", "rusak", "komplain"],
    },
    {
        "id": "antrian",
        "q": "Kenapa pesananku mengantri?",
        "a": ("Tiket diproses **berurutan** (yang paling lama menunggu didahulukan). "
              "Top Spender bulan ini diprioritaskan. Pantau giliranmu di papan "
              "antrian — pasti dilayani, mohon sabar ya."),
        "keywords": ["antri", "antre", "antrian", "lama", "ngantri", "giliran",
                     "kapan diproses", "nunggu", "menunggu"],
    },
    {
        "id": "top_spender",
        "q": "Apa untungnya jadi Top Spender?",
        "a": ("Top Spender (Top-N pembeli bulan berjalan) dapat: **role eksklusif**, "
              "**prioritas antrean** di semua layanan, dan **diutamakan admin** saat "
              "tiket ramai."),
        "keywords": ["top spender", "topspender", "untung", "benefit", "prioritas",
                     "vip", "royal"],
    },
    {
        "id": "rules",
        "q": "Aturan singkat member",
        "a": ("- Sopan, no spam, no toxic.\n"
              "- **Dilarang promosi/jualan tanpa izin admin**, termasuk mempromosikan "
              "barang yang sama dengan yang dijual {store}.\n"
              "- **Scam akan ditindak tegas** (ban permanen).\n"
              "- Ikuti instruksi admin di dalam tiket.\n"
              "Aturan lengkap ada di channel rules."),
        "keywords": ["rules", "aturan", "peraturan", "larangan", "boleh", "tidak boleh",
                     "scam", "promosi", "promote", "jualan"],
    },
    {
        "id": "saran",
        "q": "Mau kasih saran/masukan?",
        "a": ("Kami terbuka untuk saran! Pakai command **/saran** untuk kirim "
              "masukan/keluhan/ide langsung ke admin. Masukanmu membantu kami "
              "berkembang."),
        "keywords": ["saran", "masukan", "keluhan", "kritik", "feedback", "ide",
                     "request", "usul"],
    },
]


def default_faq():
    return json.loads(json.dumps(DEFAULT_FAQ))


def _valid_entry(e):
    return (isinstance(e, dict) and e.get("q") and e.get("a"))


def normalize_faq(raw):
    """Validasi & rapikan data FAQ (toleran input rusak -> default)."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = None
    if not isinstance(raw, list):
        return default_faq()
    out = []
    for i, e in enumerate(raw):
        if not _valid_entry(e):
            continue
        kw = e.get("keywords") or []
        if isinstance(kw, str):
            kw = [k.strip() for k in kw.split(",") if k.strip()]
        out.append({
            "id": str(e.get("id") or f"faq{i}"),
            "q": str(e["q"]).strip(),
            "a": str(e["a"]).strip(),
            "keywords": [str(k).strip().lower() for k in kw if str(k).strip()],
        })
    return out or default_faq()


def load_faq():
    conn = get_conn()
    try:
        row = conn.execute("SELECT value FROM bot_state WHERE key=?", (FAQ_KEY,)).fetchone()
    except Exception:
        row = None
    conn.close()
    return normalize_faq(row["value"] if row else None)


def save_faq(raw):
    entries = normalize_faq(raw)
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
        (FAQ_KEY, json.dumps(entries)),
    )
    conn.commit()
    conn.close()
    return entries


def render_text(text, store_name):
    """Ganti placeholder {store} dengan nama toko."""
    return (text or "").replace("{store}", store_name)


_WORD_RE = re.compile(r"[a-z0-9]+")


def match_question(question, entries):
    """Cari entri FAQ paling cocok untuk sebuah pertanyaan member.

    Skoring sederhana berbasis kata kunci (substring) + tumpang-tindih kata.
    Mengembalikan entri terbaik atau None bila tak ada yang relevan.
    """
    if not question or not entries:
        return None
    q = question.lower()
    q_words = set(_WORD_RE.findall(q))
    best, best_score = None, 0
    for e in entries:
        score = 0
        for kw in e.get("keywords", []):
            if not kw:
                continue
            if kw in q:                      # frasa kata kunci muncul utuh
                score += 3 + kw.count(" ")
            else:
                kw_words = set(_WORD_RE.findall(kw))
                if kw_words and kw_words <= q_words:  # semua kata kw ada
                    score += 2
        # sedikit bobot dari kemiripan dengan judul pertanyaan
        title_words = set(_WORD_RE.findall(e.get("q", "").lower()))
        score += len(title_words & q_words)
        if score > best_score:
            best, best_score = e, score
    # ambang minimal supaya tidak menjawab ngawur
    return best if best_score >= 2 else None
