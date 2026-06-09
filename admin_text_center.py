"""admin_text_center.py - Halaman indeks "Pusat Teks Bot".

Satu halaman ringkas berisi pintasan ke SEMUA editor teks bot yang tersebar di
sidebar, dikelompokkan per kategori. Murni front-end admin (tidak menyentuh cog
atau DB) — sekadar memudahkan admin menemukan editor yang diinginkan.

  - /text-center : grid kartu link ke tiap editor teks
"""
from flask import Blueprint, session, redirect

text_center_bp = Blueprint("text_center_bp", __name__)

# (Judul grup, [(emoji, label, route, deskripsi singkat), ...]).
_GROUPS = [
    ("Sambutan & Member", [
        ("👋", "Pesan Member", "/welcome-editor", "Welcome, boost, leave & sapaan publik"),
        ("✉️", "DM Sambutan", "/dm-editor", "DM sambutan untuk member baru"),
        ("🔔", "DM Perpanjangan", "/subfollowup-editor", "Pengingat langganan hampir habis"),
        ("💤", "Pesan AFK", "/afk-editor", "Set / kembali / notif mention AFK"),
    ]),
    ("Toko & Transaksi", [
        ("🏪", "Status Toko", "/store-status-editor", "Label voice channel buka/tutup"),
        ("🛡️", "Pesan Garansi", "/warranty-editor", "Panel, penolakan klaim & tiket"),
        ("📋", "Teks Antrian", "/queue-editor", "Papan antrian & kartu posisi"),
        ("🧾", "Pesan Order", "/order-editor", "Notif selesai & batal"),
        ("⭐", "Pesan Rating", "/review-editor", "Prompt, struk, pengingat & terima kasih"),
    ]),
    ("Katalog Layanan", [
        ("🔁", "Panel Midman", "/midman-editor", "Judul/deskripsi + konfirmasi trade"),
        ("🎮", "Katalog Vilog", "/vilog-editor", "Topup Robux via Login"),
        ("🎟️", "Katalog GP", "/gp-editor", "Topup Robux via Gamepass"),
        ("🪙", "Katalog Robux", "/robux-editor", "Robux Store"),
        ("💎", "Katalog ML", "/ml-editor", "Topup Diamond"),
        ("🛒", "Katalog Lainnya", "/lainnya-editor", "Panel & auto-reply layanan lainnya"),
        ("📄", "Info Kategori Lainnya", "/lainnya-info-editor", "Deskripsi & S&K per kategori"),
    ]),
    ("Bantuan & Komunitas", [
        ("❓", "Teks FAQ", "/faq-text-editor", "Embed FAQ, Auto-CS & /saran"),
        ("📖", "Teks /help", "/help-editor", "Pembungkus panduan slash command"),
        ("🏆", "Papan Top Spender", "/topspender-editor", "Leaderboard pelanggan"),
        ("🏅", "Teks Badge & Profil", "/profiltext-editor", "Embed /badges & fallback /profil"),
    ]),
]


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@text_center_bp.route("/text-center")
def page_text_center():
    g = _guard()
    if g:
        return g
    from admin import render_page

    total = sum(len(items) for _, items in _GROUPS)
    blocks = []
    for group_title, items in _GROUPS:
        cards = []
        for emoji, label, route, desc in items:
            cards.append(
                '<a href="' + route + '" class="card" '
                'style="display:block;text-decoration:none;border:1px solid var(--border);'
                'border-radius:10px;padding:.9rem 1rem;transition:border-color .15s;">'
                '<div style="font-size:1.3rem;line-height:1;margin-bottom:.4rem;">' + emoji + '</div>'
                '<div style="font-weight:700;color:var(--text);">' + _esc(label) + '</div>'
                '<div style="font-size:.78rem;color:var(--muted);margin-top:.2rem;">' + _esc(desc) + '</div>'
                '</a>'
            )
        blocks.append(
            '<div class="nav-section" style="margin:1.4rem 0 .6rem;">' + _esc(group_title) + '</div>'
            '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:.8rem;">'
            + "".join(cards) +
            '</div>'
        )

    content = (
        '<div class="page-header">'
        '<div class="page-title">Pusat Teks Bot <small>' + str(total) +
        ' editor teks dalam satu tempat</small></div>'
        '</div>'
        '<div class="card"><div class="card-body">'
        '<div class="note" style="margin-bottom:.4rem;">'
        'Semua teks bot yang bisa diubah dari panel, dikelompokkan biar gampang dicari. '
        'Klik kartu untuk membuka editornya. Tiap editor punya tombol <b>Default</b> untuk reset.'
        '</div>'
        + "".join(blocks) +
        '</div></div>'
    )
    return render_page(content)
