"""admin_achievement_theme.py - Editor Kartu Badge (Achievement) untuk Admin Panel.

Blueprint terpisah (pola sama dgn admin_profile_theme.py). Memberi editor visual
untuk kartu "Achievement Unlocked" yang dikirim saat member dapat badge baru:
  - /badge-theme            : halaman editor (drag-drop posisi + warna/font/size/judul)
  - /badge-theme/preview.png: render kartu contoh dgn tema saat ini
  - /badge-theme/save       : simpan tema (POST JSON)
  - /badge-theme/font       : upload file font .ttf/.otf (POST file)
  - /badge-theme/reset      : kembalikan ke default

render_page di-import lazily di dalam view (hindari circular import).
"""
import os
import json

from flask import Blueprint, request, session, redirect, Response, jsonify

from utils import achievement_theme as achthemelib

badge_theme_bp = Blueprint("badge_theme_bp", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ALLOWED_FONT_EXTS = (".ttf", ".otf")


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


def _sample_badges():
    """Data contoh untuk preview kartu (tanpa akses DB)."""
    return ["Belanja 10x", "Pelanggan Setia", "Reviewer Aktif"]


@badge_theme_bp.route("/badge-theme/preview.png")
def preview_png():
    g = _guard()
    if g:
        return g
    # Render pakai theme yang dikirim via query (?t=<json>) bila ada, else tersimpan.
    raw = request.args.get("t")
    theme = achthemelib.merge_theme(raw) if raw else achthemelib.load_theme()
    try:
        from cogs.profile import render_achievement_card
        buf = render_achievement_card("ContohMember", None, _sample_badges(),
                                      tier="Gold", theme=theme)
        return Response(buf.getvalue(), mimetype="image/png")
    except Exception as e:
        # Pillow tak tersedia / error -> PNG 1x1 transparan + pesan di header.
        png_1x1 = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                   b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
                   b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        return Response(png_1x1, mimetype="image/png",
                        headers={"X-Render-Error": str(e)[:200]})


@badge_theme_bp.route("/badge-theme/save", methods=["POST"])
def save_theme_route():
    g = _guard()
    if g:
        return g
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        payload = {}
    # pertahankan font_file tersimpan bila tidak dikirim
    if "font_file" not in payload:
        payload["font_file"] = achthemelib.load_theme().get("font_file")
    theme = achthemelib.save_theme(payload)
    return jsonify({"ok": True, "theme": theme})


@badge_theme_bp.route("/badge-theme/reset", methods=["POST"])
def reset_theme_route():
    g = _guard()
    if g:
        return g
    theme = achthemelib.save_theme(achthemelib.default_theme())
    return jsonify({"ok": True, "theme": theme})


@badge_theme_bp.route("/badge-theme/font", methods=["POST"])
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
    fname = "badge_font" + ext
    # bersihkan font lama dgn ekstensi lain
    for e in ALLOWED_FONT_EXTS:
        old = os.path.join(DATA_DIR, "badge_font" + e)
        if os.path.exists(old) and e != ext:
            try:
                os.remove(old)
            except Exception:
                pass
    f.save(os.path.join(DATA_DIR, fname))
    theme = achthemelib.load_theme()
    theme["font_file"] = fname
    achthemelib.save_theme(theme)
    return jsonify({"ok": True, "font_file": fname})


@badge_theme_bp.route("/badge-theme")
def page_theme():
    g = _guard()
    if g:
        return g
    from admin import render_page

    theme = achthemelib.load_theme()
    theme_json = json.dumps(theme)
    labels_json = json.dumps(dict(achthemelib.ELEMENT_LABELS))
    order_json = json.dumps([k for k, _ in achthemelib.ELEMENT_LABELS])
    cur_font = theme.get("font_file") or "(default sistem)"

    content = f"""
<div class="page-header">
  <div class="page-title">Editor Kartu Badge <small>Geser elemen, atur judul, font, warna & ukuran — lalu Simpan</small></div>
</div>
<div class="card"><div class="card-body" style="display:flex;flex-wrap:wrap;gap:1.5rem;align-items:flex-start;">
  <div style="flex:1 1 480px;min-width:320px;">
    <div style="font-size:.8rem;color:var(--muted);margin-bottom:.5rem;">
      Seret kotak elemen untuk memindah posisi. Kanvas {achthemelib.ACH_W}×{achthemelib.ACH_H} (skala mengikuti lebar).</div>
    <div id="stage" style="position:relative;width:100%;max-width:600px;aspect-ratio:{achthemelib.ACH_W}/{achthemelib.ACH_H};
        border-radius:14px;overflow:hidden;border:1px solid var(--border);
        background:#222 url('/badge-theme/preview.png') center/cover no-repeat;user-select:none;"></div>
    <div style="display:flex;gap:.5rem;margin-top:.8rem;flex-wrap:wrap;">
      <button class="btn btn-primary" onclick="saveTheme()">💾 Simpan</button>
      <button class="btn btn-ghost" onclick="refreshPreview()">🔄 Perbarui Pratinjau</button>
      <button class="btn btn-ghost" onclick="resetTheme()">↩️ Reset Default</button>
    </div>
    <div id="status" style="margin-top:.6rem;font-size:.85rem;"></div>
  </div>
  <div style="flex:1 1 300px;min-width:280px;">
    <div class="form-group">
      <label>Opacity Panel ({{op}})</label>
      <input type="range" min="0" max="255" id="panelOpacity" value="{theme['panel_opacity']}"
        oninput="theme.panel_opacity=+this.value;markDirty();">
    </div>
    <div class="form-group">
      <label>Font Kustom — saat ini: <b id="curFont">{cur_font}</b></label>
      <input type="file" id="fontFile" accept=".ttf,.otf">
      <button class="btn btn-ghost btn-sm" style="margin-top:.4rem;" onclick="uploadFont()">⬆️ Upload Font (.ttf/.otf)</button>
    </div>
    <hr style="border-color:var(--border);margin:1rem 0;">
    <label style="font-weight:600;">Elemen</label>
    <select id="elemSel" onchange="renderControls()" style="width:100%;margin:.4rem 0 .8rem;"></select>
    <div id="elemControls"></div>
  </div>
</div></div>

<script>
var THEME = {theme_json};
var LABELS = {labels_json};
var ORDER = {order_json};
var theme = JSON.parse(JSON.stringify(THEME));
var CARD_W={achthemelib.ACH_W}, CARD_H={achthemelib.ACH_H};

var _previewTimer=null;
function markDirty(){{
  document.getElementById('status').innerHTML='<span style="color:var(--warning)">● Perubahan belum disimpan (pratinjau diperbarui...)</span>';
  // Debounce: perbarui pratinjau 400ms setelah perubahan terakhir.
  if(_previewTimer) clearTimeout(_previewTimer);
  _previewTimer=setTimeout(refreshPreview, 400);
}}
function setOk(m){{ document.getElementById('status').innerHTML='<span style="color:var(--success)">✓ '+m+'</span>'; }}

// Build element selector
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
      'background:rgba(37,99,235,.85);color:#fff;white-space:nowrap;'+(el.show===false?'opacity:.4;':'');
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
    h+='<div class="form-group"><label>Teks Judul</label><input type="text" maxlength="40" value="'+(el.text||'').replace(/"/g,'&quot;')+'" oninput="theme.elements[\\''+k+'\\'].text=this.value;markDirty();"></div>';
  }}
  h+='<div class="form-group"><label>X: '+el.x+'</label><input type="range" min="0" max="'+CARD_W+'" value="'+el.x+'" oninput="theme.elements[\\''+k+'\\'].x=+this.value;renderBoxes();markDirty();"></div>';
  h+='<div class="form-group"><label>Y: '+el.y+'</label><input type="range" min="0" max="'+CARD_H+'" value="'+el.y+'" oninput="theme.elements[\\''+k+'\\'].y=+this.value;renderBoxes();markDirty();"></div>';
  if(el.type==='text'){{
    h+='<div class="form-group"><label>Ukuran Font: '+el.size+'</label><input type="range" min="8" max="120" value="'+el.size+'" oninput="theme.elements[\\''+k+'\\'].size=+this.value;markDirty();"></div>';
    h+='<div class="form-group"><label>Warna</label><input type="color" value="'+el.color+'" oninput="theme.elements[\\''+k+'\\'].color=this.value;markDirty();"></div>';
    h+='<div class="form-group"><label>Tebal</label><select onchange="theme.elements[\\''+k+'\\'].bold=(this.value==\\'1\\');markDirty();"><option value="1"'+(el.bold?' selected':'')+'>Bold</option><option value="0"'+(!el.bold?' selected':'')+'>Normal</option></select></div>';
  }} else if(el.type==='avatar'){{
    h+='<div class="form-group"><label>Ukuran: '+el.size+'</label><input type="range" min="32" max="300" value="'+el.size+'" oninput="theme.elements[\\''+k+'\\'].size=+this.value;renderBoxes();markDirty();"></div>';
  }}
  document.getElementById('elemControls').innerHTML=h;
}}

function refreshPreview(){{
  var url='/badge-theme/preview.png?t='+encodeURIComponent(JSON.stringify(theme))+'&_='+Date.now();
  stage.style.backgroundImage="url('"+url+"')";
}}
function saveTheme(){{
  fetch('/badge-theme/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(theme)}})
    .then(r=>r.json()).then(function(d){{ if(d.ok){{theme=d.theme; setOk('Tema disimpan & diterapkan ke bot.'); refreshPreview();}} else {{markDirty();}} }});
}}
function resetTheme(){{
  if(!confirm('Kembalikan ke tema default?')) return;
  fetch('/badge-theme/reset',{{method:'POST'}}).then(r=>r.json()).then(function(d){{
    theme=d.theme; renderBoxes(); renderControls(); refreshPreview(); setOk('Direset ke default.'); }});
}}
function uploadFont(){{
  var f=document.getElementById('fontFile').files[0];
  if(!f){{alert('Pilih file font dulu.');return;}}
  var fd=new FormData(); fd.append('font',f);
  fetch('/badge-theme/font',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ theme.font_file=d.font_file; document.getElementById('curFont').textContent=d.font_file; setOk('Font diupload & diterapkan.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload font.'); }}
  }});
}}

window.addEventListener('resize', renderBoxes);
renderBoxes(); renderControls();
</script>"""
    content = content.replace("{{op}}", str(theme["panel_opacity"]))
    return render_page(content)
