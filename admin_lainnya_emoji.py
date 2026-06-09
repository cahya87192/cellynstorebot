"""admin_lainnya_emoji.py - Editor Emoji Katalog "Lainnya" untuk Admin Panel.

Blueprint terpisah (pola sama dgn admin_faq.py). Owner bisa mengganti emoji
per GRUP & per KATEGORI tanpa ubah kode; override disimpan di bot_state
(key lainnya_emoji_overrides) dan dipakai oleh cogs/lainnya.py
(_group_emoji/_category_emoji) dengan urutan: override DB > map statis > fallback.

  - /lainnya/emoji        : halaman editor (input emoji per grup/kategori)
  - /lainnya/emoji/save   : simpan override (POST JSON)
  - /lainnya/emoji/reset  : hapus semua override (kembali ke default)

Mengambil daftar & default emoji dari cogs/lainnya_catalog.py (modul DATA murni,
tanpa import discord) agar aman di-import dari panel Flask.
"""
import json

from flask import Blueprint, request, session, redirect, jsonify

from utils import catalog_emoji_settings as emoji_settings
from cogs.lainnya_catalog import (
    GROUP_ORDER, GROUP_EMOJI, CATEGORY_EMOJI, CATEGORY_GROUP,
)

lainnya_emoji_bp = Blueprint("lainnya_emoji_bp", __name__)


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


def _build_rows(overrides):
    """Susun data grup & kategori untuk ditampilkan di editor."""
    ov_g = overrides.get("groups", {})
    ov_c = overrides.get("categories", {})
    groups = [
        {"name": g, "default": GROUP_EMOJI.get(g, ""), "override": ov_g.get(g, "")}
        for g in GROUP_ORDER
    ]
    # Kategori dikelompokkan per grup, urut sesuai GROUP_ORDER lalu abjad.
    cats_by_group = {}
    for cat, grp in CATEGORY_GROUP.items():
        cats_by_group.setdefault(grp, []).append(cat)
    categories = []
    seen_groups = list(GROUP_ORDER) + [
        g for g in cats_by_group if g not in GROUP_ORDER
    ]
    for grp in seen_groups:
        for cat in sorted(cats_by_group.get(grp, [])):
            categories.append({
                "name": cat,
                "group": grp,
                "default": CATEGORY_EMOJI.get(cat, ""),
                "override": ov_c.get(cat, ""),
            })
    return groups, categories


@lainnya_emoji_bp.route("/lainnya/emoji/save", methods=["POST"])
def save_route():
    g = _guard()
    if g:
        return g
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        payload = {}
    saved = emoji_settings.save_overrides(payload)
    return jsonify({"ok": True, "overrides": saved})


@lainnya_emoji_bp.route("/lainnya/emoji/reset", methods=["POST"])
def reset_route():
    g = _guard()
    if g:
        return g
    emoji_settings.save_overrides({})
    return jsonify({"ok": True})


@lainnya_emoji_bp.route("/lainnya/emoji")
def page():
    g = _guard()
    if g:
        return g
    from admin import render_page

    overrides = emoji_settings.load_overrides()
    groups, categories = _build_rows(overrides)
    data_json = json.dumps({"groups": groups, "categories": categories})

    content = """
<div class="page-header">
  <div class="page-title">Emoji Katalog Lainnya <small>Ganti emoji grup &amp; kategori (override default)</small></div>
  <div class="page-actions">
    <button class="btn btn-primary" onclick="saveAll()">💾 Simpan</button>
    <button class="btn btn-ghost" onclick="resetAll()">↩️ Reset Default</button>
  </div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Isi dengan <b>emoji unicode</b> (mis. 🎮) atau <b>custom emoji</b> server kamu
    (format <code>&lt;:nama:id&gt;</code> / <code>&lt;a:nama:id&gt;</code>).
    Kosongkan untuk memakai default. Setelah simpan, refresh embed katalog
    (<code>!lainnyarefresh</code> atau buka ulang menu) agar berubah.
    <br><small style="color:var(--muted)">Catatan: di server selain Cellyn, set
    <code>LAINNYA_USE_CUSTOM_EMOJI=false</code> agar custom emoji yang tak tersedia di-fallback ke unicode.</small>
  </div>
  <div style="display:flex;gap:.5rem;margin-bottom:1rem;">
    <button class="btn btn-ghost btn-sm" onclick="showTab('groups')" id="tab-groups">Grup</button>
    <button class="btn btn-ghost btn-sm" onclick="showTab('categories')" id="tab-categories">Kategori</button>
  </div>
  <div id="list"></div>
  <div id="status" style="margin-top:.6rem;font-size:.85rem;"></div>
</div></div>

<script>
var D = DATA_JSON;
var GOV = {}; var COV = {};
D.groups.forEach(function(r){ GOV[r.name] = r.override || ""; });
D.categories.forEach(function(r){ COV[r.name] = r.override || ""; });
var TAB = 'groups';

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function setStatus(msg, ok){
  document.getElementById('status').innerHTML =
    '<span style="color:var(--'+(ok?'success':'warning')+')">'+(ok?'✓ ':'● ')+msg+'</span>';
}
function markDirty(){ setStatus('Perubahan belum disimpan', false); }

function rowHtml(r, kind){
  var sub = kind==='g' ? '' : ' <small style="color:var(--muted)">('+esc(r.group)+')</small>';
  var def = r.default ? esc(r.default) : '—';
  return '<div class="card" style="margin-bottom:.5rem;border:1px solid var(--border);">'
    + '<div class="card-body" style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap;">'
    + '<div style="flex:1 1 240px;min-width:200px;font-weight:600;">'+esc(r.name)+sub+'</div>'
    + '<div style="flex:0 0 auto;color:var(--muted);font-size:.85rem;">default: <span style="font-size:1.1rem">'+def+'</span></div>'
    + '<div style="flex:0 0 200px;"><input type="text" placeholder="(pakai default)" value="'+esc(r.override||'')+'" '
    + 'data-kind="'+kind+'" data-name="'+esc(r.name)+'" oninput="setOv(this);"></div>'
    + '</div></div>';
}
function setOv(inp){
  var kind = inp.getAttribute('data-kind');
  var name = inp.getAttribute('data-name');
  (kind==='g'?GOV:COV)[name] = inp.value;
  markDirty();
}

function render(){
  var rows = (TAB==='groups') ? D.groups : D.categories;
  var kind = (TAB==='groups') ? 'g' : 'c';
  var html = '';
  rows.forEach(function(r){ r.override = (kind==='g'?GOV:COV)[r.name]; html += rowHtml(r, kind); });
  document.getElementById('list').innerHTML = html;
  document.getElementById('tab-groups').className = 'btn btn-sm ' + (TAB==='groups'?'btn-primary':'btn-ghost');
  document.getElementById('tab-categories').className = 'btn btn-sm ' + (TAB==='categories'?'btn-primary':'btn-ghost');
}
function showTab(t){ TAB=t; render(); }

function cleanMap(m){ var o={}; Object.keys(m).forEach(function(k){ if(m[k] && m[k].trim()) o[k]=m[k].trim(); }); return o; }
function saveAll(){
  fetch('/lainnya/emoji/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({groups:cleanMap(GOV), categories:cleanMap(COV)})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ GOV={}; COV={};
        Object.keys(d.overrides.groups||{}).forEach(function(k){GOV[k]=d.overrides.groups[k];});
        Object.keys(d.overrides.categories||{}).forEach(function(k){COV[k]=d.overrides.categories[k];});
        render(); setStatus('Tersimpan. Refresh embed katalog di Discord agar berubah.', true); }
      else { setStatus('Gagal menyimpan', false); }
    });
}
function resetAll(){
  if(!confirm('Hapus semua override emoji (kembali ke default)?')) return;
  fetch('/lainnya/emoji/reset',{method:'POST'}).then(function(r){return r.json();}).then(function(){
    location.reload();
  });
}
render();
</script>"""
    content = content.replace("DATA_JSON", data_json)
    return render_page(content)
