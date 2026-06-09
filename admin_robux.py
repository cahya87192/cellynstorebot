"""admin_robux.py - Editor teks katalog Robux Store (cogs/robux.py).

Cog membaca teks lewat utils.robux_text. Halaman dibangun lewat komponen bersama
`admin_text_editor`.

  - /robux-editor          : form per jenis teks + pratinjau langsung
  - /robux-editor/save     : simpan teks (POST JSON {kind,text})
  - /robux-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import robux_text as rbtext

robux_bp = Blueprint("robux_bp", __name__)

_SAMPLE = {
    "emoji": "🪙",
    "store": "Cellyn Store",
    "rate": "Rp 100/Robux",
    "categories": "🪙 **GAMEPASS**\n🪙 **CRATE**\n🪙 **BOOST**",
}

_INTRO = (
    "Teks panel katalog Robux Store (<code>!catalog</code>). Rate, stok, &amp; daftar kategori "
    "disisipkan otomatis via placeholder. Perubahan dipakai saat katalog di-refresh berikutnya. "
    "Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia."
)


@robux_bp.route("/robux-editor/save", methods=["POST"])
def save_robux_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(rbtext.ROBUX_SPECS, rbtext.save_text)


@robux_bp.route("/robux-editor/reset", methods=["POST"])
def reset_robux_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(rbtext.ROBUX_SPECS, rbtext.save_text, rbtext.load_text)


@robux_bp.route("/robux-editor")
def page_robux():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        rbtext.ROBUX_SPECS, rbtext.load_text,
        base_route="/robux-editor",
        title="Katalog Robux",
        subtitle="Robux Store — teks panel katalog",
        intro=_INTRO,
        rows=3,
        sample_for=ate.flat_sample_resolver(_SAMPLE),
    )
