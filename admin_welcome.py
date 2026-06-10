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
    "general_greeting": {"member": "@Andi", "store": _STORE_NAME},
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


@welcome_bp.route("/welcome-editor/save-text", methods=["POST"])
def save_text_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in welcomelib.TEXT_SPECS:
        return jsonify({"ok": False, "error": "Jenis pesan tidak dikenal."}), 400
    text = payload.get("text")
    if text is None or not str(text).strip():
        return jsonify({"ok": False, "error": "Teks tidak boleh kosong."}), 400
    welcomelib.save_text(kind, text=text)
    return jsonify({"ok": True})


@welcome_bp.route("/welcome-editor/reset-text", methods=["POST"])
def reset_text_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in welcomelib.TEXT_SPECS:
        return jsonify({"ok": False, "error": "Jenis pesan tidak dikenal."}), 400
    welcomelib.save_text(kind, text="")
    return jsonify({"ok": True, "text": welcomelib.load_text(kind)})


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

    text_sections = []
    for kind, spec in welcomelib.TEXT_SPECS.items():
        text_sections.append({
            "kind": kind,
            "label": spec["label"],
            "text": welcomelib.load_text(kind),
            "placeholders": list(spec["placeholders"]),
            "sample": _SAMPLES.get(kind, {}),
        })
    text_sections_json = json.dumps(text_sections)

    content = """
<div class="page-header">
  <div class="page-title">Pesan Member <small>Welcome, Boost, Leave &amp; Sapaan Publik</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Channel &amp; gambar welcome/boost diatur dari Discord (<code>/setwelcome</code>). Halaman ini mengubah <b>teksnya</b>.
    Perubahan langsung dipakai pada event berikutnya. Mendukung <b>**bold**</b> ala Discord.
  </div>
  <div id="sections"></div>
  <div id="textSections"></div>
</div></div>

<script>
var SECTIONS = SECTIONS_JSON;
var TEXT_SECTIONS = TEXT_SECTIONS_JSON;

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

function buildText(){
  var html = '';
  TEXT_SECTIONS.forEach(function(s, i){
    var chips = s.placeholders.map(function(p){ return '<code>'+esc(p)+'</code>'; }).join(' ');
    html += '<div class="card" style="margin-bottom:1rem;border:1px solid var(--border);"><div class="card-body">'
      + '<div style="font-weight:700;margin-bottom:.2rem;">'+esc(s.label)+'</div>'
      + '<div style="font-size:.78rem;color:var(--muted);margin-bottom:.7rem;">Pesan teks biasa (bukan embed). Placeholder: '+chips+'</div>'
      + '<div class="form-group"><textarea id="txt_'+s.kind+'" rows="3" style="width:100%;" '
      + 'oninput="updateText('+i+');setStatus(\\''+s.kind+'\\',\\'Belum disimpan\\',false);"></textarea></div>'
      + '<button class="btn btn-primary btn-sm" onclick="saveText('+i+')">💾 Simpan</button> '
      + '<button class="btn btn-ghost btn-sm" onclick="resetText('+i+')">↺ Default</button>'
      + '<span id="st_'+s.kind+'" style="margin-left:.6rem;font-size:.85rem;"></span>'
      + '<div style="margin-top:.9rem;border-left:4px solid var(--accent);background:var(--surface3);border-radius:6px;padding:.7rem .9rem;">'
      + '<div id="pvtxt_'+s.kind+'" style="color:var(--text);"></div></div>'
      + '</div></div>';
  });
  document.getElementById('textSections').innerHTML = html;
  TEXT_SECTIONS.forEach(function(s, i){
    document.getElementById('txt_'+s.kind).value = s.text;
    updateText(i);
  });
}
function updateText(i){
  var s = TEXT_SECTIONS[i];
  document.getElementById('pvtxt_'+s.kind).innerHTML =
    render(document.getElementById('txt_'+s.kind).value, s.sample);
}
function saveText(i){
  var s = TEXT_SECTIONS[i];
  fetch('/welcome-editor/save-text',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({kind:s.kind, text:document.getElementById('txt_'+s.kind).value})})
    .then(function(r){return r.json();}).then(function(d){
      setStatus(s.kind, d.ok ? 'Tersimpan.' : (d.error||'Gagal menyimpan'), !!d.ok);
    });
}
function resetText(i){
  var s = TEXT_SECTIONS[i];
  if(!confirm('Kembalikan pesan "'+s.label+'" ke teks default?')) return;
  fetch('/welcome-editor/reset-text',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({kind:s.kind})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){
        document.getElementById('txt_'+s.kind).value = d.text;
        updateText(i);
        setStatus(s.kind, 'Dikembalikan ke default.', true);
      } else { setStatus(s.kind, d.error||'Gagal reset', false); }
    });
}
build();
buildText();
</script>"""
    content = content.replace("TEXT_SECTIONS_JSON", text_sections_json)
    content = content.replace("SECTIONS_JSON", sections_json)
    return render_page(content)



# ── DM Sambutan (embed multi-field + thumbnail + banner di atas) ─────────────────

@welcome_bp.route("/dm-editor/save", methods=["POST"])
def save_dm_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    title = payload.get("title")
    desc = payload.get("desc")
    if (title is None or not str(title).strip()) and (desc is None or not str(desc).strip()):
        return jsonify({"ok": False, "error": "Judul & isi tidak boleh kosong keduanya."}), 400
    fields = payload.get("fields")
    if fields is not None and not isinstance(fields, list):
        fields = None
    welcomelib.save_dm_config(
        title=title,
        desc=desc,
        footer=payload.get("footer"),
        thumbnail=payload.get("thumbnail"),
        banner=payload.get("banner"),
        fields=fields,
    )
    return jsonify({"ok": True})


@welcome_bp.route("/dm-editor/reset", methods=["POST"])
def reset_dm_route():
    g = _guard()
    if g:
        return g
    welcomelib.reset_dm_config()
    return jsonify({"ok": True, "config": welcomelib.load_dm_config()})


@welcome_bp.route("/dm-editor")
def page_dm():
    g = _guard()
    if g:
        return g
    from admin import render_page

    cfg = welcomelib.load_dm_config()
    cfg["store"] = _STORE_NAME
    cfg_json = json.dumps(cfg)

    content = """
<div class="page-header">
  <div class="page-title">DM Sambutan <small>Pesan privat ke member baru (embed + banner)</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    DM ini dikirim otomatis ke member baru. Placeholder: <code>{member}</code>, <code>{store}</code>.
    Mendukung <b>**bold**</b> ala Discord. Banner (gambar lebar) tampil di <b>ATAS</b> teks,
    thumbnail (gambar kecil) di pojok kanan atas. Kosongkan banner kalau tak mau pakai.
  </div>

  <div class="form-group"><label>Judul</label>
    <input type="text" id="dmTitle" maxlength="256" style="width:100%;" oninput="upd();dirty();"></div>
  <div class="form-group"><label>Isi / sambutan</label>
    <textarea id="dmDesc" rows="4" style="width:100%;" oninput="upd();dirty();"></textarea></div>

  <div style="display:flex;gap:1rem;flex-wrap:wrap;">
    <div class="form-group" style="flex:1 1 320px;"><label>URL Banner (di atas, gambar lebar)</label>
      <input type="text" id="dmBanner" placeholder="https://... (kosongkan = tanpa banner)" style="width:100%;" oninput="upd();dirty();"></div>
    <div class="form-group" style="flex:1 1 320px;"><label>URL Thumbnail (pojok kanan atas)</label>
      <input type="text" id="dmThumb" placeholder="https://..." style="width:100%;" oninput="upd();dirty();"></div>
  </div>

  <div class="form-group"><label>Field (kotak info, urut dari atas ke bawah)</label>
    <div id="fieldList"></div>
    <button class="btn btn-ghost btn-sm" onclick="addField()">+ Tambah field</button>
  </div>

  <div class="form-group"><label>Footer</label>
    <input type="text" id="dmFooter" maxlength="2048" style="width:100%;" oninput="upd();dirty();"></div>

  <button class="btn btn-primary btn-sm" onclick="saveDm()">💾 Simpan</button>
  <button class="btn btn-ghost btn-sm" onclick="resetDm()">↺ Kembalikan default</button>
  <span id="status" style="margin-left:.6rem;font-size:.85rem;"></span>

  <div style="margin-top:1.2rem;">
    <label style="font-size:.8rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;">Pratinjau DM</label>
    <div id="pvWrap" style="max-width:460px;margin-top:.4rem;">
      <img id="pvBanner" style="width:100%;border-radius:8px 8px 0 0;display:none;" alt="banner">
      <div style="border-left:4px solid var(--accent);background:var(--surface3);border-radius:6px;padding:.85rem 1rem;position:relative;">
        <img id="pvThumb" style="position:absolute;top:.85rem;right:1rem;width:64px;height:64px;border-radius:8px;object-fit:cover;display:none;" alt="thumb">
        <div id="pvTitle" style="font-weight:700;margin-bottom:.4rem;padding-right:72px;"></div>
        <div id="pvDesc" style="margin-bottom:.5rem;"></div>
        <div id="pvFields"></div>
        <div id="pvFooter" style="font-size:.75rem;color:var(--muted);margin-top:.6rem;"></div>
      </div>
    </div>
  </div>
</div></div>

<script>
var CFG = CFG_JSON;
var SAMPLE = {member:"Andi", store:CFG.store || "Store"};
var FIELDS = (CFG.fields || []).map(function(f){ return {name:f.name||"", value:f.value||""}; });

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function render(tpl){
  var out = esc(tpl);
  Object.keys(SAMPLE).forEach(function(k){ out = out.split("{"+k+"}").join(esc(String(SAMPLE[k]))); });
  return out.replace(/\\*\\*([^*]+)\\*\\*/g, "<b>$1</b>").replace(/\n/g, "<br>");
}
function setStatus(msg, ok){
  document.getElementById('status').innerHTML =
    '<span style="color:var(--'+(ok?'success':'warning')+')">'+(ok?'✓ ':'● ')+msg+'</span>';
}
function dirty(){ setStatus('Perubahan belum disimpan', false); }

function renderFieldEditor(){
  var html = '';
  FIELDS.forEach(function(f, i){
    html += '<div style="border:1px solid var(--border);border-radius:8px;padding:.6rem;margin-bottom:.5rem;">'
      + '<input type="text" value="'+esc(f.name)+'" placeholder="Judul field" style="width:100%;margin-bottom:.4rem;" '
      + 'oninput="FIELDS['+i+'].name=this.value;upd();dirty();">'
      + '<textarea rows="3" placeholder="Isi field" style="width:100%;" '
      + 'oninput="FIELDS['+i+'].value=this.value;upd();dirty();">'+esc(f.value)+'</textarea>'
      + '<div style="text-align:right;margin-top:.3rem;">'
      + '<button class="btn btn-ghost btn-sm" onclick="moveField('+i+',-1)">↑</button> '
      + '<button class="btn btn-ghost btn-sm" onclick="moveField('+i+',1)">↓</button> '
      + '<button class="btn btn-ghost btn-sm" onclick="delField('+i+')">🗑️</button></div>'
      + '</div>';
  });
  document.getElementById('fieldList').innerHTML = html;
}
function addField(){ FIELDS.push({name:"", value:""}); renderFieldEditor(); upd(); dirty(); }
function delField(i){ FIELDS.splice(i,1); renderFieldEditor(); upd(); dirty(); }
function moveField(i, d){
  var j = i + d;
  if(j < 0 || j >= FIELDS.length) return;
  var tmp = FIELDS[i]; FIELDS[i] = FIELDS[j]; FIELDS[j] = tmp;
  renderFieldEditor(); upd(); dirty();
}

function upd(){
  var banner = document.getElementById('dmBanner').value.trim();
  var thumb = document.getElementById('dmThumb').value.trim();
  var b = document.getElementById('pvBanner'), t = document.getElementById('pvThumb');
  if(banner){ b.src = banner; b.style.display='block'; } else { b.style.display='none'; }
  if(thumb){ t.src = thumb; t.style.display='block'; } else { t.style.display='none'; }
  document.getElementById('pvTitle').innerHTML = render(document.getElementById('dmTitle').value);
  document.getElementById('pvDesc').innerHTML = render(document.getElementById('dmDesc').value);
  document.getElementById('pvFooter').innerHTML = render(document.getElementById('dmFooter').value);
  var fh = '';
  FIELDS.forEach(function(f){
    if(!f.name && !f.value) return;
    fh += '<div style="margin-bottom:.5rem;"><div style="font-weight:600;">'+render(f.name)+'</div>'
       + '<div style="color:var(--text);">'+render(f.value)+'</div></div>';
  });
  document.getElementById('pvFields').innerHTML = fh;
}

function saveDm(){
  fetch('/dm-editor/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({title:document.getElementById('dmTitle').value,
      desc:document.getElementById('dmDesc').value,
      footer:document.getElementById('dmFooter').value,
      thumbnail:document.getElementById('dmThumb').value,
      banner:document.getElementById('dmBanner').value,
      fields:FIELDS})})
    .then(function(r){return r.json();}).then(function(d){
      setStatus(d.ok ? 'Tersimpan.' : (d.error||'Gagal menyimpan'), !!d.ok);
    });
}
function resetDm(){
  if(!confirm('Kembalikan DM sambutan ke teks & gambar default?')) return;
  fetch('/dm-editor/reset',{method:'POST'})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ CFG = d.config; CFG.store = SAMPLE.store; loadInto(); setStatus('Dikembalikan ke default.', true); }
      else { setStatus('Gagal reset', false); }
    });
}

function loadInto(){
  document.getElementById('dmTitle').value = CFG.title || "";
  document.getElementById('dmDesc').value = CFG.desc || "";
  document.getElementById('dmFooter').value = CFG.footer || "";
  document.getElementById('dmThumb').value = CFG.thumbnail || "";
  document.getElementById('dmBanner').value = CFG.banner || "";
  FIELDS = (CFG.fields || []).map(function(f){ return {name:f.name||"", value:f.value||""}; });
  renderFieldEditor();
  upd();
}
loadInto();
</script>"""
    content = content.replace("CFG_JSON", cfg_json)
    return render_page(content)
