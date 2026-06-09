"""admin_afk.py - Editor teks pesan sistem AFK (cogs/afk.py).

Mengubah pesan yang dikirim bot saat member set AFK, kembali dari AFK, di-mention
saat AFK, atau jalankan !afk padahal sudah AFK. Cog `cogs/afk.py` membaca teks
lewat utils.afk.render_text(), jadi perubahan di sini langsung dipakai berikutnya.
Halaman dibangun lewat komponen bersama `admin_text_editor`.

  - /afk-editor          : form per jenis pesan + pratinjau langsung
  - /afk-editor/save     : simpan teks (POST JSON {kind,text})
  - /afk-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import afk as afklib

afk_bp = Blueprint("afk_bp", __name__)

# Nilai contoh per jenis pesan untuk pratinjau langsung di panel.
_SAMPLES = {
    "set": {"member": "@Andi", "reason": "lagi makan"},
    "back": {"member": "@Andi"},
    "mention": {"name": "Andi", "reason": "lagi makan", "durasi": "5 menit lalu"},
    "already": {"member": "@Andi"},
}

_INTRO = (
    'Teks ini dikirim bot saat sistem AFK aktif. Perubahan langsung dipakai berikutnya. '
    'Mendukung <b>**bold**</b> ala Discord. Gunakan placeholder yang tersedia di tiap kotak.'
)


@afk_bp.route("/afk-editor/save", methods=["POST"])
def save_afk_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(afklib.AFK_SPECS, afklib.save_text)


@afk_bp.route("/afk-editor/reset", methods=["POST"])
def reset_afk_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(afklib.AFK_SPECS, afklib.save_text, afklib.load_text)


@afk_bp.route("/afk-editor")
def page_afk():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        afklib.AFK_SPECS, afklib.load_text,
        base_route="/afk-editor",
        title="Pesan AFK",
        subtitle="Set, Kembali, Notif Mention &amp; Sudah AFK",
        intro=_INTRO,
        rows=3,
        sample_for=ate.per_kind_sample_resolver(_SAMPLES),
    )
