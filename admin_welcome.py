"""admin_welcome.py - Editor teks pesan event member (welcome / boost / leave).

Blueprint terpisah (pola sama dgn admin_faq.py / admin_sticky.py). Mengubah judul
& isi embed yang dikirim saat member join, nge-boost server, atau keluar. Cog
`cogs/welcome.py` membaca teks lewat utils.welcome.render_*(), jadi perubahan di
sini langsung dipakai pada event berikutnya.

  - /welcome-editor              : form per jenis pesan + pratinjau langsung
  - /welcome-editor/save         : simpan template (POST JSON {kind,title,desc})
  - /welcome-editor/reset        : kembalikan satu jenis ke default (POST JSON {kind})

Catatan: channel & gambar welcome/boost tetap diatur dari Discord (/setwelcome)
karena butuh izin bot. Halaman ini hanya mengubah teksnya.
"""
import json

from flask import Blueprint, request, session, redirect, jsonify

from utils import welcome as welcomelib

try:
    from utils.config import STORE_NAME as _STORE_NAME
except Exception:
    _STORE_NAME = "Store"

welcome_bp = Blueprint("welcome_bp", __name__)

# Nilai contoh per jenis pesan untuk pratinjau langsung di panel.
_SAMPLES = {
    "welcome": {"member": "Andi", "store": _STORE_NAME, "count": "123"},
    "boost": {"member": "@Andi", "store": _STORE_NAME},
    "leave": {"member": "Andi", "store": _STORE_NAME, "durasi": "3 bulan"},
}


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@welcome_bp.route("/welcome-editor/save", methods=["POST"])
def save_welcome_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in welcomelib.MSG_SPECS:
        return jsonify({"ok": False, "error": "Jenis pesan tidak dikenal."}), 400
    title = payload.get("title")
    desc = payload.get("desc")
    if (title is None or not str(title).strip()) and (desc is None or not str(desc).strip()):
        return jsonify({"ok": False, "error": "Judul & isi tidak boleh kosong keduanya."}), 400
    welcomelib.save_texts(kind, title=title, desc=desc)
    return jsonify({"ok": True})


@welcome_bp.route("/welcome-editor/reset", methods=["POST"])
def reset_welcome_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in welcomelib.MSG_SPECS:
        return jsonify({"ok": False, "error": "Jenis pesan tidak dikenal."}), 400
    welcomelib.save_texts(kind, title="", desc="")
    title, desc = welcomelib.load_texts(kind)
    return jsonify({"ok": True, "title": title, "desc": desc})


@welcome_bp.route("/welcome-editor")
def page_welcome():
    g = _guard()
    if g:
        return g
    from admin import render_page

    sections = []
    for kind, spec in welcomelib.MSG_SPECS.items():
        title, desc = welcomelib.load_texts(kind)
        sections.append({
            "kind": kind,
            "label": spec["label"],
            "title": title,
            "desc": desc,
            "placeholders": list(spec["placeholders"]),
            "sample": _SAMPLES.get(kind, {}),
        })
    sections_json = json.dumps(sections)

    content = """
<div class="page-header">
  <div class="page-title">Pesan Member <small>Teks Welcome, Boost &amp; Leave</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Channel &amp; gambar welcome/boost diatur dari Discord (<code>/setwelcome</code>). Halaman ini mengubah <b>teksnya</b>.
    Perubahan langsung dipakai pada event berikutnya. Mendukung <b>**bold**</b> ala Discord.
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
  var t = document.getElementById('title_'+s.kind).value;
  var d = document.getElementById('desc_'+s.kind).value;
  document.getElementById('pvt_'+s.kind).innerHTML = render(t, s.sample);
  document.getElementById('pvd_'+s.kind).innerHTML = render(d, s.sample);
}

function build(){
  var html = '';
  SECTIONS.forEach(function(s, i){
    var chips = s.placeholders.map(function(p){ return '<code>'+esc(p)+'</code>'; }).join(' ');
    html += '<div class="card" style="margin-bottom:1rem;border:1px solid var(--border);"><div class="card-body">'
      + '<div style="font-weight:700;margin-bottom:.2rem;">'+esc(s.label)+'</div>'
      + '<div style="font-size:.78rem;color:var(--muted);margin-bottom:.7rem;">Placeholder: '+chips+'</div>'
      + '<div class="form-group"><label>Judul</label>'
      + '<input type="text" id="title_'+s.kind+'" maxlength="256" style="width:100%;" '
      + 'oninput="updatePreview('+i+');setStatus(\\''+s.kind+'\\',\\'Belum disimpan\\',false);"></div>'
      + '<div class="form-group"><label>Isi</label>'
      + '<textarea id="desc_'+s.kind+'" rows="5" style="width:100%;" '
      + 'oninput="updatePreview('+i+');setStatus(\\''+s.kind+'\\',\\'Belum disimpan\\',false);"></textarea></div>'
      + '<button class="btn btn-primary btn-sm" onclick="saveSec('+i+')">💾 Simpan</button> '
      + '<button class="btn btn-ghost btn-sm" onclick="resetSec('+i+')">↺ Default</button>'
      + '<span id="st_'+s.kind+'" style="margin-left:.6rem;font-size:.85rem;"></span>'
      + '<div style="margin-top:.9rem;border-left:4px solid var(--accent);background:var(--surface3);border-radius:6px;padding:.7rem .9rem;">'
      + '<div id="pvt_'+s.kind+'" style="font-weight:700;margin-bottom:.35rem;"></div>'
      + '<div id="pvd_'+s.kind+'" style="color:var(--text);"></div></div>'
      + '</div></div>';
  });
  document.getElementById('sections').innerHTML = html;
  SECTIONS.forEach(function(s, i){
    document.getElementById('title_'+s.kind).value = s.title;
    document.getElementById('desc_'+s.kind).value = s.desc;
    updatePreview(i);
  });
}

function saveSec(i){
  var s = SECTIONS[i];
  fetch('/welcome-editor/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({kind:s.kind, title:document.getElementById('title_'+s.kind).value,
                         desc:document.getElementById('desc_'+s.kind).value})})
    .then(function(r){return r.json();}).then(function(d){
      setStatus(s.kind, d.ok ? 'Tersimpan.' : (d.error||'Gagal menyimpan'), !!d.ok);
    });
}
function resetSec(i){
  var s = SECTIONS[i];
  if(!confirm('Kembalikan pesan "'+s.label+'" ke teks default?')) return;
  fetch('/welcome-editor/reset',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({kind:s.kind})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){
        document.getElementById('title_'+s.kind).value = d.title;
        document.getElementById('desc_'+s.kind).value = d.desc;
        updatePreview(i);
        setStatus(s.kind, 'Dikembalikan ke default.', true);
      } else { setStatus(s.kind, d.error||'Gagal reset', false); }
    });
}
build();
</script>"""
    content = content.replace("SECTIONS_JSON", sections_json)
    return render_page(content)
