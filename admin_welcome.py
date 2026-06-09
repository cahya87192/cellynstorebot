"""admin_welcome.py - Editor teks pesan Welcome (sambutan member baru).

Blueprint terpisah (pola sama dgn admin_faq.py / admin_sticky.py). Mengubah
judul & isi embed sambutan join yang dikirim ke channel welcome. Cog
`cogs/welcome.py` membaca teks lewat utils.welcome.render_welcome(), jadi
perubahan di sini langsung dipakai pada member yang join berikutnya.

  - /welcome-editor         : form judul + isi (template) & pratinjau langsung
  - /welcome-editor/save    : simpan template (POST JSON)
  - /welcome-editor/reset   : kembalikan ke teks default (POST)

Catatan: channel welcome & gambar tetap diatur dari Discord (/setwelcome)
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


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


def _welcome_channel_id():
    """Ambil welcome_channel_id (read-only, untuk info) dari bot_state."""
    try:
        from utils.db import get_conn
        conn = get_conn()
        row = conn.execute(
            "SELECT value FROM bot_state WHERE key=?", ("welcome_channel_id",)
        ).fetchone()
        conn.close()
        return (row["value"] if row else "") or ""
    except Exception:
        return ""


@welcome_bp.route("/welcome-editor/save", methods=["POST"])
def save_welcome_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    title = payload.get("title")
    desc = payload.get("desc")
    if (title is None or not str(title).strip()) and (desc is None or not str(desc).strip()):
        return jsonify({"ok": False, "error": "Judul & isi tidak boleh kosong keduanya."}), 400
    welcomelib.save_welcome_texts(title=title, desc=desc)
    return jsonify({"ok": True})


@welcome_bp.route("/welcome-editor/reset", methods=["POST"])
def reset_welcome_route():
    g = _guard()
    if g:
        return g
    # String kosong -> baris dihapus -> kembali ke default.
    welcomelib.save_welcome_texts(title="", desc="")
    title, desc = welcomelib.load_welcome_texts()
    return jsonify({"ok": True, "title": title, "desc": desc})


@welcome_bp.route("/welcome-editor")
def page_welcome():
    g = _guard()
    if g:
        return g
    from admin import render_page

    title, desc = welcomelib.load_welcome_texts()
    ch_id = _welcome_channel_id()
    data = {
        "title": title,
        "desc": desc,
        "store": _STORE_NAME,
        "channel_id": ch_id,
    }
    data_json = json.dumps(data)

    content = """
<div class="page-header">
  <div class="page-title">Pesan Welcome <small>Teks sambutan member baru di channel welcome</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Channel &amp; gambar welcome diatur dari Discord (<code>/setwelcome</code>). Halaman ini mengubah <b>teksnya</b>.
    Perubahan langsung dipakai untuk member yang join berikutnya.
    <br>Placeholder: <code>{member}</code> (nama member), <code>{store}</code> (nama toko),
    <code>{count}</code> (nomor urut member). Channel welcome saat ini:
    <code id="chInfo"></code>
  </div>

  <div class="form-group">
    <label>Judul sambutan</label>
    <input type="text" id="wTitle" maxlength="256" oninput="updatePreview();markDirty();" style="width:100%;">
  </div>
  <div class="form-group">
    <label>Isi sambutan (boleh beberapa baris, mendukung **bold** Discord)</label>
    <textarea id="wDesc" rows="6" oninput="updatePreview();markDirty();" style="width:100%;"></textarea>
  </div>

  <button class="btn btn-primary btn-sm" onclick="saveWelcome()">💾 Simpan</button>
  <button class="btn btn-ghost btn-sm" onclick="resetWelcome()">↺ Kembalikan default</button>
  <span id="status" style="margin-left:.6rem;font-size:.85rem;"></span>

  <div style="margin-top:1.2rem;">
    <label style="font-size:.8rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;">Pratinjau</label>
    <div style="border-left:4px solid #00BFFF;background:var(--surface3);border-radius:6px;padding:.8rem 1rem;margin-top:.4rem;">
      <div id="pvTitle" style="font-weight:700;margin-bottom:.4rem;"></div>
      <div id="pvDesc" style="white-space:pre-wrap;color:var(--text);"></div>
    </div>
  </div>
</div></div>

<script>
var DATA = DATA_JSON;
var SAMPLE = {member:"Andi", store:DATA.store || "Store", count:"123"};

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function render(tpl){
  return esc(tpl)
    .replace(/\\{member\\}/g, esc(SAMPLE.member))
    .replace(/\\{store\\}/g, esc(SAMPLE.store))
    .replace(/\\{count\\}/g, esc(SAMPLE.count))
    .replace(/\\*\\*(.+?)\\*\\*/g, "<b>$1</b>");
}
function updatePreview(){
  document.getElementById('pvTitle').innerHTML = render(document.getElementById('wTitle').value);
  document.getElementById('pvDesc').innerHTML = render(document.getElementById('wDesc').value);
}
function setStatus(msg, ok){
  document.getElementById('status').innerHTML =
    '<span style="color:var(--'+(ok?'success':'warning')+')">'+(ok?'✓ ':'● ')+msg+'</span>';
}
function markDirty(){ setStatus('Perubahan belum disimpan', false); }

function saveWelcome(){
  fetch('/welcome-editor/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({title:document.getElementById('wTitle').value,
                         desc:document.getElementById('wDesc').value})})
    .then(function(r){return r.json();}).then(function(d){
      setStatus(d.ok ? 'Tersimpan.' : (d.error||'Gagal menyimpan'), !!d.ok);
    });
}
function resetWelcome(){
  if(!confirm('Kembalikan judul & isi ke teks default?')) return;
  fetch('/welcome-editor/reset',{method:'POST'})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){
        document.getElementById('wTitle').value = d.title;
        document.getElementById('wDesc').value = d.desc;
        updatePreview();
        setStatus('Dikembalikan ke default.', true);
      } else { setStatus('Gagal reset', false); }
    });
}

document.getElementById('wTitle').value = DATA.title;
document.getElementById('wDesc').value = DATA.desc;
document.getElementById('chInfo').textContent = DATA.channel_id ? DATA.channel_id : '(belum diset)';
updatePreview();
</script>"""
    content = content.replace("DATA_JSON", data_json)
    return render_page(content)
