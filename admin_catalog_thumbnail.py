"""admin_catalog_thumbnail.py - Editor Media Katalog (thumbnail & banner).

Blueprint terpisah (pola sama dgn admin_faq.py). Admin bisa mengatur URL
thumbnail (gambar kecil) DAN banner (gambar besar/embed.set_image) untuk tiap
embed katalog produk (robux, ml, gp, vilog, lainnya). Data disimpan di bot_state
(key catalog_thumbnails & catalog_banners) dipakai bareng oleh build_catalog_embed
tiap cog.

  - /catalog-thumbnails        : halaman editor (thumbnail + banner per katalog)
  - /catalog-thumbnails/save   : simpan thumbnail (POST JSON {thumbnails})
  - /catalog-thumbnails/reset  : kosongkan thumbnail (-> default)
  - /catalog-banners/save      : simpan banner (POST JSON {banners})
  - /catalog-banners/reset     : kosongkan banner (-> tanpa banner)

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
    payload = request.get_json(force=True, silent=True) or {}
    saved = cs.save_settings(payload.get("thumbnails", payload))
    return jsonify({"ok": True, "thumbnails": saved})


@catalog_thumb_bp.route("/catalog-thumbnails/reset", methods=["POST"])
def reset_route():
    g = _guard()
    if g:
        return g
    saved = cs.save_settings({})
    return jsonify({"ok": True, "thumbnails": saved})


@catalog_thumb_bp.route("/catalog-banners/save", methods=["POST"])
def save_banner_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    saved = cs.save_banners(payload.get("banners", payload))
    return jsonify({"ok": True, "banners": saved})


@catalog_thumb_bp.route("/catalog-banners/reset", methods=["POST"])
def reset_banner_route():
    g = _guard()
    if g:
        return g
    saved = cs.save_banners({})
    return jsonify({"ok": True, "banners": saved})


@catalog_thumb_bp.route("/catalog-thumbnails")
def page():
    g = _guard()
    if g:
        return g
    from admin import render_page

    data_json = json.dumps({
        "catalogs": cs.CATALOGS,
        "thumbnails": cs.load_settings(),
        "banners": cs.load_banners(),
        "defaultThumb": cs.DEFAULT_THUMBNAIL,
    })

    content = """
<div class="page-header">
  <div>
    <h2>Media Katalog</h2>
    <p class="text-muted">Atur thumbnail (gambar kecil) &amp; banner (gambar besar) tiap embed katalog produk.</p>
  </div>
  <div class="page-actions" style="display:flex;gap:.5rem;">
    <button class="btn btn-primary" onclick="saveAll()">Simpan Semua</button>
    <button class="btn btn-ghost" onclick="resetAll()">Reset Default</button>
  </div>
</div>

<div class="card" style="margin-bottom:1rem;">
  <div class="card-body">
    <div class="note" style="margin:0;">
      Tempel <b>URL gambar</b> (http/https) untuk tiap katalog.
      <b>Thumbnail</b> tampil kecil di pojok embed (kosong = pakai logo default toko).
      <b>Banner</b> tampil lebar di bawah embed (kosong = tanpa banner).
      Setelah simpan, refresh embed katalog di Discord (mis. <code>!robuxrefresh</code>,
      <code>!mlcatalog</code>, dsb.) agar berubah.
      <br>Catatan: katalog <b>ML</b> adalah embed gabungan Topup Diamond Game (termasuk FF &amp; WDP).
    </div>
  </div>
</div>

<div id="list"></div>
<div id="status" style="margin-top:.6rem;font-size:.85rem;"></div>

<script>
var D = DATA_JSON;
var THUMB = {}, BANNER = {};
D.catalogs.forEach(function(c){ THUMB[c[0]] = D.thumbnails[c[0]] || ""; BANNER[c[0]] = D.banners[c[0]] || ""; });

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function setStatus(msg, ok){
  document.getElementById('status').innerHTML =
    '<span style="color:var(--'+(ok?'success':'warning')+')">'+(ok?'\\u2713 ':'\\u25CF ')+msg+'</span>';
}
function thumbSrc(code){ return THUMB[code] && THUMB[code].trim() ? THUMB[code].trim() : D.defaultThumb; }

function render(){
  var html = '';
  D.catalogs.forEach(function(c){
    var code=c[0], label=c[1];
    var hasBanner = BANNER[code] && BANNER[code].trim();
    html += '<div class="card" style="margin-bottom:1rem;">'
      + '<div class="card-header" style="display:flex;align-items:center;gap:.6rem;">'
      + '<span style="font-weight:700;">'+esc(label)+'</span>'
      + '<span class="text-muted" style="font-size:.75rem;">('+code+')</span></div>'
      + '<div class="card-body">'
      + '<div style="display:grid;grid-template-columns:1fr;gap:1.1rem;">'

      // Thumbnail row
      + '<div style="display:flex;gap:1rem;align-items:flex-start;flex-wrap:wrap;">'
      + '<img id="th-'+code+'" src="'+esc(thumbSrc(code))+'" alt="" '
      + 'style="width:72px;height:72px;border-radius:12px;object-fit:cover;border:1px solid var(--border);background:var(--surface3);flex:none;" '
      + 'onerror="this.style.opacity=.25;">'
      + '<div style="flex:1 1 320px;min-width:240px;">'
      + '<div class="form-group" style="margin:0;"><label>Thumbnail <small class="text-muted">(gambar kecil)</small></label>'
      + '<input type="text" id="thin-'+code+'" placeholder="'+esc(D.defaultThumb)+'" value="'+esc(THUMB[code])+'" '
      + 'oninput="onThumb(\\''+code+'\\', this.value);"></div></div></div>'

      // Banner row
      + '<div>'
      + '<div class="form-group" style="margin:0 0 .6rem 0;"><label>Banner <small class="text-muted">(gambar besar / lebar)</small></label>'
      + '<input type="text" id="bnin-'+code+'" placeholder="https://... (kosongkan untuk tanpa banner)" value="'+esc(BANNER[code])+'" '
      + 'oninput="onBanner(\\''+code+'\\', this.value);"></div>'
      + '<img id="bn-'+code+'" src="'+esc(hasBanner?BANNER[code].trim():'')+'" alt="" '
      + 'style="width:100%;max-height:200px;border-radius:12px;object-fit:cover;border:1px solid var(--border);background:var(--surface3);'+(hasBanner?'':'display:none;')+'" '
      + 'onerror="this.style.opacity=.25;">'
      + '<div id="bnph-'+code+'" class="text-muted" style="'+(hasBanner?'display:none;':'')+'font-size:.8rem;padding:.9rem;border:1px dashed var(--border);border-radius:12px;text-align:center;">Tidak ada banner</div>'
      + '</div>'

      + '</div></div></div>';
  });
  document.getElementById('list').innerHTML = html;
}
function onThumb(code, val){
  THUMB[code] = val;
  var img = document.getElementById('th-'+code);
  if(img){ img.src = (val && val.trim()) ? val.trim() : D.defaultThumb; img.style.opacity = 1; }
  markDirty();
}
function onBanner(code, val){
  BANNER[code] = val;
  var img = document.getElementById('bn-'+code), ph = document.getElementById('bnph-'+code);
  if(val && val.trim()){
    if(img){ img.src = val.trim(); img.style.display=''; img.style.opacity=1; }
    if(ph) ph.style.display='none';
  } else {
    if(img) img.style.display='none';
    if(ph) ph.style.display='';
  }
  markDirty();
}
function markDirty(){ setStatus('Perubahan belum disimpan', false); }

function saveAll(){
  Promise.all([
    fetch('/catalog-thumbnails/save',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({thumbnails:THUMB})}).then(function(r){return r.json();}),
    fetch('/catalog-banners/save',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({banners:BANNER})}).then(function(r){return r.json();})
  ]).then(function(res){
    var t=res[0], b=res[1];
    if(t.ok && b.ok){
      D.catalogs.forEach(function(c){ THUMB[c[0]]=t.thumbnails[c[0]]||""; BANNER[c[0]]=b.banners[c[0]]||""; });
      render();
      setStatus('Tersimpan. Refresh embed katalog di Discord agar berubah.', true);
    } else {
      setStatus('Sebagian gagal disimpan (pastikan URL http/https valid).', false);
    }
  }).catch(function(){ setStatus('Gagal menyimpan.', false); });
}
function resetAll(){
  if(!confirm('Kosongkan semua thumbnail & banner (kembali ke default)?')) return;
  Promise.all([
    fetch('/catalog-thumbnails/reset',{method:'POST'}),
    fetch('/catalog-banners/reset',{method:'POST'})
  ]).then(function(){ location.reload(); });
}
render();
</script>"""
    content = content.replace("DATA_JSON", data_json)
    return render_page(content)
