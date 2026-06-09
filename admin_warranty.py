"""admin_warranty.py - Editor teks sistem klaim garansi (cogs/warranty.py).

Mengubah teks panel garansi, pesan penolakan klaim, dan deskripsi embed tiket. Cog
`cogs/warranty.py` membaca teks lewat utils.warranty_text. Halaman dibangun lewat
komponen bersama `admin_text_editor`.

  - /warranty-editor          : form per jenis teks + pratinjau langsung
  - /warranty-editor/save     : simpan teks (POST JSON {kind,text})
  - /warranty-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import warranty_text as wtext

warranty_bp = Blueprint("warranty_bp", __name__)

_INTRO = (
    "Teks ini dipakai sistem klaim garansi. Perubahan langsung dipakai berikutnya "
    "(panel garansi di-update saat admin menjalankan <code>!garansi</code> lagi). "
    "Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia."
)


@warranty_bp.route("/warranty-editor/save", methods=["POST"])
def save_warranty_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(wtext.WARRANTY_SPECS, wtext.save_text)


@warranty_bp.route("/warranty-editor/reset", methods=["POST"])
def reset_warranty_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(wtext.WARRANTY_SPECS, wtext.save_text, wtext.load_text)


@warranty_bp.route("/warranty-editor")
def page_warranty():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        wtext.WARRANTY_SPECS, wtext.load_text,
        base_route="/warranty-editor",
        title="Pesan Garansi",
        subtitle="Panel, penolakan klaim &amp; embed tiket",
        intro=_INTRO,
        rows=3,
        sample_for=ate.flat_sample_resolver({"store": "Cellyn Store"}),
    )
