"""admin_profile_theme.py - Editor Kartu Profil untuk Admin Panel.

Blueprint terpisah (pola sama dgn admin_insights.py). Memberi editor visual:
  - /profil-theme            : halaman editor (drag-drop posisi + warna/font/size)
  - /profil-theme/preview.png: render kartu contoh dgn tema saat ini
  - /profil-theme/save       : simpan tema (POST JSON)
  - /profil-theme/font       : upload file font .ttf/.otf (POST file)
  - /profil-theme/reset      : kembalikan ke default

render_page/ICONS di-import lazily di dalam view (hindari circular import).
"""
import os
import json

from flask import Blueprint, request, session, redirect, Response, jsonify

from utils import profile_theme as themelib

theme_bp = Blueprint("theme_bp", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ALLOWED_FONT_EXTS = (".ttf", ".otf")
ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
VALID_TIERS = ["Bronze", "Silver", "Gold", "Diamond"]
PROFILE_BG_BASE = "profilebg"


def _bg_path(base, tier):
    """Path file background tier (atau None). Sama dgn yang dibaca cogs/profile.py."""
    if tier not in VALID_TIERS:
        return None
    for ext in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, f"{base}_{tier.lower()}{ext}")
        if os.path.exists(p):
            return p
    return None


def _tiers_with_bg(base):
    return [t for t in VALID_TIERS if _bg_path(base, t)]


def _save_bg_file(base, tier, file_storage):
    """Validasi & simpan background -> data/<base>_<tier>.<ext>. Return (ok, msg)."""
    if tier not in VALID_TIERS:
        return False, "Tier tidak valid."
    if not file_storage or not file_storage.filename:
        return False, "Tidak ada file."
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return False, "Format harus PNG/JPG/WEBP."
    os.makedirs(DATA_DIR, exist_ok=True)
    # hapus versi lama (ekstensi apa pun) supaya tak ada dobel.
    for e in ALLOWED_IMAGE_EXTS:
        old = os.path.join(DATA_DIR, f"{base}_{tier.lower()}{e}")
        if os.path.exists(old):
            try:
                os.remove(old)
            except Exception:
                pass
    file_storage.save(os.path.join(DATA_DIR, f"{base}_{tier.lower()}{ext}"))
    return True, "ok"


def _delete_bg_file(base, tier):
    removed = False
    for e in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, f"{base}_{(tier or '').lower()}{e}")
        if os.path.exists(p):
            try:
                os.remove(p)
                removed = True
            except Exception:
                pass
    return removed


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


def _sample_data():
    """Data contoh untuk preview kartu (tanpa akses DB)."""
    return {
        "tier": "Gold", "level": 12,
        "xp_into_level": 720, "xp_for_next": 1000, "xp_remaining": 280,
        "next_tier": "Diamond",
        "spent_month": 1250000, "total_orders": 24, "total_reviews": 8,
        "first_order": "2025-01-12T00:00:00+00:00",
    }



@theme_bp.route("/profil-theme/preview.png")
def preview_png():
    g = _guard()
    if g:
        return g
    # Render pakai theme yang dikirim via query (?t=<json>) bila ada, else tersimpan.
    raw = request.args.get("t")
    theme = themelib.merge_theme(raw) if raw else themelib.load_theme()
    bg_path = _bg_path(PROFILE_BG_BASE, request.args.get("bg"))
    try:
        from cogs.profile import render_profile_card
        buf = render_profile_card("ContohMember", None, _sample_data(),
                                  rank=3, badges=["👑 Top Spender", "🔁 Repeat Buyer"],
                                  bg_path=bg_path, theme=theme)
        return Response(buf.getvalue(), mimetype="image/png")
    except Exception as e:
        # Pillow tak tersedia / error -> PNG 1x1 transparan + pesan di header.
        png_1x1 = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                   b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
                   b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        return Response(png_1x1, mimetype="image/png",
                        headers={"X-Render-Error": str(e)[:200]})


@theme_bp.route("/profil-theme/save", methods=["POST"])
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
        payload["font_file"] = themelib.load_theme().get("font_file")
    theme = themelib.save_theme(payload)
    return jsonify({"ok": True, "theme": theme})


@theme_bp.route("/profil-theme/reset", methods=["POST"])
def reset_theme_route():
    g = _guard()
    if g:
        return g
    theme = themelib.save_theme(themelib.default_theme())
    return jsonify({"ok": True, "theme": theme})


@theme_bp.route("/profil-theme/font", methods=["POST"])
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
    fname = "profile_font" + ext
    # bersihkan font lama dgn ekstensi lain
    for e in ALLOWED_FONT_EXTS:
        old = os.path.join(DATA_DIR, "profile_font" + e)
        if os.path.exists(old) and e != ext:
            try:
                os.remove(old)
            except Exception:
                pass
    f.save(os.path.join(DATA_DIR, fname))
    theme = themelib.load_theme()
    theme["font_file"] = fname
    themelib.save_theme(theme)
    return jsonify({"ok": True, "font_file": fname})



@theme_bp.route("/profil-theme/bg", methods=["POST"])
def upload_bg():
    g = _guard()
    if g:
        return g
    tier = request.form.get("tier", "")
    ok, msg = _save_bg_file(PROFILE_BG_BASE, tier, request.files.get("bg"))
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True, "tier": tier, "tiers_with_bg": _tiers_with_bg(PROFILE_BG_BASE)})


@theme_bp.route("/profil-theme/bg/delete", methods=["POST"])
def delete_bg():
    g = _guard()
    if g:
        return g
    tier = (request.get_json(force=True, silent=True) or {}).get("tier", "")
    removed = _delete_bg_file(PROFILE_BG_BASE, tier)
    return jsonify({"ok": True, "removed": removed, "tiers_with_bg": _tiers_with_bg(PROFILE_BG_BASE)})


@theme_bp.route("/profil-theme")
def page_theme():
    g = _guard()
    if g:
        return g
    from admin import render_page

    theme = themelib.load_theme()
    theme_json = json.dumps(theme)
    labels_json = json.dumps(dict(themelib.ELEMENT_LABELS))
    order_json = json.dumps([k for k, _ in themelib.ELEMENT_LABELS])
    cur_font = theme.get("font_file") or "(default sistem)"
    bg_tiers_json = json.dumps(_tiers_with_bg(PROFILE_BG_BASE))
    tiers_json = json.dumps(VALID_TIERS)

    content = f"""
<div class="page-header">
  <div class="page-title">Editor Kartu Profil <small>Geser elemen, atur font, warna & ukuran — lalu Simpan</small></div>
</div>
<div class="card"><div class="card-body" style="display:flex;flex-wrap:wrap;gap:1.5rem;align-items:flex-start;">
  <div style="flex:1 1 480px;min-width:320px;">
    <div style="font-size:.8rem;color:var(--muted);margin-bottom:.5rem;">
      Seret kotak elemen untuk memindah posisi. Kanvas 900×360 (skala mengikuti lebar).</div>
    <div id="stage" style="position:relative;width:100%;max-width:600px;aspect-ratio:900/360;
        border-radius:14px;overflow:hidden;border:1px solid var(--border);
        background:#222 url('/profil-theme/preview.png') center/cover no-repeat;user-select:none;"></div>
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
    <div class="form-group">
      <label>Background per Tier <small style="color:var(--muted)" id="bgInfo"></small></label>
      <select id="bgTier" onchange="refreshPreview()" style="width:100%;margin-bottom:.4rem;"></select>
      <input type="file" id="bgFile" accept=".png,.jpg,.jpeg,.webp">
      <div style="display:flex;gap:.5rem;margin-top:.4rem;flex-wrap:wrap;">
        <button class="btn btn-ghost btn-sm" onclick="uploadBg()">⬆️ Upload Background</button>
        <button class="btn btn-ghost btn-sm" onclick="deleteBg()">🗑️ Hapus Background</button>
      </div>
      <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem;">Pratinjau memakai background tier yang dipilih di atas.</div>
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
var BG_TIERS = {bg_tiers_json};
var TIERS = {tiers_json};
var theme = JSON.parse(JSON.stringify(THEME));
var CARD_W=900, CARD_H=360;

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
  h+='<div class="form-group"><label>X: '+el.x+'</label><input type="range" min="0" max="'+CARD_W+'" value="'+el.x+'" oninput="theme.elements[\\''+k+'\\'].x=+this.value;renderBoxes();markDirty();"></div>';
  h+='<div class="form-group"><label>Y: '+el.y+'</label><input type="range" min="0" max="'+CARD_H+'" value="'+el.y+'" oninput="theme.elements[\\''+k+'\\'].y=+this.value;renderBoxes();markDirty();"></div>';
  if(el.type==='text'){{
    h+='<div class="form-group"><label>Ukuran Font: '+el.size+'</label><input type="range" min="8" max="120" value="'+el.size+'" oninput="theme.elements[\\''+k+'\\'].size=+this.value;markDirty();"></div>';
    h+='<div class="form-group"><label>Warna</label><input type="color" value="'+el.color+'" oninput="theme.elements[\\''+k+'\\'].color=this.value;markDirty();"></div>';
    h+='<div class="form-group"><label>Tebal</label><select onchange="theme.elements[\\''+k+'\\'].bold=(this.value==\\'1\\');markDirty();"><option value="1"'+(el.bold?' selected':'')+'>Bold</option><option value="0"'+(!el.bold?' selected':'')+'>Normal</option></select></div>';
  }} else if(el.type==='avatar'){{
    h+='<div class="form-group"><label>Ukuran: '+el.size+'</label><input type="range" min="32" max="300" value="'+el.size+'" oninput="theme.elements[\\''+k+'\\'].size=+this.value;renderBoxes();markDirty();"></div>';
  }} else if(el.type==='bar'){{
    h+='<div class="form-group"><label>Lebar: '+el.w+'</label><input type="range" min="50" max="'+CARD_W+'" value="'+el.w+'" oninput="theme.elements[\\''+k+'\\'].w=+this.value;markDirty();"></div>';
    h+='<div class="form-group"><label>Tinggi: '+el.h+'</label><input type="range" min="6" max="80" value="'+el.h+'" oninput="theme.elements[\\''+k+'\\'].h=+this.value;markDirty();"></div>';
    h+='<div class="form-group"><label>Warna</label><input type="color" value="'+el.color+'" oninput="theme.elements[\\''+k+'\\'].color=this.value;markDirty();"></div>';
  }}
  document.getElementById('elemControls').innerHTML=h;
}}

function refreshPreview(){{
  var bgt=document.getElementById('bgTier');
  var bgq=(bgt && bgt.value) ? '&bg='+encodeURIComponent(bgt.value) : '';
  var url='/profil-theme/preview.png?t='+encodeURIComponent(JSON.stringify(theme))+bgq+'&_='+Date.now();
  stage.style.backgroundImage="url('"+url+"')";
}}
function initBgUI(){{
  var sel=document.getElementById('bgTier');
  sel.innerHTML='';
  TIERS.forEach(function(t){{
    var o=document.createElement('option'); o.value=t;
    o.textContent=t+(BG_TIERS.indexOf(t)>=0?' ✓':' (default)'); sel.appendChild(o);
  }});
  var def=BG_TIERS.length?BG_TIERS[0]:'Gold'; sel.value=def;
  document.getElementById('bgInfo').textContent = BG_TIERS.length
    ? '— punya BG: '+BG_TIERS.join(', ') : '— belum ada BG kustom';
}}
function uploadBg(){{
  var f=document.getElementById('bgFile').files[0];
  var tier=document.getElementById('bgTier').value;
  if(!f){{alert('Pilih file gambar dulu.');return;}}
  var fd=new FormData(); fd.append('tier',tier); fd.append('bg',f);
  fetch('/profil-theme/bg',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ BG_TIERS=d.tiers_with_bg; initBgUI(); document.getElementById('bgTier').value=tier;
      setOk('Background tier '+tier+' diupload & diterapkan ke bot.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload background.'); }}
  }});
}}
function deleteBg(){{
  var tier=document.getElementById('bgTier').value;
  if(!confirm('Hapus background tier '+tier+'?')) return;
  fetch('/profil-theme/bg/delete',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{tier:tier}})}})
    .then(r=>r.json()).then(function(d){{ BG_TIERS=d.tiers_with_bg; initBgUI();
      document.getElementById('bgTier').value=tier; setOk('Background tier '+tier+' dihapus (kembali ke gradien).'); refreshPreview(); }});
}}
function saveTheme(){{
  fetch('/profil-theme/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(theme)}})
    .then(r=>r.json()).then(function(d){{ if(d.ok){{theme=d.theme; setOk('Tema disimpan & diterapkan ke bot.'); refreshPreview();}} else {{markDirty();}} }});
}}
function resetTheme(){{
  if(!confirm('Kembalikan ke tema default?')) return;
  fetch('/profil-theme/reset',{{method:'POST'}}).then(r=>r.json()).then(function(d){{
    theme=d.theme; renderBoxes(); renderControls(); refreshPreview(); setOk('Direset ke default.'); }});
}}
function uploadFont(){{
  var f=document.getElementById('fontFile').files[0];
  if(!f){{alert('Pilih file font dulu.');return;}}
  var fd=new FormData(); fd.append('font',f);
  fetch('/profil-theme/font',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ theme.font_file=d.font_file; document.getElementById('curFont').textContent=d.font_file; setOk('Font diupload & diterapkan.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload font.'); }}
  }});
}}

window.addEventListener('resize', renderBoxes);
renderBoxes(); renderControls(); initBgUI();
</script>"""
    content = content.replace("{{op}}", str(theme["panel_opacity"]))
    return render_page(content)
