"""admin_top_spender.py - Editor teks papan Top Spender (cogs/top_spender.py).

Blueprint terpisah (pola sama dgn admin_afk.py). Mengubah prosa papan leaderboard
(judul/deskripsi/benefit/footer/state kosong). Daftar peringkat & nominal tetap
dihitung cog. Cog membaca teks lewat utils.top_spender_text, jadi perubahan dipakai
saat papan di-refresh berikutnya (otomatis tiap ada transaksi).

  - /topspender-editor          : form per jenis teks + pratinjau langsung
  - /topspender-editor/save     : simpan teks (POST JSON {kind,text})
  - /topspender-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
import json

from flask import Blueprint, request, session, redirect, jsonify

from utils import top_spender_text as tstext

top_spender_bp = Blueprint("top_spender_bp", __name__)

# Nilai contoh per placeholder untuk pratinjau langsung.
_SAMPLE = {"store": "Cellyn Store", "month": "Juni 2026"}


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@top_spender_bp.route("/topspender-editor/save", methods=["POST"])
def save_top_spender_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in tstext.TOP_SPENDER_SPECS:
        return jsonify({"ok": False, "error": "Jenis teks tidak dikenal."}), 400
    text = payload.get("text")
    if text is None or not str(text).strip():
        return jsonify({"ok": False, "error": "Teks tidak boleh kosong."}), 400
    tstext.save_text(kind, text=text)
    return jsonify({"ok": True})


@top_spender_bp.route("/topspender-editor/reset", methods=["POST"])
def reset_top_spender_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in tstext.TOP_SPENDER_SPECS:
        return jsonify({"ok": False, "error": "Jenis teks tidak dikenal."}), 400
    tstext.save_text(kind, text="")
    return jsonify({"ok": True, "text": tstext.load_text(kind)})


@top_spender_bp.route("/topspender-editor")
def page_top_spender():
    g = _guard()
    if g:
        return g
    from admin import render_page

    sections = []
    for kind, spec in tstext.TOP_SPENDER_SPECS.items():
        sections.append({
            "kind": kind,
            "label": spec["label"],
            "text": tstext.load_text(kind),
            "placeholders": list(spec["placeholders"]),
            "sample": {k: v for k, v in _SAMPLE.items() if ("{" + k + "}") in spec["default"]},
        })
    sections_json = json.dumps(sections)

    content = """
<div class="page-header">
  <div class="page-title">Papan Top Spender <small>Teks leaderboard pelanggan</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Teks papan Top Spender. Daftar peringkat &amp; nominal dihitung otomatis dari transaksi.
    Perubahan dipakai saat papan di-refresh berikutnya. Mendukung <b>**bold**</b> ala Discord.
  </div>
  <div id="sections"></div>
</div></div>

<script>
var SECTIONS = SECTIONS_JSON;

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function render(tpl, sample){
  var out = esc(tpl);
  Object.keys(sample||{}).forEach(function(k){
    out = out.split("{"+k+"}").join(esc(String(sample[k])));
  });
  return out.replace(/\\*\\*([^*]+)\\*\\*/g, "<b>$1</b>").replace(/\\n/g, "<br>");
}
function setStatus(kind, msg, ok){
  document.getElementById('st_'+kind).innerHTML =
    '<span style="color:var(--'+(ok?'success':'warning')+')">'+(ok?'✓ ':'● ')+msg+'</span>';
}
function updatePreview(i){
  var s = SECTIONS[i];
  document.getElementById('pv_'+s.kind).innerHTML =
    render(document.getElementById('txt_'+s.kind).value, s.sample);
}

function build(){
  var html = '';
  SECTIONS.forEach(function(s, i){
    var chips = s.placeholders.length
      ? 'Placeholder: ' + s.placeholders.map(function(p){ return '<code>'+esc(p)+'</code>'; }).join(' ')
      : '<span style="color:var(--muted)">Tanpa placeholder</span>';
    html += '<div class="card" style="margin-bottom:1rem;border:1px solid var(--border);"><div class="card-body">'
      + '<div style="font-weight:700;margin-bottom:.2rem;">'+esc(s.label)+'</div>'
      + '<div style="font-size:.78rem;color:var(--muted);margin-bottom:.7rem;">'+chips+'</div>'
      + '<div class="form-group"><textarea id="txt_'+s.kind+'" rows="3" style="width:100%;" '
      + 'oninput="updatePreview('+i+');setStatus(\\''+s.kind+'\\',\\'Belum disimpan\\',false);"></textarea></div>'
      + '<button class="btn btn-primary btn-sm" onclick="saveSec('+i+')">💾 Simpan</button> '
      + '<button class="btn btn-ghost btn-sm" onclick="resetSec('+i+')">↺ Default</button>'
      + '<span id="st_'+s.kind+'" style="margin-left:.6rem;font-size:.85rem;"></span>'
      + '<div style="margin-top:.9rem;border-left:4px solid var(--accent);background:var(--surface3);border-radius:6px;padding:.7rem .9rem;">'
      + '<div id="pv_'+s.kind+'" style="color:var(--text);"></div></div>'
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
  fetch('/topspender-editor/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({kind:s.kind, text:document.getElementById('txt_'+s.kind).value})})
    .then(function(r){return r.json();}).then(function(d){
      setStatus(s.kind, d.ok ? 'Tersimpan.' : (d.error||'Gagal menyimpan'), !!d.ok);
    });
}
function resetSec(i){
  var s = SECTIONS[i];
  if(!confirm('Kembalikan teks "'+s.label+'" ke default?')) return;
  fetch('/topspender-editor/reset',{method:'POST',headers:{'Content-Type':'application/json'},
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
