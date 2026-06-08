"""admin_faq.py - Editor FAQ untuk Admin Panel.

Blueprint terpisah (pola sama dgn admin_profile_theme.py). Admin bisa
menambah/ubah/hapus entri FAQ lewat web UI; data disimpan di bot_state
(dipakai bareng oleh FAQ embed & Auto-CS di cogs/faq.py).

  - /faq-editor        : halaman editor (daftar entri + form per entri)
  - /faq-editor/save   : simpan seluruh daftar (POST JSON)
  - /faq-editor/reset  : kembalikan ke FAQ default

render_page di-import lazily di dalam view (hindari circular import).
"""
import json

from flask import Blueprint, request, session, redirect, jsonify

from utils import faq as faqlib

faq_bp = Blueprint("faq_bp", __name__)


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@faq_bp.route("/faq-editor/save", methods=["POST"])
def save_faq_route():
    g = _guard()
    if g:
        return g
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        payload = {}
    entries = payload.get("entries")
    saved = faqlib.save_faq(entries)
    return jsonify({"ok": True, "count": len(saved)})


@faq_bp.route("/faq-editor/reset", methods=["POST"])
def reset_faq_route():
    g = _guard()
    if g:
        return g
    saved = faqlib.save_faq(faqlib.default_faq())
    return jsonify({"ok": True, "count": len(saved)})



@faq_bp.route("/faq-editor")
def page_faq():
    g = _guard()
    if g:
        return g
    from admin import render_page

    entries = faqlib.load_faq()
    entries_json = json.dumps(entries)

    content = """
<div class="page-header">
  <div class="page-title">Editor FAQ <small>Tambah/ubah/hapus pertanyaan — dipakai FAQ &amp; Auto-CS</small></div>
  <div class="page-actions">
    <button class="btn btn-primary" onclick="saveFaq()">💾 Simpan</button>
    <button class="btn btn-ghost" onclick="addEntry()">➕ Tambah</button>
    <button class="btn btn-ghost" onclick="resetFaq()">↩️ Reset Default</button>
  </div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Gunakan <code>{store}</code> sebagai placeholder nama toko (otomatis diganti).
    <b>Keywords</b> dipisah koma — dipakai Auto-CS untuk mencocokkan pertanyaan member.
  </div>
  <div id="faqList"></div>
  <div id="status" style="margin-top:.6rem;font-size:.85rem;"></div>
</div></div>

<script>
var ENTRIES = ENTRIES_JSON;

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function setStatus(msg, ok){
  document.getElementById('status').innerHTML =
    '<span style="color:var(--'+(ok?'success':'warning')+')">'+(ok?'✓ ':'● ')+msg+'</span>';
}

function render(){
  var html = '';
  ENTRIES.forEach(function(e, i){
    html += '<div class="card" style="margin-bottom:.8rem;border:1px solid var(--border);">'
      + '<div class="card-body">'
      + '<div class="form-group"><label>Pertanyaan / Judul</label>'
      + '<input type="text" value="'+esc(e.q)+'" oninput="ENTRIES['+i+'].q=this.value;markDirty();"></div>'
      + '<div class="form-group"><label>Jawaban</label>'
      + '<textarea rows="4" oninput="ENTRIES['+i+'].a=this.value;markDirty();">'+esc(e.a)+'</textarea></div>'
      + '<div class="form-group"><label>Keywords (pisah koma)</label>'
      + '<input type="text" value="'+esc((e.keywords||[]).join(", "))+'" '
      + 'oninput="ENTRIES['+i+'].keywords=this.value.split(\',\').map(function(x){return x.trim();}).filter(Boolean);markDirty();"></div>'
      + '<button class="btn btn-ghost btn-sm" onclick="delEntry('+i+')">🗑️ Hapus</button>'
      + '</div></div>';
  });
  if(!ENTRIES.length) html = '<div class="empty">Belum ada entri. Klik ➕ Tambah.</div>';
  document.getElementById('faqList').innerHTML = html;
}
function markDirty(){ setStatus('Perubahan belum disimpan', false); }
function addEntry(){ ENTRIES.push({id:'faq'+Date.now(), q:'', a:'', keywords:[]}); render(); markDirty(); }
function delEntry(i){ ENTRIES.splice(i,1); render(); markDirty(); }
function saveFaq(){
  fetch('/faq-editor/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({entries:ENTRIES})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ setStatus('Tersimpan ('+d.count+' entri). Jalankan !faqrefresh di Discord untuk perbarui embed.', true); }
      else { setStatus('Gagal menyimpan', false); }
    });
}
function resetFaq(){
  if(!confirm('Kembalikan FAQ ke default?')) return;
  fetch('/faq-editor/reset',{method:'POST'}).then(function(r){return r.json();}).then(function(d){
    location.reload();
  });
}
render();
</script>"""
    content = content.replace("ENTRIES_JSON", entries_json)
    return render_page(content)
