"""admin_product_search.py - Editor teks balasan pencarian produk (cogs/product_search.py).

Cog membaca teks lewat utils.product_search_text. Halaman dibangun lewat komponen
bersama `admin_text_editor`.

  - /psearch-editor          : form per jenis teks + pratinjau langsung
  - /psearch-editor/save     : simpan teks (POST JSON {kind,text})
  - /psearch-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import product_search_text as pstext

psearch_bp = Blueprint("psearch_bp", __name__)

_INTRO = (
    "Teks embed balasan saat member mengetik nama produk di channel pencarian. Daftar produk &amp; "
    "harga dibangun otomatis. Perubahan langsung dipakai berikutnya. Mendukung <b>**bold**</b> ala Discord."
)


@psearch_bp.route("/psearch-editor/save", methods=["POST"])
def save_psearch_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(pstext.PRODUCT_SEARCH_SPECS, pstext.save_text)


@psearch_bp.route("/psearch-editor/reset", methods=["POST"])
def reset_psearch_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(pstext.PRODUCT_SEARCH_SPECS, pstext.save_text, pstext.load_text)


@psearch_bp.route("/psearch-editor")
def page_psearch():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        pstext.PRODUCT_SEARCH_SPECS, pstext.load_text,
        base_route="/psearch-editor",
        title="Teks Pencarian",
        subtitle="Balasan auto-search produk lintas-toko",
        intro=_INTRO,
        rows=2,
        sample_for=ate.flat_sample_resolver({"store": "Cellyn Store", "query": "diamond ml"}),
    )
