"""admin_welcome_theme.py - Editor Kartu Welcome untuk Admin Panel.

Blueprint terpisah (pola sama dgn admin_achievement_theme.py). Memberi editor
visual untuk kartu sambutan member baru (render_welcome_card di cogs/profile.py):
  - /welcome-theme            : halaman editor (drag-drop posisi + warna/font/teks)
  - /welcome-theme/preview.png: render kartu contoh dgn tema saat ini
  - /welcome-theme/save       : simpan tema (POST JSON)
  - /welcome-theme/font       : upload file font .ttf/.otf (POST file)
  - /welcome-theme/bg         : upload background (POST file)
  - /welcome-theme/bg/delete  : hapus background
  - /welcome-theme/reset      : kembalikan ke default

render_page di-import lazily di dalam view (hindari circular import).
"""
import os
import json

from flask import Blueprint, request, session, redirect, Response, jsonify

from utils import welcome_theme as wtheme

welcome_theme_bp = Blueprint("welcome_theme_bp", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ALLOWED_FONT_EXTS = (".ttf", ".otf")
ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
WELCOME_BG_BASE = "welcomecardbg"


def _bg_path():
    for ext in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, WELCOME_BG_BASE + ext)
        if os.path.exists(p):
            return p
    return None


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@welcome_theme_bp.route("/welcome-theme/preview.png")
def preview_png():
    g = _guard()
    if g:
        return g
    raw = request.args.get("t")
    theme = wtheme.merge_theme(raw) if raw else wtheme.load_theme()
    name = (request.args.get("name") or "").strip() or "ContohMember"
    try:
        from cogs.profile import render_welcome_card
        buf = render_welcome_card(name, None, member_count=123,
                                  theme=theme, bg_path=_bg_path())
        return Response(buf.getvalue(), mimetype="image/png")
    except Exception as e:
        png_1x1 = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                   b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
                   b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        return Response(png_1x1, mimetype="image/png",
                        headers={"X-Render-Error": str(e)[:200]})


@welcome_theme_bp.route("/welcome-theme/save", methods=["POST"])
def save_theme_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    if "font_file" not in payload:
        payload["font_file"] = wtheme.load_theme().get("font_file")
    theme = wtheme.save_theme(payload)
    return jsonify({"ok": True, "theme": theme})


@welcome_theme_bp.route("/welcome-theme/reset", methods=["POST"])
def reset_theme_route():
    g = _guard()
    if g:
        return g
    theme = wtheme.save_theme(wtheme.default_theme())
    return jsonify({"ok": True, "theme": theme})


@welcome_theme_bp.route("/welcome-theme/font", methods=["POST"])
def upload_font():
    g = _guard()
    if g:
        return g
    f = request.files.get("font")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "Tidak ada file."}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_FONT_EXTS:
        return jsonify({"ok": False, "error": "Format harus .ttf atau .otf."}), 400
    os.makedirs(DATA_DIR, exist_ok=True)
    fname = "welcome_font" + ext
    for e in ALLOWED_FONT_EXTS:
        old = os.path.join(DATA_DIR, "welcome_font" + e)
        if os.path.exists(old) and e != ext:
            try:
                os.remove(old)
            except Exception:
                pass
    f.save(os.path.join(DATA_DIR, fname))
    theme = wtheme.load_theme()
    theme["font_file"] = fname
    wtheme.save_theme(theme)
    return jsonify({"ok": True, "font_file": fname})


@welcome_theme_bp.route("/welcome-theme/bg", methods=["POST"])
def upload_bg():
    g = _guard()
    if g:
        return g
    f = request.files.get("bg")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "Tidak ada file."}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return jsonify({"ok": False, "error": "Format harus PNG/JPG/WEBP."}), 400
    os.makedirs(DATA_DIR, exist_ok=True)
    for e in ALLOWED_IMAGE_EXTS:
        old = os.path.join(DATA_DIR, WELCOME_BG_BASE + e)
        if os.path.exists(old):
            try:
                os.remove(old)
            except Exception:
                pass
    f.save(os.path.join(DATA_DIR, WELCOME_BG_BASE + ext))
    return jsonify({"ok": True, "has_bg": True})


@welcome_theme_bp.route("/welcome-theme/bg/delete", methods=["POST"])
def delete_bg():
    g = _guard()
    if g:
        return g
    removed = False
    for e in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, WELCOME_BG_BASE + e)
        if os.path.exists(p):
            try:
                os.remove(p)
                removed = True
            except Exception:
                pass
    return jsonify({"ok": True, "removed": removed, "has_bg": False})


@welcome_theme_bp.route("/welcome-theme")
def page_theme():
    g = _guard()
    if g:
        return g
    from admin import render_page

    theme = wtheme.load_theme()
    theme_json = json.dumps(theme)
    labels_json = json.dumps(dict(wtheme.ELEMENT_LABELS))
    order_json = json.dumps([k for k, _ in wtheme.ELEMENT_LABELS])
    cur_font = theme.get("font_file") or "(default sistem)"
    has_bg_json = json.dumps(_bg_path() is not None)
    enabled_attr = "checked" if theme.get("enabled") else ""

    content = f"""
<style>
.thm-tabs{{display:flex;gap:.25rem;margin-bottom:1rem;border-bottom:1px solid var(--border);flex-wrap:wrap;}}
.thm-tab{{appearance:none;background:none;border:none;border-bottom:2px solid transparent;color:var(--muted2);font:inherit;font-size:.82rem;font-weight:600;padding:.5rem .75rem;cursor:pointer;border-radius:8px 8px 0 0;}}
.thm-tab:hover{{color:var(--text);background:var(--surface2);}}
.thm-tab.active{{color:var(--accent);border-bottom-color:var(--accent);}}
@media(min-width:920px){{.thm-stage{{position:sticky;top:1.5rem;align-self:flex-start;}}}}
</style>
<div class="page-header">
  <div class="page-title">Editor Kartu Welcome <small>Kartu sambutan member baru — geser elemen, atur teks, warna &amp; gambar</small></div>
</div>
<div class="card"><div class="card-body" style="display:flex;flex-wrap:wrap;gap:1.5rem;align-items:flex-start;">
  <div class="thm-stage" style="flex:1 1 560px;min-width:280px;">
    <div style="font-size:.8rem;color:var(--muted);margin-bottom:.5rem;">
      Seret kotak elemen untuk memindah posisi. Kanvas {wtheme.WELCOME_W}×{wtheme.WELCOME_H} (skala mengikuti lebar).</div>
    <div id="stage" style="position:relative;width:100%;max-width:840px;margin:0 auto;aspect-ratio:{wtheme.WELCOME_W}/{wtheme.WELCOME_H};
        border-radius:14px;overflow:hidden;border:1px solid var(--border);
        background:#222 url('/welcome-theme/preview.png') center/cover no-repeat;user-select:none;"></div>
    <div style="display:flex;gap:.5rem;margin-top:.8rem;flex-wrap:wrap;">
      <button class="btn btn-primary" onclick="saveTheme()">Simpan</button>
      <button class="btn btn-ghost" onclick="refreshPreview()">Perbarui Pratinjau</button>
      <button class="btn btn-ghost" onclick="resetTheme()">Reset Default</button>
    </div>
    <div id="status" style="margin-top:.6rem;font-size:.85rem;"></div>
  </div>
  <div class="thm-col" style="flex:1 1 320px;min-width:280px;">
    <div class="thm-tabs">
      <button type="button" class="thm-tab active" data-t="elemen" onclick="showThmTab('elemen')">Elemen</button>
      <button type="button" class="thm-tab" data-t="tampilan" onclick="showThmTab('tampilan')">Tampilan</button>
      <button type="button" class="thm-tab" data-t="aset" onclick="showThmTab('aset')">Aset</button>
    </div>
    <div class="thm-panel" id="thm-tampilan" hidden>
      <div class="form-group">
        <label style="display:flex;align-items:center;gap:.5rem;">
          <input type="checkbox" id="cardEnabled" {enabled_attr} onchange="theme.enabled=this.checked;markDirty();" style="width:auto;">
          Aktifkan kartu welcome (gambar)
        </label>
        <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem;">Jika nonaktif, bot tetap memakai sambutan embed teks klasik.</div>
      </div>
      <div class="form-group">
        <label>Nama Contoh (pratinjau)</label>
        <input type="text" id="sampleName" maxlength="22" placeholder="ContohMember"
          oninput="refreshPreview();" style="width:100%;">
        <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem;">Nama &amp; avatar member asli tidak tersimpan (butuh Discord), jadi pratinjau memakai contoh.</div>
      </div>
      <div class="form-group">
        <label>Opacity Panel ({theme['panel_opacity']})</label>
        <input type="range" min="0" max="255" id="panelOpacity" value="{theme['panel_opacity']}"
          oninput="theme.panel_opacity=+this.value;markDirty();">
      </div>
    </div>
    <div class="thm-panel" id="thm-aset" hidden>
      <div class="form-group">
        <label>Font Kustom — saat ini: <b id="curFont">{cur_font}</b></label>
        <input type="file" id="fontFile" accept=".ttf,.otf">
        <button class="btn btn-ghost btn-sm" style="margin-top:.4rem;" onclick="uploadFont()">Upload Font (.ttf/.otf)</button>
      </div>
      <div class="form-group">
        <label>Background Kartu <small style="color:var(--muted)" id="bgInfo"></small></label>
        <input type="file" id="bgFile" accept=".png,.jpg,.jpeg,.webp">
        <div style="display:flex;gap:.5rem;margin-top:.4rem;flex-wrap:wrap;">
          <button class="btn btn-ghost btn-sm" onclick="uploadBg()">Upload Background</button>
          <button class="btn btn-ghost btn-sm" onclick="deleteBg()">Hapus Background</button>
        </div>
        <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem;">Tanpa background = gradien default yang kalem.</div>
      </div>
    </div>
    <div class="thm-panel" id="thm-elemen">
      <label style="font-weight:600;">Elemen</label>
      <select id="elemSel" onchange="renderControls()" style="width:100%;margin:.4rem 0 .8rem;"></select>
      <div id="elemControls"></div>
    </div>
  </div>
</div></div>

<script>
var THEME = {theme_json};
var LABELS = {labels_json};
var ORDER = {order_json};
var HAS_BG = {has_bg_json};
var theme = JSON.parse(JSON.stringify(THEME));
var CARD_W={wtheme.WELCOME_W}, CARD_H={wtheme.WELCOME_H};

function showThmTab(t){{
  document.querySelectorAll('.thm-panel').forEach(function(p){{p.hidden=(p.id!=='thm-'+t);}});
  document.querySelectorAll('.thm-tab').forEach(function(b){{b.classList.toggle('active', b.dataset.t===t);}});
}}

var _previewTimer=null;
function markDirty(){{
  document.getElementById('status').innerHTML='<span style="color:var(--warning)">\\u25CF Perubahan belum disimpan (pratinjau diperbarui...)</span>';
  if(_previewTimer) clearTimeout(_previewTimer);
  _previewTimer=setTimeout(refreshPreview, 400);
}}
function setOk(m){{ document.getElementById('status').innerHTML='<span style="color:var(--success)">\\u2713 '+m+'</span>'; }}

var sel=document.getElementById('elemSel');
ORDER.forEach(function(k){{ var o=document.createElement('option'); o.value=k; o.textContent=LABELS[k]||k; sel.appendChild(o); }});

var stage=document.getElementById('stage');
function stageScale(){{ return stage.clientWidth / CARD_W; }}

function renderBoxes(){{
  stage.querySelectorAll('.el-box').forEach(function(e){{e.remove();}});
  var sc=stageScale();
  ORDER.forEach(function(k){{
    var el=theme.elements[k]; if(!el) return;
    var box=document.createElement('div');
    box.className='el-box'; box.dataset.k=k;
    box.style.cssText='position:absolute;padding:2px 6px;font-size:11px;border-radius:6px;cursor:move;'+
      'background:rgba(90,109,196,.9);color:#fff;white-space:nowrap;'+(el.show===false?'opacity:.4;':'');
    box.style.left=(el.x*sc)+'px'; box.style.top=(el.y*sc)+'px';
    box.textContent=LABELS[k]||k;
    box.onmousedown=startDrag;
    stage.appendChild(box);
  }});
}}

var drag=null;
function startDrag(e){{
  drag={{k:e.target.dataset.k, sx:e.clientX, sy:e.clientY,
        ox:theme.elements[e.target.dataset.k].x, oy:theme.elements[e.target.dataset.k].y}};
  sel.value=drag.k; renderControls();
  document.onmousemove=onDrag; document.onmouseup=endDrag; e.preventDefault();
}}
function onDrag(e){{
  if(!drag) return; var sc=stageScale();
  var nx=Math.round(drag.ox+(e.clientX-drag.sx)/sc);
  var ny=Math.round(drag.oy+(e.clientY-drag.sy)/sc);
  var el=theme.elements[drag.k];
  el.x=Math.max(0,Math.min(CARD_W,nx)); el.y=Math.max(0,Math.min(CARD_H,ny));
  renderBoxes(); renderControls(); markDirty();
}}
function endDrag(){{ drag=null; document.onmousemove=null; document.onmouseup=null; refreshPreview(); }}

function renderControls(){{
  var k=sel.value, el=theme.elements[k]; var h='';
  h+='<div class="form-group"><label>Tampilkan</label><select onchange="theme.elements[\\''+k+'\\'].show=(this.value==\\'1\\');renderBoxes();markDirty();">'+
     '<option value="1"'+(el.show!==false?' selected':'')+'>Ya</option><option value="0"'+(el.show===false?' selected':'')+'>Sembunyikan</option></select></div>';
  if(typeof el.text!=='undefined'){{
    h+='<div class="form-group"><label>Teks</label><input type="text" maxlength="60" value="'+(el.text||'').replace(/"/g,'&quot;')+'" oninput="theme.elements[\\''+k+'\\'].text=this.value;markDirty();"></div>';
  }}
  h+='<div class="form-group"><label>X: '+el.x+'</label><input type="range" min="0" max="'+CARD_W+'" value="'+el.x+'" oninput="theme.elements[\\''+k+'\\'].x=+this.value;renderBoxes();markDirty();"></div>';
  h+='<div class="form-group"><label>Y: '+el.y+'</label><input type="range" min="0" max="'+CARD_H+'" value="'+el.y+'" oninput="theme.elements[\\''+k+'\\'].y=+this.value;renderBoxes();markDirty();"></div>';
  if(el.type==='text'){{
    h+='<div class="form-group"><label>Ukuran Font: '+el.size+'</label><input type="range" min="8" max="120" value="'+el.size+'" oninput="theme.elements[\\''+k+'\\'].size=+this.value;markDirty();"></div>';
    h+='<div class="form-group"><label>Warna</label><input type="color" value="'+el.color+'" oninput="theme.elements[\\''+k+'\\'].color=this.value;markDirty();"></div>';
    h+='<div class="form-group"><label>Tebal</label><select onchange="theme.elements[\\''+k+'\\'].bold=(this.value==\\'1\\');markDirty();"><option value="1"'+(el.bold?' selected':'')+'>Bold</option><option value="0"'+(!el.bold?' selected':'')+'>Normal</option></select></div>';
  }} else if(el.type==='avatar'){{
    h+='<div class="form-group"><label>Ukuran: '+el.size+'</label><input type="range" min="32" max="320" value="'+el.size+'" oninput="theme.elements[\\''+k+'\\'].size=+this.value;renderBoxes();markDirty();"></div>';
  }}
  document.getElementById('elemControls').innerHTML=h;
}}

function refreshPreview(){{
  var nameEl=document.getElementById('sampleName');
  var nameq=(nameEl && nameEl.value.trim()) ? '&name='+encodeURIComponent(nameEl.value.trim()) : '';
  var url='/welcome-theme/preview.png?t='+encodeURIComponent(JSON.stringify(theme))+nameq+'&_='+Date.now();
  stage.style.backgroundImage="url('"+url+"')";
}}
function initBgUI(){{
  document.getElementById('bgInfo').textContent = HAS_BG ? '— background terpasang \\u2713' : '— belum ada background';
}}
function uploadBg(){{
  var f=document.getElementById('bgFile').files[0];
  if(!f){{alert('Pilih file gambar dulu.');return;}}
  var fd=new FormData(); fd.append('bg',f);
  fetch('/welcome-theme/bg',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ HAS_BG=true; initBgUI(); setOk('Background diupload & diterapkan.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload background.'); }}
  }});
}}
function deleteBg(){{
  if(!confirm('Hapus background kartu welcome?')) return;
  fetch('/welcome-theme/bg/delete',{{method:'POST'}}).then(r=>r.json()).then(function(d){{
    HAS_BG=false; initBgUI(); setOk('Background dihapus (kembali ke gradien).'); refreshPreview(); }});
}}
function saveTheme(){{
  fetch('/welcome-theme/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(theme)}})
    .then(r=>r.json()).then(function(d){{ if(d.ok){{theme=d.theme; setOk('Tema disimpan & diterapkan ke bot.'); refreshPreview();}} else {{markDirty();}} }});
}}
function resetTheme(){{
  if(!confirm('Kembalikan ke tema default?')) return;
  fetch('/welcome-theme/reset',{{method:'POST'}}).then(r=>r.json()).then(function(d){{
    theme=d.theme; document.getElementById('cardEnabled').checked=!!theme.enabled;
    renderBoxes(); renderControls(); refreshPreview(); setOk('Direset ke default.'); }});
}}
function uploadFont(){{
  var f=document.getElementById('fontFile').files[0];
  if(!f){{alert('Pilih file font dulu.');return;}}
  var fd=new FormData(); fd.append('font',f);
  fetch('/welcome-theme/font',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ theme.font_file=d.font_file; document.getElementById('curFont').textContent=d.font_file; setOk('Font diupload & diterapkan.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload font.'); }}
  }});
}}

window.addEventListener('resize', renderBoxes);
renderBoxes(); renderControls(); initBgUI();
</script>"""
    return render_page(content)
