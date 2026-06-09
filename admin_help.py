"""admin_help.py - Editor teks pembungkus embed /help (cogs/help_slash.py).

Cog membaca teks lewat utils.help_text. Halaman dibangun lewat komponen bersama
`admin_text_editor`. Daftar slash command tetap dibangun otomatis dari kode.

  - /help-editor          : form per jenis teks + pratinjau langsung
  - /help-editor/save     : simpan teks (POST JSON {kind,text})
  - /help-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import help_text as hstext

help_bp = Blueprint("help_bp", __name__)

_INTRO = (
    "Judul/deskripsi/footer embed <code>/help</code>. Daftar command dibangun otomatis dari kode, "
    "jadi tidak diedit di sini. Perubahan langsung dipakai berikutnya. "
    "Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia."
)


@help_bp.route("/help-editor/save", methods=["POST"])
def save_help_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(hstext.HELP_SPECS, hstext.save_text)


@help_bp.route("/help-editor/reset", methods=["POST"])
def reset_help_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(hstext.HELP_SPECS, hstext.save_text, hstext.load_text)


@help_bp.route("/help-editor")
def page_help():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        hstext.HELP_SPECS, hstext.load_text,
        base_route="/help-editor",
        title="Teks /help",
        subtitle="Pembungkus embed panduan slash command",
        intro=_INTRO,
        rows=2,
        sample_for=ate.flat_sample_resolver({"store": "Cellyn Store", "seconds": "60"}),
    )
