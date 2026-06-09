"""admin_selfhost.py - Halaman "Cek Kesiapan Self-Host" untuk Admin Panel.

Menampilkan status environment variable (.env): mana yang WAJIB belum diisi
(bot tidak jalan / fitur inti rusak) dan mana yang DISARANKAN. Read-only —
tidak menulis apa pun. Pola blueprint sama dgn admin_faq.py.

  - /self-host-check : halaman ringkasan kesiapan
"""
import os

from flask import Blueprint, session, redirect

from utils import selfhost_check as shc

selfhost_bp = Blueprint("selfhost_bp", __name__)


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


@selfhost_bp.route("/self-host-check")
def page():
    g = _guard()
    if g:
        return g
    from admin import render_page

    report = shc.check_env(dict(os.environ))

    if report["ready"]:
        banner = ('<div class="card" style="border-left:4px solid var(--success);margin-bottom:1rem;">'
                  '<div class="card-body"><b style="color:var(--success)">✓ Siap!</b> '
                  'Semua variabel WAJIB sudah terisi. Bot semestinya bisa berjalan.</div></div>')
    else:
        miss = ", ".join(_esc(m) for m in report["missing_required"])
        banner = ('<div class="card" style="border-left:4px solid var(--danger);margin-bottom:1rem;">'
                  '<div class="card-body"><b style="color:var(--danger)">✗ Belum siap.</b> '
                  f'{len(report["missing_required"])} variabel WAJIB belum diisi: '
                  f'<code>{miss}</code><br><small style="color:var(--muted)">'
                  'Isi di file <code>.env</code> lalu restart bot &amp; panel.</small></div></div>')

    def _rows(items, with_default):
        out = []
        for it in items:
            if it["set"]:
                status = '<span style="color:var(--success)">✓ terisi</span>'
            elif with_default:
                status = ('<span style="color:var(--warning)">— pakai default: '
                          f'<code>{_esc(it["default"])}</code></span>')
            else:
                status = '<span style="color:var(--danger)">✗ belum diisi</span>'
            out.append(
                '<tr>'
                f'<td style="white-space:nowrap;"><code>{_esc(it["name"])}</code></td>'
                f'<td>{_esc(it["desc"])}</td>'
                f'<td style="white-space:nowrap;">{status}</td>'
                '</tr>'
            )
        return "".join(out)

    req_pct = int(100 * report["required_set"] / max(1, report["required_total"]))
    rec_pct = int(100 * report["recommended_set"] / max(1, report["recommended_total"]))

    content = f"""
<div class="page-header">
  <div class="page-title">Cek Kesiapan Self-Host
    <small>Status variabel .env — tidak menyimpan apa pun (read-only)</small></div>
</div>
{banner}
<div class="card"><div class="card-body">
  <h3 style="margin:0 0 .3rem;">Wajib <small style="color:var(--muted);font-weight:400;">
    ({report["required_set"]}/{report["required_total"]} terisi · {req_pct}%)</small></h3>
  <div style="font-size:.85rem;color:var(--muted);margin-bottom:.6rem;">Bot tidak berjalan / fitur inti rusak tanpa ini.</div>
  <table class="data-table" style="width:100%;border-collapse:collapse;">
    <thead><tr><th style="text-align:left;">Variabel</th><th style="text-align:left;">Fungsi</th><th style="text-align:left;">Status</th></tr></thead>
    <tbody>{_rows(report["required"], False)}</tbody>
  </table>
</div></div>
<div class="card" style="margin-top:1rem;"><div class="card-body">
  <h3 style="margin:0 0 .3rem;">Disarankan <small style="color:var(--muted);font-weight:400;">
    ({report["recommended_set"]}/{report["recommended_total"]} terisi · {rec_pct}%)</small></h3>
  <div style="font-size:.85rem;color:var(--muted);margin-bottom:.6rem;">Fitur opsional. Aman bila kosong — ada default / otomatis nonaktif.</div>
  <table class="data-table" style="width:100%;border-collapse:collapse;">
    <thead><tr><th style="text-align:left;">Variabel</th><th style="text-align:left;">Fungsi</th><th style="text-align:left;">Status</th></tr></thead>
    <tbody>{_rows(report["recommended"], True)}</tbody>
  </table>
</div></div>
"""
    return render_page(content)
