"""admin_topspender_theme.py - Editor Kartu Top Spender (leaderboard gambar).

Blueprint terpisah (pola sama dgn admin_rating_theme.py) tapi berbasis FORM
(bukan drag-drop) karena leaderboard adalah daftar baris berulang:
  - /topspender-card             : halaman editor (setting warna/rows/opacity + preview)
  - /topspender-card/preview.png : render kartu contoh dgn tema saat ini
  - /topspender-card/save        : simpan tema (POST JSON)
  - /topspender-card/reset       : kembalikan ke default
  - /topspender-card/font        : upload file font .ttf/.otf (POST file)
  - /topspender-card/bg          : upload background (POST file)
  - /topspender-card/bg/delete   : hapus background

Background tunggal: data/topspendercardbg.<ext>. Font kustom: data/topspender_font.<ext>.
Teks judul/footer untuk versi EMBED tetap diatur di editor "Papan Top Spender".
render_page di-import lazily di dalam view (hindari circular import).
"""
import os
import json

from flask import Blueprint, request, session, redirect, Response, jsonify

from utils import topspender_theme as tstheme

topspender_card_bp = Blueprint("topspender_card_bp", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ALLOWED_FONT_EXTS = (".ttf", ".otf")
ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
TS_BG_BASE = "topspendercardbg"

# Data contoh untuk pratinjau (nama + total belanja).
SAMPLE = [
    ("Budi Santoso", 2450000), ("Sarah Wijaya", 1980000), ("Andi Pratama", 1520000),
    ("Dewi Kartika", 990000), ("Rizky Hidayat", 870000), ("Maya Lestari", 640000),
    ("Toni Saputra", 500000), ("Vina Anggraini", 430000), ("Galih Nugroho", 310000),
    ("Putri Ayu", 250000), ("Hendra", 180000), ("Citra", 120000),
]

# Field warna yang ditampilkan di editor (key -> label).
COLOR_FIELDS = [
    ("title", "Judul"),
    ("subtitle", "Subjudul"),
    ("name", "Nama"),
    ("rank", "Peringkat / sub"),
    ("amount", "Nominal"),
    ("total", "Total (footer)"),
    ("divider", "Garis pemisah"),
]


def _bg_path():
    for ext in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, TS_BG_BASE + ext)
        if os.path.exists(p):
            return p
    return None


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@topspender_card_bp.route("/topspender-card/preview.png")
def preview_png():
    g = _guard()
    if g:
        return g
    raw = request.args.get("t")
    theme = tstheme.merge_theme(raw) if raw else tstheme.load_theme()
    spenders = [{"user_id": i, "total": amt, "name": nm}
                for i, (nm, amt) in enumerate(SAMPLE, 1)]
    try:
        from cogs.profile import render_topspender_card
        buf = render_topspender_card(spenders, "Juni 2026", theme=theme,
                                     bg_path=_bg_path(), avatars=None)
        return Response(buf.getvalue(), mimetype="image/png")
    except Exception as e:
        png_1x1 = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                   b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
                   b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        return Response(png_1x1, mimetype="image/png",
                        headers={"X-Render-Error": str(e)[:200]})


@topspender_card_bp.route("/topspender-card/save", methods=["POST"])
def save_theme_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    if "font_file" not in payload:
        payload["font_file"] = tstheme.load_theme().get("font_file")
    theme = tstheme.save_theme(payload)
    return jsonify({"ok": True, "theme": theme})


@topspender_card_bp.route("/topspender-card/reset", methods=["POST"])
def reset_theme_route():
    g = _guard()
    if g:
        return g
    theme = tstheme.save_theme(tstheme.default_theme())
    return jsonify({"ok": True, "theme": theme})


@topspender_card_bp.route("/topspender-card/font", methods=["POST"])
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
    fname = "topspender_font" + ext
    for e in ALLOWED_FONT_EXTS:
        old = os.path.join(DATA_DIR, "topspender_font" + e)
        if os.path.exists(old) and e != ext:
            try:
                os.remove(old)
            except Exception:
                pass
    f.save(os.path.join(DATA_DIR, fname))
    theme = tstheme.load_theme()
    theme["font_file"] = fname
    tstheme.save_theme(theme)
    return jsonify({"ok": True, "font_file": fname})


@topspender_card_bp.route("/topspender-card/bg", methods=["POST"])
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
        old = os.path.join(DATA_DIR, TS_BG_BASE + e)
        if os.path.exists(old):
            try:
                os.remove(old)
            except Exception:
                pass
    f.save(os.path.join(DATA_DIR, TS_BG_BASE + ext))
    return jsonify({"ok": True, "has_bg": True})


@topspender_card_bp.route("/topspender-card/bg/delete", methods=["POST"])
def delete_bg():
    g = _guard()
    if g:
        return g
    removed = False
    for e in ALLOWED_IMAGE_EXTS:
        p = os.path.join(DATA_DIR, TS_BG_BASE + e)
        if os.path.exists(p):
            try:
                os.remove(p)
                removed = True
            except Exception:
                pass
    return jsonify({"ok": True, "removed": removed, "has_bg": False})


def _color_rows(theme):
    out = ""
    for key, label in COLOR_FIELDS:
        val = theme["colors"].get(key, "#FFFFFF")
        out += (
            f'<div class="form-group" style="display:flex;align-items:center;'
            f'justify-content:space-between;gap:.5rem;">'
            f'<label style="margin:0;">{label}</label>'
            f'<input type="color" value="{val}" '
            f'oninput="theme.colors[\'{key}\']=this.value;markDirty();"></div>'
        )
    return out


@topspender_card_bp.route("/topspender-card")
def page_card():
    g = _guard()
    if g:
        return g
    from admin import render_page

    theme = tstheme.load_theme()
    theme_json = json.dumps(theme)
    default_json = json.dumps(tstheme.default_theme())
    has_bg_json = json.dumps(_bg_path() is not None)
    cur_font = theme.get("font_file") or "(default sistem)"
    enabled_attr = "checked" if theme.get("enabled") else ""
    avatars_attr = "checked" if theme.get("show_avatars") else ""

    content = f"""
<style>
.tsp-color-grid{{display:grid;grid-template-columns:1fr 1fr;gap:.2rem .9rem;}}
@media(max-width:560px){{.tsp-color-grid{{grid-template-columns:1fr;}}}}
@media(min-width:920px){{.tsp-stage{{position:sticky;top:1.5rem;align-self:flex-start;}}}}
</style>
<div class="page-header">
  <div class="page-title">Kartu Top Spender <small>Leaderboard sebagai gambar — warna, jumlah baris &amp; background</small></div>
</div>
<div class="card"><div class="card-body" style="display:flex;flex-wrap:wrap;gap:1.5rem;align-items:flex-start;">
  <div class="tsp-stage" style="flex:1 1 460px;min-width:280px;">
    <div style="font-size:.8rem;color:var(--muted);margin-bottom:.5rem;">
      Pratinjau (data contoh). Lebar kartu {tstheme.CARD_W}px, tinggi mengikuti jumlah baris.</div>
    <img id="prev" src="/topspender-card/preview.png" alt="preview"
      style="width:100%;max-width:520px;border-radius:14px;border:1px solid var(--border);display:block;">
    <div style="display:flex;gap:.5rem;margin-top:.8rem;flex-wrap:wrap;">
      <button class="btn btn-primary" onclick="saveTheme()">Simpan</button>
      <button class="btn btn-ghost" onclick="refreshPreview()">Perbarui Pratinjau</button>
      <button class="btn btn-ghost" onclick="resetTheme()">Reset Default</button>
    </div>
    <div id="status" style="margin-top:.6rem;font-size:.85rem;"></div>
  </div>
  <div style="flex:1 1 320px;min-width:280px;">
    <div class="form-group">
      <label style="display:flex;align-items:center;gap:.5rem;">
        <input type="checkbox" id="cardEnabled" {enabled_attr}
          onchange="theme.enabled=this.checked;markDirty();" style="width:auto;">
        Aktifkan leaderboard sebagai gambar
      </label>
      <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem;">Jika nonaktif, leaderboard tetap diposting sebagai embed teks klasik.</div>
    </div>
    <div class="form-group">
      <label style="display:flex;align-items:center;gap:.5rem;">
        <input type="checkbox" id="showAvatars" {avatars_attr}
          onchange="theme.show_avatars=this.checked;markDirty();" style="width:auto;">
        Tampilkan foto profil + medali untuk Top 3
      </label>
    </div>
    <div class="form-group">
      <label>Jumlah baris ditampilkan: <b id="rowsVal">{theme['rows']}</b></label>
      <input type="range" min="{tstheme.ROWS_MIN}" max="{tstheme.ROWS_MAX}" value="{theme['rows']}"
        oninput="theme.rows=+this.value;document.getElementById('rowsVal').textContent=this.value;markDirty();">
    </div>
    <div class="form-group">
      <label>Opacity panel: <b id="opVal">{theme['panel_opacity']}</b></label>
      <input type="range" min="0" max="255" value="{theme['panel_opacity']}"
        oninput="theme.panel_opacity=+this.value;document.getElementById('opVal').textContent=this.value;markDirty();">
    </div>
    <label style="font-weight:600;font-size:.85rem;">Warna teks</label>
    <div class="tsp-color-grid" style="margin:.4rem 0 1rem;">{_color_rows(theme)}</div>
    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;gap:.5rem;">
      <label style="margin:0;">Gradien latar (atas)</label>
      <input type="color" value="{theme['bg_color1']}" oninput="theme.bg_color1=this.value;markDirty();">
    </div>
    <div class="form-group" style="display:flex;align-items:center;justify-content:space-between;gap:.5rem;">
      <label style="margin:0;">Gradien latar (bawah)</label>
      <input type="color" value="{theme['bg_color2']}" oninput="theme.bg_color2=this.value;markDirty();">
    </div>
    <div style="font-size:.78rem;color:var(--muted);margin:-.2rem 0 1rem;">Gradien dipakai bila tidak ada background gambar.</div>
    <div class="form-group">
      <label>Background Kartu <small style="color:var(--muted)" id="bgInfo"></small></label>
      <input type="file" id="bgFile" accept=".png,.jpg,.jpeg,.webp">
      <div style="display:flex;gap:.5rem;margin-top:.4rem;flex-wrap:wrap;">
        <button class="btn btn-ghost btn-sm" onclick="uploadBg()">Upload Background</button>
        <button class="btn btn-ghost btn-sm" onclick="deleteBg()">Hapus Background</button>
      </div>
    </div>
    <div class="form-group">
      <label>Font Kustom — saat ini: <b id="curFont">{cur_font}</b></label>
      <input type="file" id="fontFile" accept=".ttf,.otf">
      <button class="btn btn-ghost btn-sm" style="margin-top:.4rem;" onclick="uploadFont()">Upload Font (.ttf/.otf)</button>
    </div>
    <div class="note" style="margin-top:1rem;">Teks judul/benefit untuk versi <b>embed</b> diatur di menu <b>Papan Top Spender</b>. Kartu gambar memakai judul ringkas (nama bulan) &amp; total otomatis.</div>
  </div>
</div></div>

<script>
var THEME = {theme_json};
var DEFAULT_THEME = {default_json};
var HAS_BG = {has_bg_json};
var theme = JSON.parse(JSON.stringify(THEME));

var _previewTimer=null;
function markDirty(){{
  document.getElementById('status').innerHTML='<span style="color:var(--warning)">\\u25CF Perubahan belum disimpan (pratinjau diperbarui...)</span>';
  if(_previewTimer) clearTimeout(_previewTimer);
  _previewTimer=setTimeout(refreshPreview, 400);
}}
function setOk(m){{ document.getElementById('status').innerHTML='<span style="color:var(--success)">\\u2713 '+m+'</span>'; }}

function refreshPreview(){{
  var url='/topspender-card/preview.png?t='+encodeURIComponent(JSON.stringify(theme))+'&_='+Date.now();
  document.getElementById('prev').src=url;
}}
function initBgUI(){{
  document.getElementById('bgInfo').textContent = HAS_BG ? '— background terpasang \\u2713' : '— belum ada background';
}}
function saveTheme(){{
  fetch('/topspender-card/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(theme)}})
    .then(r=>r.json()).then(function(d){{ if(d.ok){{theme=d.theme; setOk('Tema disimpan & diterapkan ke bot.'); refreshPreview();}} else {{markDirty();}} }});
}}
function resetTheme(){{
  if(!confirm('Kembalikan ke tema default?')) return;
  fetch('/topspender-card/reset',{{method:'POST'}}).then(r=>r.json()).then(function(d){{
    location.reload(); }});
}}
function uploadBg(){{
  var f=document.getElementById('bgFile').files[0];
  if(!f){{alert('Pilih file gambar dulu.');return;}}
  var fd=new FormData(); fd.append('bg',f);
  fetch('/topspender-card/bg',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ HAS_BG=true; initBgUI(); setOk('Background diupload & diterapkan.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload background.'); }}
  }});
}}
function deleteBg(){{
  if(!confirm('Hapus background kartu Top Spender?')) return;
  fetch('/topspender-card/bg/delete',{{method:'POST'}}).then(r=>r.json()).then(function(d){{
    HAS_BG=false; initBgUI(); setOk('Background dihapus (kembali ke gradien).'); refreshPreview(); }});
}}
function uploadFont(){{
  var f=document.getElementById('fontFile').files[0];
  if(!f){{alert('Pilih file font dulu.');return;}}
  var fd=new FormData(); fd.append('font',f);
  fetch('/topspender-card/font',{{method:'POST',body:fd}}).then(r=>r.json()).then(function(d){{
    if(d.ok){{ theme.font_file=d.font_file; document.getElementById('curFont').textContent=d.font_file; setOk('Font diupload & diterapkan.'); refreshPreview(); }}
    else {{ alert(d.error||'Gagal upload font.'); }}
  }});
}}
initBgUI();
</script>"""
    return render_page(content)
