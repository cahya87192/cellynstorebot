"""admin_queue.py - Editor teks antrian yang dilihat customer (cogs/queue.py).

Mengubah teks papan antrian PUBLIK & kartu posisi (bukan papan admin internal). Cog
`cogs/queue.py` membaca teks lewat utils.queue_text. Halaman dibangun lewat komponen
bersama `admin_text_editor`.

  - /queue-editor          : form per jenis teks + pratinjau langsung
  - /queue-editor/save     : simpan teks (POST JSON {kind,text})
  - /queue-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import queue_text as qtext

queue_text_bp = Blueprint("queue_text_bp", __name__)

# Nilai contoh per jenis teks untuk pratinjau langsung.
_SAMPLES = {
    "card_handling": {"admin": "@AdminCellyn"},
    "card_waiting": {"position": "3", "ahead": "2"},
}

_INTRO = (
    "Teks ini dilihat member di papan antrian publik &amp; kartu posisi tiket. "
    "Perubahan dipakai pada pembaruan berikutnya (otomatis tiap ~30 detik). "
    "Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia."
)


@queue_text_bp.route("/queue-editor/save", methods=["POST"])
def save_queue_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(qtext.QUEUE_SPECS, qtext.save_text)


@queue_text_bp.route("/queue-editor/reset", methods=["POST"])
def reset_queue_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(qtext.QUEUE_SPECS, qtext.save_text, qtext.load_text)


@queue_text_bp.route("/queue-editor")
def page_queue():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        qtext.QUEUE_SPECS, qtext.load_text,
        base_route="/queue-editor",
        title="Teks Antrian",
        subtitle="Papan publik &amp; kartu posisi customer",
        intro=_INTRO,
        rows=3,
        sample_for=ate.per_kind_sample_resolver(_SAMPLES),
    )
