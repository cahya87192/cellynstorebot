"""Logika murni render halaman editor teks panel admin (tanpa Flask).

Bagian HTML/JS halaman editor teks yang berulang dipusatkan di sini supaya bisa
diuji tanpa Flask. Glue Flask (blueprint, request, render_page) ada di
`admin_text_editor.py` yang mengimpor modul ini.
"""
import json


def flat_sample_resolver(sample_dict):
    """Resolver sample 'flat': hanya sertakan placeholder yang ada di default spec."""
    def resolve(kind, spec):
        return {k: v for k, v in sample_dict.items() if ("{" + k + "}") in spec["default"]}
    return resolve


def per_kind_sample_resolver(samples_by_kind):
    """Resolver sample per-jenis (kind -> dict contoh)."""
    def resolve(kind, spec):
        return samples_by_kind.get(kind, {})
    return resolve


def build_sections(specs, load_text, sample_for=None):
    """Bangun daftar section untuk dikirim ke front-end."""
    sections = []
    for kind, spec in specs.items():
        sample = sample_for(kind, spec) if sample_for else {}
        sections.append({
            "kind": kind,
            "label": spec["label"],
            "text": load_text(kind),
            "placeholders": list(spec["placeholders"]),
            "sample": sample,
        })
    return sections


# Template halaman editor. Token diganti via str.replace (BUKAN .format) supaya
# kurung kurawal di JS aman. SECTIONS_JSON diganti TERAKHIR agar isi JSON tidak
# ikut ter-scan token lain.
_TEMPLATE = """
<div class="page-header">
  <div class="page-title">PAGE_TITLE <small>PAGE_SUB</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">PAGE_INTRO</div>
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
  document.getElementById('pv_'+s.kind).innerHTML =
    render(document.getElementById('txt_'+s.kind).value, s.sample);
}

function build(){
  var html = '';
  SECTIONS.forEach(function(s, i){
    var chips = s.placeholders.length
      ? 'Placeholder: ' + s.placeholders.map(function(p){ return '<code>'+esc(p)+'</code>'; }).join(' ')
      : '<span style="color:var(--muted)">Tanpa placeholder</span>';
    html += '<div class="card" style="margin-bottom:1rem;border:1px solid var(--border);"><div class="card-body">'
      + '<div style="font-weight:700;margin-bottom:.2rem;">'+esc(s.label)+'</div>'
      + '<div style="font-size:.78rem;color:var(--muted);margin-bottom:.7rem;">'+chips+'</div>'
      + '<div class="form-group"><textarea id="txt_'+s.kind+'" rows="ROWS_VAL" style="width:100%;" '
      + 'oninput="updatePreview('+i+');setStatus(\\''+s.kind+'\\',\\'Belum disimpan\\',false);"></textarea></div>'
      + '<button class="btn btn-primary btn-sm" onclick="saveSec('+i+')">💾 Simpan</button> '
      + '<button class="btn btn-ghost btn-sm" onclick="resetSec('+i+')">↺ Default</button>'
      + '<span id="st_'+s.kind+'" style="margin-left:.6rem;font-size:.85rem;"></span>'
      + '<div style="margin-top:.9rem;border-left:4px solid var(--accent);background:var(--surface3);border-radius:6px;padding:.7rem .9rem;">'
      + '<div id="pv_'+s.kind+'" style="color:var(--text);"></div></div>'
      + '</div></div>';
  });
  document.getElementById('sections').innerHTML = html;
  SECTIONS.forEach(function(s, i){
    document.getElementById('txt_'+s.kind).value = s.text;
    updatePreview(i);
  });
}

function saveSec(i){
  var s = SECTIONS[i];
  fetch('BASE_ROUTE/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({kind:s.kind, text:document.getElementById('txt_'+s.kind).value})})
    .then(function(r){return r.json();}).then(function(d){
      setStatus(s.kind, d.ok ? 'Tersimpan.' : (d.error||'Gagal menyimpan'), !!d.ok);
    });
}
function resetSec(i){
  var s = SECTIONS[i];
  if(!confirm('Kembalikan teks "'+s.label+'" ke default?')) return;
  fetch('BASE_ROUTE/reset',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({kind:s.kind})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){
        document.getElementById('txt_'+s.kind).value = d.text;
        updatePreview(i);
        setStatus(s.kind, 'Dikembalikan ke default.', true);
      } else { setStatus(s.kind, d.error||'Gagal reset', false); }
    });
}
build();
</script>"""


def editor_content(*, title, subtitle, intro, base_route, sections, rows=3):
    """Bangun HTML halaman editor (murni, tanpa Flask). Aman untuk diuji."""
    sections_json = json.dumps(sections)
    out = _TEMPLATE
    out = out.replace("ROWS_VAL", str(int(rows)))
    out = out.replace("BASE_ROUTE", base_route)
    out = out.replace("PAGE_TITLE", title)
    out = out.replace("PAGE_SUB", subtitle)
    out = out.replace("PAGE_INTRO", intro)
    out = out.replace("SECTIONS_JSON", sections_json)
    return out
