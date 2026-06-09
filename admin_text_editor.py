"""admin_text_editor.py - Glue Flask untuk halaman editor teks panel admin.

Logika render murni ada di `utils/text_editor_render.py` (gampang diuji tanpa
Flask). Modul ini menambah bagian yang butuh Flask: guard login, handler rute
save/reset, dan render halaman penuh via admin.render_page.

Dipakai modul `admin_<x>.py`:
  - guard()                                     -> redirect /login bila belum login
  - save_request(specs, save_text)              -> handler rute /save
  - reset_request(specs, save_text, load_text)  -> handler rute /reset
  - render(specs, load_text, ...)               -> halaman editor lengkap
  - flat_sample_resolver / per_kind_sample_resolver (re-export)
"""
from flask import request, session, redirect, jsonify

from utils.text_editor_render import (
    editor_content,
    build_sections,
    flat_sample_resolver,
    per_kind_sample_resolver,
)
from utils import text_audit

__all__ = [
    "guard", "save_request", "reset_request", "render",
    "editor_content", "build_sections",
    "flat_sample_resolver", "per_kind_sample_resolver",
]


def guard():
    """Kembalikan redirect ke /login bila belum login, selain itu None."""
    if not session.get("logged_in"):
        return redirect("/login")
    return None


def save_request(specs, save_text):
    """Handler rute /save: validasi {kind,text} lalu simpan."""
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in specs:
        return jsonify({"ok": False, "error": "Jenis teks tidak dikenal."}), 400
    text = payload.get("text")
    if text is None or not str(text).strip():
        return jsonify({"ok": False, "error": "Teks tidak boleh kosong."}), 400
    save_text(kind, text=text)
    spec = specs[kind]
    text_audit.record("save", key=spec.get("key"), kind=kind,
                      label=spec.get("label"), detail=text)
    return jsonify({"ok": True})


def reset_request(specs, save_text, load_text):
    """Handler rute /reset: kosongkan (-> default) lalu kembalikan teks default."""
    payload = request.get_json(force=True, silent=True) or {}
    kind = payload.get("kind")
    if kind not in specs:
        return jsonify({"ok": False, "error": "Jenis teks tidak dikenal."}), 400
    save_text(kind, text="")
    spec = specs[kind]
    text_audit.record("reset", key=spec.get("key"), kind=kind,
                      label=spec.get("label"), detail="(ke default)")
    return jsonify({"ok": True, "text": load_text(kind)})


def render(specs, load_text, *, base_route, title, subtitle, intro, rows=3, sample_for=None):
    """Render halaman editor lengkap (pakai admin.render_page)."""
    from admin import render_page
    sections = build_sections(specs, load_text, sample_for)
    return render_page(editor_content(
        title=title, subtitle=subtitle, intro=intro,
        base_route=base_route, sections=sections, rows=rows,
    ))
