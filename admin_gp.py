"""admin_gp.py - Editor teks katalog & tiket GP (cogs/gp.py).

Cog membaca teks lewat utils.gp_text. Halaman dibangun lewat komponen bersama
`admin_text_editor`.

  - /gp-editor          : form per jenis teks + pratinjau langsung
  - /gp-editor/save     : simpan teks (POST JSON {kind,text})
  - /gp-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import gp_text as gptext

gp_bp = Blueprint("gp_bp", __name__)

_INTRO = (
    "Teks panel katalog GP (<code>!gpcatalog</code>) &amp; pesan tiket. Rate, stok, &amp; field dinamis "
    "tetap otomatis. Perubahan dipakai saat katalog di-refresh berikutnya. "
    "Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia."
)


@gp_bp.route("/gp-editor/save", methods=["POST"])
def save_gp_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(gptext.GP_SPECS, gptext.save_text)


@gp_bp.route("/gp-editor/reset", methods=["POST"])
def reset_gp_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(gptext.GP_SPECS, gptext.save_text, gptext.load_text)


@gp_bp.route("/gp-editor")
def page_gp():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        gptext.GP_SPECS, gptext.load_text,
        base_route="/gp-editor",
        title="Katalog GP",
        subtitle="Topup Robux via Gamepass — teks panel &amp; tiket",
        intro=_INTRO,
        rows=3,
        sample_for=ate.flat_sample_resolver({"store": "Cellyn Store", "min": "300"}),
    )
