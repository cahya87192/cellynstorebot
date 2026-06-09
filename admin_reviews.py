"""admin_reviews.py - Editor teks sistem rating & ulasan (cogs/reviews.py).

Mengubah prosa pesan rating: prompt, struk, kedaluwarsa, pengingat, judul ulasan,
ucapan terima kasih. Struktur embed tetap dikelola cog. Cog membaca teks lewat
utils.review_text. Halaman dibangun lewat komponen bersama `admin_text_editor`.

  - /review-editor          : form per jenis teks + pratinjau langsung
  - /review-editor/save     : simpan teks (POST JSON {kind,text})
  - /review-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import review_text as rtext

review_bp = Blueprint("review_bp", __name__)

_SAMPLE = {
    "store": "Cellyn Store",
    "hours": "24",
    "rating": "5",
    "stars": "⭐⭐⭐⭐⭐",
}

_INTRO = (
    "Teks ini dikirim sistem rating ke member (DM/channel testimoni). Hanya prosa yang bisa diedit; "
    "struktur embed (field Item/Nominal, tombol bintang, timestamp deadline) tetap otomatis. "
    "Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia."
)


@review_bp.route("/review-editor/save", methods=["POST"])
def save_review_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(rtext.REVIEW_SPECS, rtext.save_text)


@review_bp.route("/review-editor/reset", methods=["POST"])
def reset_review_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(rtext.REVIEW_SPECS, rtext.save_text, rtext.load_text)


@review_bp.route("/review-editor")
def page_review():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        rtext.REVIEW_SPECS, rtext.load_text,
        base_route="/review-editor",
        title="Pesan Rating &amp; Ulasan",
        subtitle="Prompt, struk, pengingat, kedaluwarsa &amp; ucapan terima kasih",
        intro=_INTRO,
        rows=3,
        sample_for=ate.flat_sample_resolver(_SAMPLE),
    )
