"""admin_welcome_theme.py - Editor Kartu (Welcome / Boost / Leave) untuk Admin Panel.

Satu halaman ber-tab untuk tiga jenis kartu notifikasi member yang strukturnya
identik (lihat utils/welcome_theme.py): welcome, boost, leave. Tab dipilih lewat
query `?kind=` sehingga editor (drag-drop + kontrol) dipakai ulang per jenis.

  - /card-theme?kind=welcome     : halaman editor (default welcome)
  - /card-theme/preview.png?kind= : render kartu contoh dgn tema saat ini
  - /card-theme/save             : simpan tema (POST JSON {kind, theme})
  - /card-theme/reset            : reset ke default (POST {kind})
  - /card-theme/font             : upload font .ttf/.otf (POST form: kind + file)
  - /card-theme/bg               : upload background (POST form: kind + file)
  - /card-theme/bg/delete        : hapus background (POST {kind})

Background kustom per jenis = data/<kind>cardbg.<ext> (welcome tetap memakai
`welcomecardbg` agar data lama kompatibel). Font kustom = data/<kind>_font.<ext>.

Route lama /welcome-theme dialihkan ke /card-theme?kind=welcome.
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

KIND_LABELS = {"welcome": "Welcome", "boost": "Boost", "leave": "Leave"}
KIND_BLURB = {
    "welcome": "Kartu sambutan member baru saat join.",
    "boost": "Kartu ucapan terima kasih saat member nge-boost server.",
    "leave": "Kartu pamitan saat member keluar server.",
}


def _kind():
    k = (request.args.get("kind") or request.form.get("kind") or "").strip().lower()
    return k if k in wtheme.KINDS else "welcome"


def _kind_from_json(payload):
    k = (payload.get("kind") or "").strip().lower() if isinstance(payload, dict) else ""
    return k if k in wtheme.KINDS else "welcome"


def _bg_base(kind):
    return f"{kind}cardbg"


def _bg_path(kind):
    base = _bg_base(kind)
    for ext in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, base + ext)
        if os.path.exists(p):
            return p
    return None


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@welcome_theme_bp.route("/welcome-theme")
def page_theme_legacy():
    """Kompatibilitas: alihkan URL lama ke editor gabungan."""
    return redirect("/card-theme?kind=welcome")


@welcome_theme_bp.route("/card-theme/preview.png")
def preview_png():
    g = _guard()
    if g:
        return g
    kind = _kind()
    raw = request.args.get("t")
    theme = wtheme.merge_theme(raw, kind) if raw else wtheme.load_theme(kind)
    name = (request.args.get("name") or "").strip() or "ContohMember"
    # Teks elemen dinamis (membercount) contoh per jenis.
    sample_count = {
        "welcome": "Member #123",
        "boost": "3x boost server",
        "leave": "Tersisa 122 member",
    }.get(kind, "Member #123")
    try:
        from cogs.profile import render_notify_card
        buf = render_notify_card(
            kind, None,
            values={"name": name, "membercount": sample_count},
            theme=theme, bg_path=_bg_path(kind),
        )
        return Response(buf.getvalue(), mimetype="image/png")
    except Exception as e:
        png_1x1 = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                   b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
                   b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        return Response(png_1x1, mimetype="image/png",
                        headers={"X-Render-Error": str(e)[:200]})


@welcome_theme_bp.route("/card-theme/save", methods=["POST"])
def save_theme_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = _kind_from_json(payload)
    theme_in = payload.get("theme") if isinstance(payload.get("theme"), dict) else payload
    if isinstance(theme_in, dict) and "font_file" not in theme_in:
        theme_in = dict(theme_in)
        theme_in["font_file"] = wtheme.load_theme(kind).get("font_file")
    theme = wtheme.save_theme(theme_in, kind)
    return jsonify({"ok": True, "kind": kind, "theme": theme})


@welcome_theme_bp.route("/card-theme/reset", methods=["POST"])
def reset_theme_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = _kind_from_json(payload) if payload else _kind()
    theme = wtheme.save_theme(wtheme.default_theme(kind), kind)
    return jsonify({"ok": True, "kind": kind, "theme": theme})


@welcome_theme_bp.route("/card-theme/font", methods=["POST"])
def upload_font():
    g = _guard()
    if g:
        return g
    kind = _kind()
    f = request.files.get("font")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "Tidak ada file."}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_FONT_EXTS:
        return jsonify({"ok": False, "error": "Format harus .ttf atau .otf."}), 400
    os.makedirs(DATA_DIR, exist_ok=True)
    fname = f"{kind}_font" + ext
    for e in ALLOWED_FONT_EXTS:
        old = os.path.join(DATA_DIR, f"{kind}_font" + e)
        if os.path.exists(old) and e != ext:
            try:
                os.remove(old)
            except Exception:
                pass
    f.save(os.path.join(DATA_DIR, fname))
    theme = wtheme.load_theme(kind)
    theme["font_file"] = fname
    wtheme.save_theme(theme, kind)
    return jsonify({"ok": True, "kind": kind, "font_file": fname})


@welcome_theme_bp.route("/card-theme/bg", methods=["POST"])
def upload_bg():
    g = _guard()
    if g:
        return g
    kind = _kind()
    f = request.files.get("bg")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "Tidak ada file."}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return jsonify({"ok": False, "error": "Format harus PNG/JPG/WEBP."}), 400
    os.makedirs(DATA_DIR, exist_ok=True)
    base = _bg_base(kind)
    for e in ALLOWED_IMAGE_EXTS:
        old = os.path.join(DATA_DIR, base + e)
        if os.path.exists(old):
            try:
                os.remove(old)
            except Exception:
                pass
    f.save(os.path.join(DATA_DIR, base + ext))
    return jsonify({"ok": True, "kind": kind, "has_bg": True})


@welcome_theme_bp.route("/card-theme/bg/delete", methods=["POST"])
def delete_bg():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    kind = _kind_from_json(payload) if payload else _kind()
    removed = False
    base = _bg_base(kind)
    for e in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, base + e)
        if os.path.exists(p):
            try:
                os.remove(p)
                removed = True
            except Exception:
                pass
    return jsonify({"ok": True, "kind": kind, "removed": removed, "has_bg": False})


@welcome_theme_bp.route("/card-theme")
def page_theme():
    g = _guard()
    if g:
        return g
    from admin import render_page

    kind = _kind()
    cw, ch = wtheme.CANVAS[kind]
    theme = wtheme.load_theme(kind)
    theme_json = json.dumps(theme)
    labels_json = json.dumps(dict(wtheme.element_labels(kind)))
    order_json = json.dumps(list(wtheme.ELEMENT_ORDER))
    cur_font = theme.get("font_file") or "(default sistem)"
    has_bg_json = json.dumps(_bg_path(kind) is not None)
    enabled_attr = "checked" if theme.get("enabled") else ""

    # Tab navigasi antar jenis kartu (link ?kind=).
    tabs = []
    for k in wtheme.KINDS:
        active = " active" if k == kind else ""
        tabs.append(
            f'<a class="kind-tab{active}" href="/card-theme?kind={k}">{KIND_LABELS[k]}</a>'
        )
    kind_tabs = "".join(tabs)
    kind_blurb = KIND_BLURB.get(kind, "")
    kind_label = KIND_LABELS.get(kind, kind)

    content = f"""
<style>
.kind-tabs{{display:flex;gap:.4rem;margin-bottom:1rem;flex-wrap:wrap;}}
.kind-tab{{display:inline-block;padding:.5rem 1rem;border-radius:10px;background:var(--surface2);
  color:var(--muted2);font-size:.85rem;font-weight:700;text-decoration:none;border:1px solid var(--border);}}
.kind-tab:hover{{color:var(--text);}}
.kind-tab.active{{background:var(--accent);color:#fff;border-color:var(--accent);}}
.thm-tabs{{display:flex;gap:.25rem;margin-bottom:1rem;border-bottom:1px solid var(--border);flex-wrap:wrap;}}
.thm-tab{{appearance:none;background:none;border:none;border-bottom:2px solid transparent;color:var(--muted2);font:inherit;font-size:.82rem;font-weight:600;padding:.5rem .75rem;cursor:pointer;border-radius:8px 8px 0 0;}}
.thm-tab:hover{{color:var(--text);background:var(--surface2);}}
.thm-tab.active{{color:var(--accent);border-bottom-color:var(--accent);}}
@media(min-width:920px){{.thm-stage{{position:sticky;top:1.5rem;align-self:flex-start;}}}}
</style>
<div class="page-header">
  <div class="page-title">Editor Kartu <small>Welcome, Boost &amp; Leave — geser elemen, atur teks, warna, bingkai avatar &amp; gambar</small></div>
</div>
<div class="kind-tabs">{kind_tabs}</div>
<div style="font-size:.82rem;color:var(--muted);margin-bottom:1rem;">Sedang mengedit kartu <b>{kind_label}</b> — {kind_blurb}</div>
<div class="card"><div class="card-body" style="display:flex;flex-wrap:wrap;gap:1.5rem;align-items:flex-start;">
  <div class="thm-stage" style="flex:1 1 560px;min-width:280px;">
    <div style="font-size:.8rem;color:var(--muted);margin-bottom:.5rem;">
      Seret kotak elemen untuk memindah posisi. Kanvas {cw}×{ch} (skala mengikuti lebar).</div>
    <div id="stage" style="position:relative;width:100%;max-width:840px;margin:0 auto;aspect-ratio:{cw}/{ch};
        border-radius:14px;overflow:hidden;border:1px solid var(--border);
        background:#222 url('/card-theme/preview.png?kind={kind}') center/cover no-repeat;user-select:none;"></div>
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
          Aktifkan kartu {kind_label} (gambar)
        </label>
        <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem;">Jika nonaktif, bot tetap memakai notifikasi embed teks klasik untuk {kind_label}.</div>
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
var KIND = "{kind}";
var theme = JSON.parse(JSON.stringify(THEME));
var CARD_W={cw}, CARD_H={ch};

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
    h+='<div class="form-group"><label>Warna Bingkai (ring)</label><input type="color" value="'+(el.ring_color||'#8B9BE0')+'" oninput="theme.elements[\\''+k+'\\'].ring_color=this.value;markDirty();"></div>';
  }}
  document.getElementById('elemControls').innerHTML=h;
}}

function refreshPreview(){{
  var nameEl=document.getElementById('sampleName');
  var nameq=(nameEl && nameEl.value.trim()) ? '&name='+encodeURIComponent(nameEl.value.trim()) : '';
  var url='/card-theme/preview.png?kind='+KIND+'&t='+encodeURIComponent(JSON.stringify(theme))+nameq+'&_='+Date.now();
  stage.style.backgroundImage="url('"+url+"')";
}}
function initBgUI(){{
  document.getElementById('bgInfo').textContent = HAS_BG ? '— background terpasang \\u2713' : '— belum ada background';
}}
function uploadBg(){{
  var f=document.getElementById('bgFile').files[0];
  if(!f){{alert('Pilih file gambar dulu.');return;}}
  var fd=new FormData(); fd.append('bg',f); fd.append('kind',KIND);
  fetch('/card-theme/bg',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ HAS_BG=true; initBgUI(); setOk('Background diupload & diterapkan.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload background.'); }}
  }});
}}
function deleteBg(){{
  if(!confirm('Hapus background kartu '+KIND+'?')) return;
  fetch('/card-theme/bg/delete',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{kind:KIND}})}}).then(r=>r.json()).then(function(d){{
    HAS_BG=false; initBgUI(); setOk('Background dihapus (kembali ke gradien).'); refreshPreview(); }});
}}
function saveTheme(){{
  fetch('/card-theme/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{kind:KIND,theme:theme}})}})
    .then(r=>r.json()).then(function(d){{ if(d.ok){{theme=d.theme; setOk('Tema disimpan & diterapkan ke bot.'); refreshPreview();}} else {{markDirty();}} }});
}}
function resetTheme(){{
  if(!confirm('Kembalikan kartu '+KIND+' ke tema default?')) return;
  fetch('/card-theme/reset',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{kind:KIND}})}}).then(r=>r.json()).then(function(d){{
    theme=d.theme; document.getElementById('cardEnabled').checked=!!theme.enabled;
    renderBoxes(); renderControls(); refreshPreview(); setOk('Direset ke default.'); }});
}}
function uploadFont(){{
  var f=document.getElementById('fontFile').files[0];
  if(!f){{alert('Pilih file font dulu.');return;}}
  var fd=new FormData(); fd.append('font',f); fd.append('kind',KIND);
  fetch('/card-theme/font',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ theme.font_file=d.font_file; document.getElementById('curFont').textContent=d.font_file; setOk('Font diupload & diterapkan.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload font.'); }}
  }});
}}

window.addEventListener('resize', renderBoxes);
renderBoxes(); renderControls(); initBgUI();
</script>"""
    return render_page(content)
