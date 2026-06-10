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
  <div>
    <h2>PAGE_TITLE</h2>
    <p class="text-muted">PAGE_SUB</p>
  </div>
</div>
<div class="card" style="margin-bottom:1rem;"><div class="card-body">
  <div class="note" style="margin:0;">PAGE_INTRO</div>
</div></div>
<div id="sections"></div>

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
    '<span style="color:var(--'+(ok?'success':'warning')+');font-weight:600;">'+(ok?'\\u2713 ':'\\u25CF ')+msg+'</span>';
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
      ? s.placeholders.map(function(p){
          return '<code style="background:var(--accent-soft);color:var(--accent);border-radius:6px;padding:.1rem .4rem;font-size:.72rem;">'+esc(p)+'</code>';
        }).join(' ')
      : '<span class="text-muted" style="font-size:.75rem;">Tanpa placeholder</span>';
    html += '<div class="card" style="margin-bottom:1rem;">'
      + '<div class="card-header" style="display:flex;justify-content:space-between;align-items:center;gap:.6rem;flex-wrap:wrap;">'
      + '<span style="font-weight:700;">'+esc(s.label)+'</span>'
      + '<span style="display:flex;gap:.3rem;flex-wrap:wrap;align-items:center;">'+chips+'</span>'
      + '</div>'
      + '<div class="card-body">'
      + '<div class="form-group" style="margin:0 0 .7rem 0;"><textarea id="txt_'+s.kind+'" rows="ROWS_VAL" style="width:100%;" '
      + 'oninput="updatePreview('+i+');setStatus(\\''+s.kind+'\\',\\'Belum disimpan\\',false);"></textarea></div>'
      + '<div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;">'
      + '<button class="btn btn-primary btn-sm" onclick="saveSec('+i+')">Simpan</button>'
      + '<button class="btn btn-ghost btn-sm" onclick="resetSec('+i+')">Default</button>'
      + '<span id="st_'+s.kind+'" style="margin-left:.2rem;font-size:.82rem;"></span>'
      + '</div>'
      + '<div style="margin-top:.9rem;">'
      + '<div class="text-muted" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;margin-bottom:.35rem;">Pratinjau</div>'
      + '<div style="border-left:3px solid var(--accent);background:var(--surface3);border-radius:8px;padding:.75rem .95rem;">'
      + '<div id="pv_'+s.kind+'" style="color:var(--text);line-height:1.5;"></div></div>'
      + '</div>'
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
