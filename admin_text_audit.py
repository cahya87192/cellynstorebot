"""admin_text_audit.py - Riwayat perubahan teks bot.

Menampilkan jejak audit (kapan & apa) dari aksi simpan/reset editor teks + import/
reset-massal backup. Data dari utils.text_audit. Tidak menyentuh cog.

  - /text-audit         : tabel riwayat terbaru
  - /text-audit/clear   : kosongkan riwayat (POST)
"""
from flask import Blueprint, session, redirect, jsonify

from utils import text_audit

text_audit_bp = Blueprint("text_audit_bp", __name__)

# Label & warna ramah untuk tiap aksi.
_ACTION_LABEL = {
    "save": ("Simpan", "var(--accent)"),
    "reset": ("Default", "var(--warning)"),
    "import": ("Import backup", "var(--success)"),
    "reset_all": ("Reset semua", "var(--danger, #ED4245)"),
}


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@text_audit_bp.route("/text-audit/clear", methods=["POST"])
def clear_audit_route():
    g = _guard()
    if g:
        return g
    removed = text_audit.clear()
    return jsonify({"ok": True, "removed": removed})


@text_audit_bp.route("/text-audit")
def page_text_audit():
    g = _guard()
    if g:
        return g
    from admin import render_page

    entries = text_audit.recent(300)
    total = text_audit.count()

    if entries:
        rows = []
        for e in entries:
            act_label, act_color = _ACTION_LABEL.get(e["action"], (e["action"], "var(--muted)"))
            what = _esc(e.get("label") or e.get("kind") or e.get("key") or "—")
            detail = _esc(e.get("detail") or "")
            ts = _esc(e.get("ts") or "")
            rows.append(
                "<tr>"
                '<td style="white-space:nowrap;color:var(--muted);font-size:.8rem;" data-ts="' + ts + '">' + ts + "</td>"
                '<td><span style="color:' + act_color + ';font-weight:600;">' + _esc(act_label) + "</span></td>"
                "<td>" + what + "</td>"
                '<td style="color:var(--muted);font-size:.82rem;">' + detail + "</td>"
                "</tr>"
            )
        table = (
            '<div class="table-wrapper">'
            '<table style="width:100%;border-collapse:collapse;" class="audit-table">'
            '<thead><tr style="text-align:left;border-bottom:1px solid var(--border);">'
            '<th style="padding:.4rem;">Waktu</th><th style="padding:.4rem;">Aksi</th>'
            '<th style="padding:.4rem;">Teks</th><th style="padding:.4rem;">Detail</th>'
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        )
    else:
        table = '<div style="color:var(--muted);padding:1rem 0;">Belum ada riwayat perubahan teks.</div>'

    content = (
        '<div class="page-header">'
        '<div class="page-title">Riwayat Teks <small>' + str(total) +
        ' entri — kapan &amp; apa yang diubah</small></div>'
        '</div>'
        '<div class="card"><div class="card-body">'
        '<div class="note" style="margin-bottom:.8rem;">'
        'Jejak perubahan teks bot (simpan/default per editor, serta import &amp; reset-massal backup). '
        'Waktu dalam UTC. Maksimal 300 entri terbaru ditampilkan.'
        '</div>'
        '<div style="margin-bottom:.6rem;">'
        '<button class="btn btn-ghost btn-sm" onclick="clearAudit()">🗑️ Kosongkan riwayat</button>'
        '<span id="auditStatus" style="margin-left:.6rem;font-size:.85rem;"></span>'
        '</div>'
        + table +
        '</div></div>'
        '<script>'
        '(function(){'
        ' document.querySelectorAll("td[data-ts]").forEach(function(td){'
        '   var v=td.getAttribute("data-ts"); if(!v) return;'
        '   var d=new Date(v); if(!isNaN(d)) td.textContent=d.toLocaleString();'
        ' });'
        '})();'
        'function clearAudit(){'
        ' if(!confirm("Kosongkan seluruh riwayat perubahan teks?")) return;'
        ' fetch("/text-audit/clear",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"})'
        '  .then(function(r){return r.json();}).then(function(d){'
        '    var s=document.getElementById("auditStatus");'
        '    if(d.ok){ s.innerHTML="<span style=\\"color:var(--success)\\">✓ "+d.removed+" entri dihapus. Muat ulang halaman.</span>"; }'
        '    else { s.innerHTML="<span style=\\"color:var(--warning)\\">● Gagal.</span>"; }'
        '  });'
        '}'
        '</script>'
    )
    return render_page(content)
