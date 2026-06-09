"""admin_top_spender.py - Editor teks papan Top Spender (cogs/top_spender.py).

Cog membaca teks lewat utils.top_spender_text. Halaman dibangun lewat komponen
bersama `admin_text_editor`.

  - /topspender-editor          : form per jenis teks + pratinjau langsung
  - /topspender-editor/save     : simpan teks (POST JSON {kind,text})
  - /topspender-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import top_spender_text as tstext

top_spender_bp = Blueprint("top_spender_bp", __name__)

_INTRO = (
    "Teks papan Top Spender. Daftar peringkat &amp; nominal dihitung otomatis dari transaksi. "
    "Perubahan dipakai saat papan di-refresh berikutnya. Mendukung <b>**bold**</b> ala Discord."
)


@top_spender_bp.route("/topspender-editor/save", methods=["POST"])
def save_top_spender_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(tstext.TOP_SPENDER_SPECS, tstext.save_text)


@top_spender_bp.route("/topspender-editor/reset", methods=["POST"])
def reset_top_spender_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(tstext.TOP_SPENDER_SPECS, tstext.save_text, tstext.load_text)


@top_spender_bp.route("/topspender-editor")
def page_top_spender():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        tstext.TOP_SPENDER_SPECS, tstext.load_text,
        base_route="/topspender-editor",
        title="Papan Top Spender",
        subtitle="Teks leaderboard pelanggan",
        intro=_INTRO,
        rows=3,
        sample_for=ate.flat_sample_resolver({"store": "Cellyn Store", "month": "Juni 2026"}),
    )
