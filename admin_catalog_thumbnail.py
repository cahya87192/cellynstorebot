"""admin_catalog_thumbnail.py - Editor Thumbnail Katalog untuk Admin Panel.

Blueprint terpisah (pola sama dgn admin_faq.py). Admin bisa mengatur URL
thumbnail untuk tiap embed katalog produk (robux, ml, gp, vilog, lainnya);
data disimpan di bot_state (key catalog_thumbnails) dipakai bareng oleh
build_catalog_embed tiap cog.

  - /catalog-thumbnails        : halaman editor (form URL per katalog)
  - /catalog-thumbnails/save   : simpan seluruh setting (POST JSON)
  - /catalog-thumbnails/reset  : kosongkan (kembali ke thumbnail default)

render_page di-import lazily di dalam view (hindari circular import).
"""
import json

from flask import Blueprint, request, session, redirect, jsonify

from utils import catalog_settings as cs

catalog_thumb_bp = Blueprint("catalog_thumb_bp", __name__)


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@catalog_thumb_bp.route("/catalog-thumbnails/save", methods=["POST"])
def save_route():
    g = _guard()
    if g:
        return g
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        payload = {}
    saved = cs.save_settings(payload.get("thumbnails", payload))
    return jsonify({"ok": True, "thumbnails": saved})


@catalog_thumb_bp.route("/catalog-thumbnails/reset", methods=["POST"])
def reset_route():
    g = _guard()
    if g:
        return g
    saved = cs.save_settings({})
    return jsonify({"ok": True, "thumbnails": saved})


@catalog_thumb_bp.route("/catalog-thumbnails")
def page():
    g = _guard()
    if g:
        return g
    from admin import render_page

    current = cs.load_settings()
    data_json = json.dumps({
        "catalogs": cs.CATALOGS,
        "current": current,
        "default": cs.DEFAULT_THUMBNAIL,
    })

    content = """
<div class="page-header">
  <div class="page-title">Thumbnail Katalog <small>Atur gambar kecil tiap embed katalog produk</small></div>
  <div class="page-actions">
    <button class="btn btn-primary" onclick="saveAll()">💾 Simpan</button>
    <button class="btn btn-ghost" onclick="resetAll()">↩️ Reset Default</button>
  </div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Tempel <b>URL gambar</b> (http/https) untuk tiap katalog. Kosongkan untuk memakai
    thumbnail default toko. Setelah simpan, refresh embed katalog di Discord
    (mis. <code>!robuxrefresh</code>, <code>!mlcatalog</code>, dsb.) agar berubah.
    <br>Catatan: katalog <b>ML</b> adalah embed gabungan Topup Diamond Game (termasuk FF &amp; WDP).
  </div>
  <div id="list"></div>
  <div id="status" style="margin-top:.6rem;font-size:.85rem;"></div>
</div></div>

<script>
var D = DATA_JSON;
var STATE = {};
D.catalogs.forEach(function(c){ STATE[c[0]] = D.current[c[0]] || ""; });

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function setStatus(msg, ok){
  document.getElementById('status').innerHTML =
    '<span style="color:var(--'+(ok?'success':'warning')+')">'+(ok?'✓ ':'● ')+msg+'</span>';
}
function previewSrc(code){ return STATE[code] && STATE[code].trim() ? STATE[code].trim() : D.default; }

function render(){
  var html = '';
  D.catalogs.forEach(function(c){
    var code=c[0], label=c[1];
    html += '<div class="card" style="margin-bottom:.8rem;border:1px solid var(--border);">'
      + '<div class="card-body" style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap;">'
      + '<img id="img-'+code+'" src="'+esc(previewSrc(code))+'" alt="" '
      + 'style="width:64px;height:64px;border-radius:10px;object-fit:cover;background:#222;" '
      + 'onerror="this.style.opacity=.3;">'
      + '<div style="flex:1 1 320px;min-width:260px;">'
      + '<div class="form-group" style="margin:0;"><label>'+esc(label)+' <small style="color:var(--muted)">('+code+')</small></label>'
      + '<input type="text" id="in-'+code+'" placeholder="'+esc(D.default)+'" value="'+esc(STATE[code])+'" '
      + 'oninput="updateThumb(\\''+code+'\\', this.value);"></div>'
      + '</div></div></div>';
  });
  document.getElementById('list').innerHTML = html;
}
function updateThumb(code, val){
  STATE[code] = val;
  var img = document.getElementById('img-'+code);
  if(img){ img.src = (val && val.trim()) ? val.trim() : D.default; img.style.opacity = 1; }
  markDirty();
}
function markDirty(){ setStatus('Perubahan belum disimpan', false); }
function saveAll(){
  fetch('/catalog-thumbnails/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({thumbnails:STATE})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ STATE={}; D.catalogs.forEach(function(c){STATE[c[0]]=d.thumbnails[c[0]]||"";}); render();
        setStatus('Tersimpan. Refresh embed katalog di Discord agar berubah.', true); }
      else { setStatus('Gagal menyimpan (cek URL harus http/https)', false); }
    });
}
function resetAll(){
  if(!confirm('Kosongkan semua thumbnail (kembali ke default)?')) return;
  fetch('/catalog-thumbnails/reset',{method:'POST'}).then(function(r){return r.json();}).then(function(){
    location.reload();
  });
}
render();
</script>"""
    content = content.replace("DATA_JSON", data_json)
    return render_page(content)
