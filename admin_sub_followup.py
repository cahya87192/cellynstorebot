"""admin_sub_followup.py - Editor teks DM pengingat perpanjangan (cogs/sub_followup.py).

Cog membaca teks lewat utils.sub_followup_text. Halaman dibangun lewat komponen
bersama `admin_text_editor`.

  - /subfollowup-editor          : form per jenis teks + pratinjau langsung
  - /subfollowup-editor/save     : simpan teks (POST JSON {kind,text})
  - /subfollowup-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import sub_followup_text as sftext

sub_followup_bp = Blueprint("sub_followup_bp", __name__)

_INTRO = (
    "Teks DM personal yang dikirim ke member beberapa hari sebelum langganannya habis "
    "(ajakan perpanjang + tombol order). Perubahan langsung dipakai berikutnya. "
    "Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia."
)


@sub_followup_bp.route("/subfollowup-editor/save", methods=["POST"])
def save_sub_followup_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(sftext.SUB_FOLLOWUP_SPECS, sftext.save_text)


@sub_followup_bp.route("/subfollowup-editor/reset", methods=["POST"])
def reset_sub_followup_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(sftext.SUB_FOLLOWUP_SPECS, sftext.save_text, sftext.load_text)


@sub_followup_bp.route("/subfollowup-editor")
def page_sub_followup():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        sftext.SUB_FOLLOWUP_SPECS, sftext.load_text,
        base_route="/subfollowup-editor",
        title="DM Perpanjangan",
        subtitle="Pengingat langganan hampir habis",
        intro=_INTRO,
        rows=3,
        sample_for=ate.flat_sample_resolver(
            {"store": "Cellyn Store", "item": "Spotify Premium 1 Bulan", "waktu": "dalam 3 hari lagi"}
        ),
    )
