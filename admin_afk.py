"""admin_afk.py - Editor teks pesan sistem AFK (cogs/afk.py).

Blueprint terpisah (pola sama dgn admin_welcome.py bagian teks tunggal). Mengubah
pesan yang dikirim bot saat member set AFK, kembali dari AFK, di-mention saat AFK,
atau jalankan !afk padahal sudah AFK. Cog `cogs/afk.py` membaca teks lewat
utils.afk.render_text(), jadi perubahan di sini langsung dipakai berikutnya.

  - /afk-editor          : form per jenis pesan + pratinjau langsung
  - /afk-editor/save     : simpan teks (POST JSON {kind,text})
  - /afk-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
import json

from flask import Blueprint, request, session, redirect, jsonify

from utils import afk as afklib

afk_bp = Blueprint("afk_bp", __name__)

# Nilai contoh per jenis pesan untuk pratinjau langsung di panel.
_SAMPLES = {
    "set": {"member": "@Andi", "reason": "lagi makan"},
    "back": {"member": "@Andi"},
    "mention": {"name": "Andi", "reason": "lagi makan", "durasi": "5 menit lalu"},
    "already": {"member": "@Andi"},
}


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@afk_bp.route("/afk-editor/save", methods=["POST"])
def save_afk_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in afklib.AFK_SPECS:
        return jsonify({"ok": False, "error": "Jenis pesan tidak dikenal."}), 400
    text = payload.get("text")
    if text is None or not str(text).strip():
        return jsonify({"ok": False, "error": "Teks tidak boleh kosong."}), 400
    afklib.save_text(kind, text=text)
    return jsonify({"ok": True})


@afk_bp.route("/afk-editor/reset", methods=["POST"])
def reset_afk_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in afklib.AFK_SPECS:
        return jsonify({"ok": False, "error": "Jenis pesan tidak dikenal."}), 400
    afklib.save_text(kind, text="")
    return jsonify({"ok": True, "text": afklib.load_text(kind)})


@afk_bp.route("/afk-editor")
def page_afk():
    g = _guard()
    if g:
        return g
    from admin import render_page

    sections = []
    for kind, spec in afklib.AFK_SPECS.items():
        sections.append({
            "kind": kind,
            "label": spec["label"],
            "text": afklib.load_text(kind),
            "placeholders": list(spec["placeholders"]),
            "sample": _SAMPLES.get(kind, {}),
        })
    sections_json = json.dumps(sections)

    content = """
<div class="page-header">
  <div class="page-title">Pesan AFK <small>Set, Kembali, Notif Mention &amp; Sudah AFK</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Teks ini dikirim bot saat sistem AFK aktif. Perubahan langsung dipakai berikutnya.
    Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia di tiap kotak.
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
    var chips = s.placeholders.map(function(p){ return '<code>'+esc(p)+'</code>'; }).join(' ');
    html += '<div class="card" style="margin-bottom:1rem;border:1px solid var(--border);"><div class="card-body">'
      + '<div style="font-weight:700;margin-bottom:.2rem;">'+esc(s.label)+'</div>'
      + '<div style="font-size:.78rem;color:var(--muted);margin-bottom:.7rem;">Placeholder: '+chips+'</div>'
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
  fetch('/afk-editor/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({kind:s.kind, text:document.getElementById('txt_'+s.kind).value})})
    .then(function(r){return r.json();}).then(function(d){
      setStatus(s.kind, d.ok ? 'Tersimpan.' : (d.error||'Gagal menyimpan'), !!d.ok);
    });
}
function resetSec(i){
  var s = SECTIONS[i];
  if(!confirm('Kembalikan pesan "'+s.label+'" ke teks default?')) return;
  fetch('/afk-editor/reset',{method:'POST',headers:{'Content-Type':'application/json'},
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
