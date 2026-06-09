"""admin_midman.py - Editor teks panel Midman Trade (cogs/midman.py).

Mengubah judul & deskripsi panel katalog Midman (!open) serta pesan konfirmasi trade
selesai (!acc). Cog membaca teks lewat utils.midman_text. Halaman dibangun lewat
komponen bersama `admin_text_editor`.

  - /midman-editor          : form per jenis teks + pratinjau langsung
  - /midman-editor/save     : simpan teks (POST JSON {kind,text})
  - /midman-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import midman_text as mtext

midman_bp = Blueprint("midman_bp", __name__)

_INTRO = (
    "Teks panel Midman Trade (perintah <code>!open</code>) &amp; konfirmasi <code>!acc</code>. "
    "Perubahan dipakai saat panel dikirim ulang. Tabel fee &amp; tombol tetap otomatis. "
    "Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia."
)


@midman_bp.route("/midman-editor/save", methods=["POST"])
def save_midman_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(mtext.MIDMAN_SPECS, mtext.save_text)


@midman_bp.route("/midman-editor/reset", methods=["POST"])
def reset_midman_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(mtext.MIDMAN_SPECS, mtext.save_text, mtext.load_text)


@midman_bp.route("/midman-editor")
def page_midman():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        mtext.MIDMAN_SPECS, mtext.load_text,
        base_route="/midman-editor",
        title="Panel Midman",
        subtitle="Judul &amp; deskripsi katalog + konfirmasi trade",
        intro=_INTRO,
        rows=3,
        sample_for=ate.flat_sample_resolver({"store": "Cellyn Store"}),
    )
