"""admin_lainnya.py - Editor teks katalog & auto-reply Layanan Lainnya (cogs/lainnya.py).

Cog membaca teks lewat utils.lainnya_text. Halaman dibangun lewat komponen bersama
`admin_text_editor`.

  - /lainnya-editor          : form per jenis teks + pratinjau langsung
  - /lainnya-editor/save     : simpan teks (POST JSON {kind,text})
  - /lainnya-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import lainnya_text as latext

lainnya_text_bp = Blueprint("lainnya_text_bp", __name__)

_SAMPLE = {
    "store": "Cellyn Store",
    "groups": "🤖 **AI** — 5 produk\n🎬 **STREAMING** — 8 produk",
    "category": "CANVA",
}

_INTRO = (
    "Teks panel katalog Layanan Lainnya (<code>!catalog_lainnya</code>) &amp; balasan auto-reply. "
    "Daftar grup/produk disisipkan otomatis via placeholder. Perubahan dipakai saat di-refresh berikutnya. "
    "Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia."
)


@lainnya_text_bp.route("/lainnya-editor/save", methods=["POST"])
def save_lainnya_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(latext.LAINNYA_SPECS, latext.save_text)


@lainnya_text_bp.route("/lainnya-editor/reset", methods=["POST"])
def reset_lainnya_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(latext.LAINNYA_SPECS, latext.save_text, latext.load_text)


@lainnya_text_bp.route("/lainnya-editor")
def page_lainnya_text():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        latext.LAINNYA_SPECS, latext.load_text,
        base_route="/lainnya-editor",
        title="Katalog Lainnya",
        subtitle="Layanan Lainnya — teks panel &amp; auto-reply",
        intro=_INTRO,
        rows=3,
        sample_for=ate.flat_sample_resolver(_SAMPLE),
    )
