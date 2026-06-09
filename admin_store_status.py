"""admin_store_status.py - Editor label status toko (cogs/store_status.py).

Blueprint terpisah (pola sama dgn admin_welcome.py bagian teks tunggal). Mengubah
nama voice channel yang dipakai bot saat toko buka / tutup. Cog
`cogs/store_status.py` membaca label lewat utils.store_status.get_label(), jadi
perubahan di sini dipakai pada sinkronisasi status berikutnya.

  - /store-status-editor          : form label buka & tutup + pratinjau langsung
  - /store-status-editor/save     : simpan label (POST JSON {kind,text})
  - /store-status-editor/reset    : kembalikan satu label ke default (POST JSON {kind})
"""
import json

from flask import Blueprint, request, session, redirect, jsonify

from utils import store_status as statuslib

store_status_bp = Blueprint("store_status_bp", __name__)

# Definisi tiap label: getter/setter + default + keterangan.
_KINDS = {
    "open": {
        "label": "Toko Buka",
        "default": statuslib.DEFAULT_OPEN_LABEL,
        "get": statuslib.get_open_label,
        "set": statuslib.set_open_label,
    },
    "close": {
        "label": "Toko Tutup",
        "default": statuslib.DEFAULT_CLOSE_LABEL,
        "get": statuslib.get_close_label,
        "set": statuslib.set_close_label,
    },
}


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@store_status_bp.route("/store-status-editor/save", methods=["POST"])
def save_status_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in _KINDS:
        return jsonify({"ok": False, "error": "Jenis label tidak dikenal."}), 400
    text = payload.get("text")
    if text is None or not str(text).strip():
        return jsonify({"ok": False, "error": "Label tidak boleh kosong."}), 400
    _KINDS[kind]["set"](text)
    return jsonify({"ok": True})


@store_status_bp.route("/store-status-editor/reset", methods=["POST"])
def reset_status_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in _KINDS:
        return jsonify({"ok": False, "error": "Jenis label tidak dikenal."}), 400
    _KINDS[kind]["set"]("")
    return jsonify({"ok": True, "text": _KINDS[kind]["get"]()})


@store_status_bp.route("/store-status-editor")
def page_store_status():
    g = _guard()
    if g:
        return g
    from admin import render_page

    sections = []
    for kind, spec in _KINDS.items():
        sections.append({
            "kind": kind,
            "label": spec["label"],
            "text": spec["get"](),
            "default": spec["default"],
        })
    sections_json = json.dumps(sections)

    content = """
<div class="page-header">
  <div class="page-title">Status Toko <small>Label voice channel saat Buka &amp; Tutup</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Label ini jadi nama voice channel status toko, diganti otomatis sesuai jam buka/tutup.
    Perubahan dipakai pada sinkronisasi status berikutnya. Maksimal 100 karakter (batas nama channel Discord).
  </div>
  <div id="sections"></div>
</div></div>

<script>
var SECTIONS = SECTIONS_JSON;

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function setStatus(kind, msg, ok){
  document.getElementById('st_'+kind).innerHTML =
    '<span style="color:var(--'+(ok?'success':'warning')+')">'+(ok?'✓ ':'● ')+msg+'</span>';
}
function updatePreview(i){
  var s = SECTIONS[i];
  document.getElementById('pv_'+s.kind).innerHTML =
    '🔊 ' + esc(document.getElementById('txt_'+s.kind).value);
}

function build(){
  var html = '';
  SECTIONS.forEach(function(s, i){
    html += '<div class="card" style="margin-bottom:1rem;border:1px solid var(--border);"><div class="card-body">'
      + '<div style="font-weight:700;margin-bottom:.2rem;">'+esc(s.label)+'</div>'
      + '<div style="font-size:.78rem;color:var(--muted);margin-bottom:.7rem;">Default: <code>'+esc(s.default)+'</code></div>'
      + '<div class="form-group"><input type="text" id="txt_'+s.kind+'" maxlength="100" style="width:100%;" '
      + 'oninput="updatePreview('+i+');setStatus(\\''+s.kind+'\\',\\'Belum disimpan\\',false);"></div>'
      + '<button class="btn btn-primary btn-sm" onclick="saveSec('+i+')">💾 Simpan</button> '
      + '<button class="btn btn-ghost btn-sm" onclick="resetSec('+i+')">↺ Default</button>'
      + '<span id="st_'+s.kind+'" style="margin-left:.6rem;font-size:.85rem;"></span>'
      + '<div style="margin-top:.9rem;border-left:4px solid var(--accent);background:var(--surface3);border-radius:6px;padding:.7rem .9rem;">'
      + '<div id="pv_'+s.kind+'" style="color:var(--text);font-weight:600;"></div></div>'
      + '</div></div>';
  });
  document.getElementById('sections').innerHTML = html;
  SECTIONS.forEach(function(s, i){
    document.getElementById('txt_'+s.kind).value = s.text;
    updatePreview(i);
  });
}

function saveSec(i){
  var s = SECTIONS[i];
  fetch('/store-status-editor/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({kind:s.kind, text:document.getElementById('txt_'+s.kind).value})})
    .then(function(r){return r.json();}).then(function(d){
      setStatus(s.kind, d.ok ? 'Tersimpan.' : (d.error||'Gagal menyimpan'), !!d.ok);
    });
}
function resetSec(i){
  var s = SECTIONS[i];
  if(!confirm('Kembalikan label "'+s.label+'" ke teks default?')) return;
  fetch('/store-status-editor/reset',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({kind:s.kind})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){
        document.getElementById('txt_'+s.kind).value = d.text;
        updatePreview(i);
        setStatus(s.kind, 'Dikembalikan ke default.', true);
      } else { setStatus(s.kind, d.error||'Gagal reset', false); }
    });
}
build();
</script>"""
    content = content.replace("SECTIONS_JSON", sections_json)
    return render_page(content)
