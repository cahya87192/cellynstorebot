"""admin_text_backup.py - Backup & Restore semua teks bot.

Halaman admin untuk meng-export semua teks yang sudah dikustomisasi ke file JSON
(download) dan meng-import-nya kembali (cadangan / pindah server). Memanfaatkan
utils.text_backup. Tidak menyentuh cog.

  - /text-backup          : halaman download + form import
  - /text-backup/export   : unduh JSON backup (GET)
  - /text-backup/import   : terapkan backup (POST JSON {data})
"""
from flask import Blueprint, request, session, redirect, jsonify, Response

from utils import text_backup as backup

text_backup_bp = Blueprint("text_backup_bp", __name__)


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@text_backup_bp.route("/text-backup/export")
def export_route():
    g = _guard()
    if g:
        return g
    data = backup.export_json()
    resp = Response(data, mimetype="application/json")
    resp.headers["Content-Disposition"] = "attachment; filename=cellyn-texts-backup.json"
    return resp


@text_backup_bp.route("/text-backup/import", methods=["POST"])
def import_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    data = payload.get("data")
    if data is None:
        return jsonify({"ok": False, "error": "Tidak ada data backup."}), 400
    try:
        result = backup.import_data(data)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True, **result})


@text_backup_bp.route("/text-backup")
def page_text_backup():
    g = _guard()
    if g:
        return g
    from admin import render_page

    total_keys = len(backup.collect_keys())

    content = """
<div class="page-header">
  <div class="page-title">Backup Teks <small>Cadangkan &amp; pulihkan semua teks bot</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Export menyimpan SEMUA teks yang sudah kamu ubah (dari TOTAL_KEYS kunci teks + info kategori)
    ke satu file JSON. Berguna untuk cadangan sebelum eksperimen atau pindah server.
    Import hanya menulis kunci yang dikenal — aman.
  </div>

  <div style="margin-bottom:1.4rem;">
    <div style="font-weight:700;margin-bottom:.5rem;">1. Export (unduh)</div>
    <a href="/text-backup/export" class="btn btn-primary btn-sm">⬇️ Download backup JSON</a>
  </div>

  <div style="border-top:1px solid var(--border);padding-top:1.2rem;">
    <div style="font-weight:700;margin-bottom:.5rem;">2. Import (pulihkan)</div>
    <div class="form-group">
      <input type="file" id="file" accept="application/json,.json" onchange="loadFile()" />
    </div>
    <div class="form-group">
      <textarea id="data" rows="8" style="width:100%;font-family:monospace;font-size:.8rem;"
        placeholder="Tempel isi file backup JSON di sini, atau pilih file di atas."></textarea>
    </div>
    <button class="btn btn-primary btn-sm" onclick="doImport()">⬆️ Terapkan backup</button>
    <span id="st" style="margin-left:.6rem;font-size:.85rem;"></span>
  </div>
</div></div>

<script>
function setStatus(msg, ok){
  document.getElementById('st').innerHTML =
    '<span style="color:var(--'+(ok?'success':'warning')+')">'+(ok?'✓ ':'● ')+msg+'</span>';
}
function loadFile(){
  var f = document.getElementById('file').files[0];
  if(!f) return;
  var rd = new FileReader();
  rd.onload = function(e){ document.getElementById('data').value = e.target.result; setStatus('File dimuat. Klik Terapkan.', true); };
  rd.readAsText(f);
}
function doImport(){
  var raw = document.getElementById('data').value.trim();
  if(!raw){ setStatus('Isi/pilih file backup dulu.', false); return; }
  var parsed;
  try { parsed = JSON.parse(raw); }
  catch(e){ setStatus('JSON tidak valid: '+e.message, false); return; }
  if(!confirm('Terapkan backup ini? Teks yang ada akan ditimpa oleh isi backup.')) return;
  fetch('/text-backup/import',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({data:parsed})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ setStatus('Berhasil: '+d.applied+' teks, '+d.categories+' kategori diterapkan'
        + (d.skipped? ', '+d.skipped+' dilewati':'') + '.', true); }
      else { setStatus(d.error||'Gagal import', false); }
    }).catch(function(e){ setStatus('Error: '+e, false); });
}
</script>"""
    content = content.replace("TOTAL_KEYS", str(total_keys))
    return render_page(content)
