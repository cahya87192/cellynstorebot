"""admin_ml.py - Editor teks katalog & tiket ML/Topup Diamond (cogs/ml.py).

Cog membaca teks lewat utils.ml_text. Halaman dibangun lewat komponen bersama
`admin_text_editor`.

  - /ml-editor          : form per jenis teks + pratinjau langsung
  - /ml-editor/save     : simpan teks (POST JSON {kind,text})
  - /ml-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import ml_text as mltext

ml_bp = Blueprint("ml_bp", __name__)

_SAMPLE = {
    "store": "Cellyn Store",
    "games": "• **Mobile Legends**\n• **Free Fire**\n• **Genshin Impact**",
}

_INTRO = (
    "Teks panel katalog Topup Diamond (<code>!mlcatalog</code>) &amp; pesan tiket. Daftar game "
    "disisipkan otomatis via placeholder. Perubahan dipakai saat katalog di-refresh berikutnya. "
    "Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia."
)


@ml_bp.route("/ml-editor/save", methods=["POST"])
def save_ml_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(mltext.ML_SPECS, mltext.save_text)


@ml_bp.route("/ml-editor/reset", methods=["POST"])
def reset_ml_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(mltext.ML_SPECS, mltext.save_text, mltext.load_text)


@ml_bp.route("/ml-editor")
def page_ml():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        mltext.ML_SPECS, mltext.load_text,
        base_route="/ml-editor",
        title="Katalog ML",
        subtitle="Topup Diamond — teks panel &amp; tiket",
        intro=_INTRO,
        rows=3,
        sample_for=ate.flat_sample_resolver(_SAMPLE),
    )
