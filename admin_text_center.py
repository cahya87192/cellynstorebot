"""admin_text_center.py - Halaman indeks "Pusat Teks Bot".

Satu halaman ringkas berisi pintasan ke SEMUA editor teks bot yang tersebar di
sidebar, dikelompokkan per kategori. Dilengkapi pencarian cepat + tombol "Reset
semua teks ke default". Murni front-end admin untuk daftar link; reset memakai
utils.text_backup.reset_all.

  - /text-center            : grid kartu link + pencarian + reset-all
  - /text-center/reset-all  : hapus semua kustomisasi teks (POST)
"""
from flask import Blueprint, session, redirect, jsonify

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
    ("Alat", [
        ("💾", "Backup Teks", "/text-backup", "Export / import semua teks"),
    ]),
]


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@text_center_bp.route("/text-center/reset-all", methods=["POST"])
def reset_all_route():
    g = _guard()
    if g:
        return g
    from utils import text_backup
    res = text_backup.reset_all()
    return jsonify({"ok": True, **res})


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
            search = _esc((label + " " + desc).lower())
            cards.append(
                '<a href="' + route + '" class="tc-card card" data-search="' + search + '" '
                'style="display:block;text-decoration:none;border:1px solid var(--border);'
                'border-radius:10px;padding:.9rem 1rem;transition:border-color .15s;">'
                '<div style="font-size:1.3rem;line-height:1;margin-bottom:.4rem;">' + emoji + '</div>'
                '<div style="font-weight:700;color:var(--text);">' + _esc(label) + '</div>'
                '<div style="font-size:.78rem;color:var(--muted);margin-top:.2rem;">' + _esc(desc) + '</div>'
                '</a>'
            )
        blocks.append(
            '<div class="tc-group" data-group="' + _esc(group_title.lower()) + '">'
            '<div class="nav-section" style="margin:1.4rem 0 .6rem;">' + _esc(group_title) + '</div>'
            '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:.8rem;">'
            + "".join(cards) +
            '</div></div>'
        )

    content = (
        '<div class="page-header">'
        '<div class="page-title">Pusat Teks Bot <small>' + str(total) +
        ' editor teks dalam satu tempat</small></div>'
        '</div>'
        '<div class="card"><div class="card-body">'
        '<div class="note" style="margin-bottom:.8rem;">'
        'Semua teks bot yang bisa diubah dari panel, dikelompokkan biar gampang dicari. '
        'Klik kartu untuk membuka editornya. Tiap editor punya tombol <b>Default</b> untuk reset.'
        '</div>'
        '<div style="display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;margin-bottom:.4rem;">'
        '<input type="text" id="tcSearch" placeholder="🔎 Cari editor (mis. garansi, antrian, dm)..." '
        'style="flex:1;min-width:220px;" oninput="tcFilter()" />'
        '<button class="btn btn-ghost btn-sm" onclick="tcResetAll()">↺ Reset semua teks</button>'
        '</div>'
        '<div id="tcNoResult" style="display:none;color:var(--muted);padding:.6rem 0;">Tidak ada editor cocok.</div>'
        '<span id="tcStatus" style="font-size:.85rem;"></span>'
        + "".join(blocks) +
        '</div></div>'
        '<script>'
        'function tcFilter(){'
        ' var q=(document.getElementById("tcSearch").value||"").toLowerCase().trim();'
        ' var shown=0;'
        ' document.querySelectorAll(".tc-group").forEach(function(g){'
        '   var any=false;'
        '   g.querySelectorAll(".tc-card").forEach(function(c){'
        '     var hit=!q||(c.getAttribute("data-search")||"").indexOf(q)>=0;'
        '     c.style.display=hit?"block":"none"; if(hit){any=true;shown++;}'
        '   });'
        '   g.style.display=any?"block":"none";'
        ' });'
        ' document.getElementById("tcNoResult").style.display=shown?"none":"block";'
        '}'
        'function tcResetAll(){'
        ' if(!confirm("Reset SEMUA teks bot ke default? Semua kustomisasi teks akan dihapus dan tidak bisa dibatalkan.")) return;'
        ' fetch("/text-center/reset-all",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"})'
        '  .then(function(r){return r.json();}).then(function(d){'
        '    var s=document.getElementById("tcStatus");'
        '    if(d.ok){ s.innerHTML="<span style=\\"color:var(--success)\\">✓ "+d.removed+" teks & "+d.categories_cleared+" info kategori dikembalikan ke default.</span>"; }'
        '    else { s.innerHTML="<span style=\\"color:var(--warning)\\">● Gagal reset.</span>"; }'
        '  }).catch(function(e){ document.getElementById("tcStatus").innerHTML="● Error: "+e; });'
        '}'
        '</script>'
    )
    return render_page(content)
