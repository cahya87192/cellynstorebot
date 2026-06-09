"""admin_vilog.py - Editor teks katalog & tiket Vilog (cogs/vilog.py).

Mengubah prosa panel katalog Topup Robux via Login (judul/deskripsi/catatan/footer),
pesan selesai, dan judul pembatalan. Cog membaca teks lewat utils.vilog_text. Halaman
dibangun lewat komponen bersama `admin_text_editor`.

  - /vilog-editor          : form per jenis teks + pratinjau langsung
  - /vilog-editor/save     : simpan teks (POST JSON {kind,text})
  - /vilog-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import vilog_text as vtext

vilog_bp = Blueprint("vilog_bp", __name__)

_INTRO = (
    "Teks panel katalog Vilog (<code>!vilogcatalog</code>) &amp; pesan tiket. Tabel harga, stok, "
    "&amp; field dinamis tetap otomatis. Perubahan dipakai saat katalog di-refresh berikutnya. "
    "Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia."
)


@vilog_bp.route("/vilog-editor/save", methods=["POST"])
def save_vilog_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(vtext.VILOG_SPECS, vtext.save_text)


@vilog_bp.route("/vilog-editor/reset", methods=["POST"])
def reset_vilog_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(vtext.VILOG_SPECS, vtext.save_text, vtext.load_text)


@vilog_bp.route("/vilog-editor")
def page_vilog():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        vtext.VILOG_SPECS, vtext.load_text,
        base_route="/vilog-editor",
        title="Katalog Vilog",
        subtitle="Topup Robux via Login — teks panel &amp; tiket",
        intro=_INTRO,
        rows=3,
        sample_for=ate.flat_sample_resolver({"store": "Cellyn Store", "step": "500", "max": "10000"}),
    )
