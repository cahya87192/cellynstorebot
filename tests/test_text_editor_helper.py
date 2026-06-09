"""Unit test logika render murni editor teks (utils/text_editor_render).

Modul ini murni (tanpa Flask) sehingga bisa diuji langsung. Memastikan token
tersubstitusi benar & tidak ada token sisa.
"""
import json

from utils import text_editor_render as ter


_SECTIONS = [
    {"kind": "set", "label": "Set AFK", "text": "{member} AFK",
     "placeholders": ["{member}"], "sample": {"member": "@Andi"}},
    {"kind": "back", "label": "Kembali", "text": "Halo {member}",
     "placeholders": [], "sample": {}},
]


def _build(rows=3, base="/afk-editor"):
    return ter.editor_content(
        title="Pesan AFK", subtitle="Sub &amp; judul", intro="Intro <b>bold</b>",
        base_route=base, sections=_SECTIONS, rows=rows,
    )


def test_no_leftover_tokens():
    html = _build()
    for tok in ("SECTIONS_JSON", "ROWS_VAL", "BASE_ROUTE", "PAGE_TITLE", "PAGE_SUB", "PAGE_INTRO"):
        assert tok not in html


def test_title_subtitle_intro_embedded():
    html = _build()
    assert "Pesan AFK" in html
    assert "Sub &amp; judul" in html
    assert "Intro <b>bold</b>" in html


def test_rows_applied():
    assert 'rows="3"' in _build(rows=3)
    assert 'rows="2"' in _build(rows=2)
    assert 'rows="3"' not in _build(rows=2)


def test_base_route_in_fetch_urls():
    html = _build(base="/order-editor")
    assert "'/order-editor/save'" in html
    assert "'/order-editor/reset'" in html


def test_sections_json_embedded_and_valid():
    html = _build()
    start = html.index("var SECTIONS = ") + len("var SECTIONS = ")
    end = html.index(";", start)
    parsed = json.loads(html[start:end])
    assert parsed == _SECTIONS


def test_build_sections_flat_resolver():
    specs = {
        "a": {"label": "A", "default": "Halo {store}", "placeholders": ("{store}",)},
        "b": {"label": "B", "default": "tanpa", "placeholders": ()},
    }
    texts = {"a": "Halo {store}", "b": "tanpa"}
    secs = ter.build_sections(specs, lambda k: texts[k],
                              ter.flat_sample_resolver({"store": "Cellyn"}))
    by = {s["kind"]: s for s in secs}
    assert by["a"]["sample"] == {"store": "Cellyn"}
    assert by["b"]["sample"] == {}
    assert by["a"]["text"] == "Halo {store}"
    assert by["a"]["placeholders"] == ["{store}"]


def test_build_sections_per_kind_resolver():
    specs = {"a": {"label": "A", "default": "x", "placeholders": ()}}
    secs = ter.build_sections(specs, lambda k: "x",
                              ter.per_kind_sample_resolver({"a": {"member": "@A"}}))
    assert secs[0]["sample"] == {"member": "@A"}


def test_build_sections_no_resolver():
    specs = {"a": {"label": "A", "default": "x", "placeholders": ()}}
    secs = ter.build_sections(specs, lambda k: "x")
    assert secs[0]["sample"] == {}
