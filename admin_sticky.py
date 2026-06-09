"""admin_sticky.py - Kelola Sticky Message dari Admin Panel.

Blueprint terpisah (pola sama dgn admin_faq.py). Sticky message umum dipasang
per-channel lewat command Discord `/stick_msg` (lihat cogs/sticky.py) dan
tersimpan di tabel `bot_state` key `sticky_messages`. Halaman ini memungkinkan
admin MENGUBAH isi (teks/embed) atau MENGHAPUS sticky yang sudah ada tanpa
harus buka Discord.

  - /sticky-manager         : daftar sticky aktif + form edit per channel
  - /sticky-manager/save    : simpan isi satu sticky (POST JSON)
  - /sticky-manager/delete  : hapus satu sticky dari daftar (POST JSON)

Catatan penting (ditampilkan juga di UI):
  * Sticky BARU tetap dibuat dari Discord (`/stick_msg`) karena butuh channel &
    izin bot untuk mengirim pesan. Panel ini hanya mengelola yang sudah ada.
  * Perubahan teks/embed berlaku saat bot mengirim-ulang sticky berikutnya
    (otomatis ketika channel ramai), bukan langsung mengedit pesan lama.
  * Menghapus di sini menghentikan bot mengirim-ulang sticky tersebut.

render_page di-import lazily di dalam view (hindari circular import).
"""
import json

from flask import Blueprint, request, session, redirect, jsonify

from utils import sticky as stickylib

try:
    from utils.config import STORE_NAME as _STORE_NAME
except Exception:
    _STORE_NAME = "Store"

sticky_bp = Blueprint("sticky_bp", __name__)


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@sticky_bp.route("/sticky-manager/save", methods=["POST"])
def save_sticky_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    channel_id = payload.get("channel_id")
    m = stickylib.load_sticky_map()
    m, ok = stickylib.update_entry_content(
        m, channel_id,
        content=payload.get("content"),
        title=payload.get("title"),
        description=payload.get("description"),
        color_hex=payload.get("color"),
        footer=_STORE_NAME,
    )
    if not ok:
        return jsonify({"ok": False,
                        "error": "Isi minimal teks ATAU judul/isi embed, dan channel harus ada."}), 400
    stickylib.save_sticky_map(m)
    return jsonify({"ok": True})


@sticky_bp.route("/sticky-manager/delete", methods=["POST"])
def delete_sticky_route():
    g = _guard()
    if g:
        return g
    payload = request.get_json(force=True, silent=True) or {}
    m = stickylib.load_sticky_map()
    m, removed = stickylib.remove_entry(m, payload.get("channel_id"))
    if removed is None:
        return jsonify({"ok": False, "error": "Sticky tidak ditemukan."}), 404
    stickylib.save_sticky_map(m)
    return jsonify({"ok": True})


@sticky_bp.route("/sticky-manager")
def page_sticky():
    g = _guard()
    if g:
        return g
    from admin import render_page

    m = stickylib.load_sticky_map()
    entries = []
    for cid, entry in m.items():
        f = stickylib.entry_fields(entry)
        f["channel_id"] = str(cid)
        f["summary"] = stickylib.entry_summary(entry)
        entries.append(f)
    entries.sort(key=lambda e: e["channel_id"])
    entries_json = json.dumps(entries)

    content = """
<div class="page-header">
  <div class="page-title">Kelola Sticky Message <small>Ubah/hapus sticky aktif per channel</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Sticky <b>baru</b> dibuat dari Discord (<code>/stick_msg</code>) karena butuh channel &amp; izin bot.
    Halaman ini mengelola yang sudah ada: ubah teks/embed atau hapus.
    <br>Perubahan berlaku saat bot <b>mengirim-ulang</b> sticky berikutnya (otomatis saat channel ramai),
    bukan langsung mengedit pesan lama. Menghapus di sini menghentikan bot mengirim-ulang sticky tersebut.
  </div>
  <div id="stickyList"></div>
  <div id="status" style="margin-top:.6rem;font-size:.85rem;"></div>
</div></div>

<script>
var ENTRIES = ENTRIES_JSON;

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function setStatus(msg, ok){
  document.getElementById('status').innerHTML =
    '<span style="color:var(--'+(ok?'success':'warning')+')">'+(ok?'✓ ':'● ')+msg+'</span>';
}

function render(){
  var html = '';
  ENTRIES.forEach(function(e, i){
    html += '<div class="card" style="margin-bottom:.8rem;border:1px solid var(--border);">'
      + '<div class="card-body">'
      + '<div style="font-weight:600;margin-bottom:.5rem;">Channel ID: <code>'+esc(e.channel_id)+'</code></div>'
      + '<div class="form-group"><label>Teks sticky (body)</label>'
      + '<textarea rows="3" oninput="ENTRIES['+i+'].content=this.value;markDirty();" '
      + 'placeholder="Teks bebas. Kosongkan bila hanya pakai embed.">'+esc(e.content)+'</textarea></div>'
      + '<div class="form-group"><label>Judul embed (opsional)</label>'
      + '<input type="text" maxlength="256" value="'+esc(e.title)+'" '
      + 'oninput="ENTRIES['+i+'].title=this.value;markDirty();"></div>'
      + '<div class="form-group"><label>Isi embed (opsional)</label>'
      + '<textarea rows="3" oninput="ENTRIES['+i+'].description=this.value;markDirty();">'+esc(e.description)+'</textarea></div>'
      + '<div class="form-group"><label>Warna embed (hex)</label>'
      + '<input type="text" maxlength="7" value="'+esc(e.color_hex)+'" placeholder="#5865F2" '
      + 'oninput="ENTRIES['+i+'].color_hex=this.value;markDirty();" style="max-width:140px;"></div>'
      + '<button class="btn btn-primary btn-sm" onclick="saveEntry('+i+')">💾 Simpan</button> '
      + '<button class="btn btn-ghost btn-sm" onclick="delEntry('+i+')">🗑️ Hapus</button>'
      + '</div></div>';
  });
  if(!ENTRIES.length) html = '<div class="empty">Belum ada sticky aktif. Pasang dari Discord dengan <code>/stick_msg</code>.</div>';
  document.getElementById('stickyList').innerHTML = html;
}
function markDirty(){ setStatus('Perubahan belum disimpan', false); }

function saveEntry(i){
  var e = ENTRIES[i];
  fetch('/sticky-manager/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({channel_id:e.channel_id, content:e.content, title:e.title,
      description:e.description, color:e.color_hex})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ setStatus('Tersimpan. Sticky channel '+e.channel_id+' akan diperbarui saat dikirim-ulang.', true); }
      else { setStatus(d.error || 'Gagal menyimpan', false); }
    });
}
function delEntry(i){
  var e = ENTRIES[i];
  if(!confirm('Hapus sticky di channel '+e.channel_id+'? Bot berhenti mengirim-ulang sticky ini.')) return;
  fetch('/sticky-manager/delete',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({channel_id:e.channel_id})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ ENTRIES.splice(i,1); render(); setStatus('Sticky dihapus.', true); }
      else { setStatus(d.error || 'Gagal menghapus', false); }
    });
}
render();
</script>"""
    content = content.replace("ENTRIES_JSON", entries_json)
    return render_page(content)
