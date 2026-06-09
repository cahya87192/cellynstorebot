"""admin_lainnya_info.py - Editor deskripsi & S&K per-kategori Layanan Lainnya.

Blueprint terpisah. Mengedit isi tabel `lainnya_category_info` (deskripsi + Syarat
& Ketentuan) yang dipakai cog `cogs/lainnya.py` di embed tiket & auto-reply. Cog
sudah membaca tabel ini lewat load_category_info(), jadi perubahan langsung dipakai
berikutnya — tidak perlu ubah kode cog.

  - /lainnya-info-editor          : pilih kategori + edit deskripsi & S&K
  - /lainnya-info-editor/save     : simpan (POST JSON {category,description,terms})
  - /lainnya-info-editor/reset    : kembalikan ke default statis (POST JSON {category})
"""
import json

from flask import Blueprint, request, session, redirect, jsonify

from utils import lainnya_category as lcat

lainnya_info_bp = Blueprint("lainnya_info_bp", __name__)


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@lainnya_info_bp.route("/lainnya-info-editor/save", methods=["POST"])
def save_lainnya_info_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    category = (payload.get("category") or "").strip()
    if not category:
        return jsonify({"ok": False, "error": "Kategori wajib dipilih."}), 400
    description = payload.get("description") or ""
    terms = payload.get("terms") or ""
    if not description.strip() and not terms.strip():
        return jsonify({"ok": False, "error": "Deskripsi & S&K tidak boleh kosong dua-duanya. Gunakan Default untuk reset."}), 400
    lcat.save_info(category, description=description, terms=terms)
    return jsonify({"ok": True})


@lainnya_info_bp.route("/lainnya-info-editor/reset", methods=["POST"])
def reset_lainnya_info_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    category = (payload.get("category") or "").strip()
    if not category:
        return jsonify({"ok": False, "error": "Kategori wajib dipilih."}), 400
    info = lcat.reset_info(category)
    return jsonify({"ok": True, "description": info.get("description", ""), "terms": info.get("terms", "")})


@lainnya_info_bp.route("/lainnya-info-editor")
def page_lainnya_info():
    g = _guard()
    if g:
        return g
    from admin import render_page

    cats = []
    for category in lcat.list_categories():
        info = lcat.load_info(category)
        cats.append({
            "category": category,
            "description": info.get("description", ""),
            "terms": info.get("terms", ""),
        })
    cats_json = json.dumps(cats)

    content = """
<div class="page-header">
  <div class="page-title">Info Kategori Lainnya <small>Deskripsi &amp; Syarat/Ketentuan per kategori</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Teks ini muncul di embed tiket &amp; balasan auto-reply kategori. Pilih kategori, ubah,
    lalu Simpan. Tombol <b>Default</b> mengembalikan ke teks bawaan. Mendukung <b>**bold**</b> ala Discord.
  </div>
  <div class="form-group" style="max-width:420px;">
    <label for="catsel"><b>Kategori</b></label>
    <select id="catsel" style="width:100%;" onchange="selectCat()"></select>
  </div>
  <div id="editor" style="display:none;">
    <div class="form-group">
      <label><b>Deskripsi</b></label>
      <textarea id="desc" rows="4" style="width:100%;" oninput="onEdit()"></textarea>
    </div>
    <div class="form-group">
      <label><b>Syarat &amp; Ketentuan</b></label>
      <textarea id="terms" rows="6" style="width:100%;" oninput="onEdit()"></textarea>
    </div>
    <button class="btn btn-primary btn-sm" onclick="saveCat()">💾 Simpan</button>
    <button class="btn btn-ghost btn-sm" onclick="resetCat()">↺ Default</button>
    <span id="st" style="margin-left:.6rem;font-size:.85rem;"></span>
    <div style="margin-top:1rem;border-left:4px solid var(--accent);background:var(--surface3);border-radius:6px;padding:.8rem 1rem;">
      <div style="font-size:.78rem;color:var(--muted);margin-bottom:.3rem;">Pratinjau Deskripsi</div>
      <div id="pv_desc" style="color:var(--text);margin-bottom:.7rem;"></div>
      <div style="font-size:.78rem;color:var(--muted);margin-bottom:.3rem;">Pratinjau S&amp;K</div>
      <div id="pv_terms" style="color:var(--text);"></div>
    </div>
  </div>
</div></div>

<script>
var CATS = CATS_JSON;
var MAP = {};
CATS.forEach(function(c){ MAP[c.category] = c; });

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function fmt(s){ return esc(s).replace(/\\*\\*([^*]+)\\*\\*/g, "<b>$1</b>").replace(/\\n/g, "<br>"); }
function setStatus(msg, ok){
  document.getElementById('st').innerHTML =
    '<span style="color:var(--'+(ok?'success':'warning')+')">'+(ok?'✓ ':'● ')+msg+'</span>';
}
function preview(){
  document.getElementById('pv_desc').innerHTML = fmt(document.getElementById('desc').value) || '<span style="color:var(--muted)">(kosong)</span>';
  document.getElementById('pv_terms').innerHTML = fmt(document.getElementById('terms').value) || '<span style="color:var(--muted)">(kosong)</span>';
}
function onEdit(){ preview(); setStatus('Belum disimpan', false); }

function selectCat(){
  var cat = document.getElementById('catsel').value;
  var c = MAP[cat];
  if(!c){ document.getElementById('editor').style.display='none'; return; }
  document.getElementById('editor').style.display='block';
  document.getElementById('desc').value = c.description;
  document.getElementById('terms').value = c.terms;
  document.getElementById('st').innerHTML = '';
  preview();
}

function saveCat(){
  var cat = document.getElementById('catsel').value;
  var desc = document.getElementById('desc').value;
  var terms = document.getElementById('terms').value;
  fetch('/lainnya-info-editor/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({category:cat, description:desc, terms:terms})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ MAP[cat].description=desc; MAP[cat].terms=terms; setStatus('Tersimpan.', true); }
      else { setStatus(d.error||'Gagal menyimpan', false); }
    });
}
function resetCat(){
  var cat = document.getElementById('catsel').value;
  if(!confirm('Kembalikan info kategori "'+cat+'" ke teks default?')) return;
  fetch('/lainnya-info-editor/reset',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({category:cat})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){
        document.getElementById('desc').value = d.description;
        document.getElementById('terms').value = d.terms;
        MAP[cat].description = d.description; MAP[cat].terms = d.terms;
        preview();
        setStatus('Dikembalikan ke default.', true);
      } else { setStatus(d.error||'Gagal reset', false); }
    });
}

function build(){
  var sel = document.getElementById('catsel');
  var opts = '<option value="">— pilih kategori —</option>';
  CATS.forEach(function(c){ opts += '<option value="'+esc(c.category)+'">'+esc(c.category)+'</option>'; });
  sel.innerHTML = opts;
}
build();
</script>"""
    content = content.replace("CATS_JSON", cats_json)
    return render_page(content)
