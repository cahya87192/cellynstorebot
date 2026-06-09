"""admin_faq_text.py - Editor teks pembungkus FAQ / Auto-CS / Saran (cogs/faq.py).

Cog membaca teks lewat utils.faq_text. Halaman dibangun lewat komponen bersama
`admin_text_editor`. Knowledge base (Q&A) tetap di halaman "Editor FAQ" yang lama.

  - /faq-text-editor          : form per jenis teks + pratinjau langsung
  - /faq-text-editor/save     : simpan teks (POST JSON {kind,text})
  - /faq-text-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import faq_text as fqtext

faq_text_bp = Blueprint("faq_text_bp", __name__)

_INTRO = (
    "Ini teks <b>pembungkus</b> FAQ (judul/deskripsi/footer), footer Auto-CS, &amp; pesan <code>/saran</code>. "
    "Daftar pertanyaan/jawaban diedit di halaman <b>Editor FAQ</b>. Setelah ubah teks embed FAQ, "
    "jalankan <code>!faqrefresh</code> di Discord. Mendukung <b>**bold**</b> ala Discord."
)


@faq_text_bp.route("/faq-text-editor/save", methods=["POST"])
def save_faq_text_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(fqtext.FAQ_TEXT_SPECS, fqtext.save_text)


@faq_text_bp.route("/faq-text-editor/reset", methods=["POST"])
def reset_faq_text_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(fqtext.FAQ_TEXT_SPECS, fqtext.save_text, fqtext.load_text)


@faq_text_bp.route("/faq-text-editor")
def page_faq_text():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        fqtext.FAQ_TEXT_SPECS, fqtext.load_text,
        base_route="/faq-text-editor",
        title="Teks FAQ",
        subtitle="Embed FAQ, Auto-CS &amp; pesan /saran",
        intro=_INTRO,
        rows=2,
        sample_for=ate.flat_sample_resolver({"store": "Cellyn Store", "question": "Berapa lama proses topup?"}),
    )
