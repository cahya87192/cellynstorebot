"""admin_orders.py - Editor teks pesan tiket order (cogs/orders.py).

Mengubah pesan saat admin menjalankan !done (selesai) / !cancel (batal) pada tiket
order layanan "lainnya". Cog `cogs/orders.py` membaca teks lewat utils.order_text,
jadi perubahan langsung dipakai berikutnya. Halaman dibangun lewat komponen bersama
`admin_text_editor`.

  - /order-editor          : form per jenis teks + pratinjau langsung
  - /order-editor/save     : simpan teks (POST JSON {kind,text})
  - /order-editor/reset    : kembalikan satu jenis ke default (POST JSON {kind})
"""
from flask import Blueprint

import admin_text_editor as ate
from utils import order_text as otext

order_bp = Blueprint("order_bp", __name__)

_INTRO = (
    'Teks ini dikirim bot saat admin menyelesaikan / membatalkan tiket order layanan "lainnya". '
    'Perubahan langsung dipakai berikutnya. Mendukung <b>**bold**</b> ala Discord.'
)


@order_bp.route("/order-editor/save", methods=["POST"])
def save_order_route():
    g = ate.guard()
    if g:
        return g
    return ate.save_request(otext.ORDER_SPECS, otext.save_text)


@order_bp.route("/order-editor/reset", methods=["POST"])
def reset_order_route():
    g = ate.guard()
    if g:
        return g
    return ate.reset_request(otext.ORDER_SPECS, otext.save_text, otext.load_text)


@order_bp.route("/order-editor")
def page_order():
    g = ate.guard()
    if g:
        return g
    return ate.render(
        otext.ORDER_SPECS, otext.load_text,
        base_route="/order-editor",
        title="Pesan Order",
        subtitle="Notifikasi selesai (!done) &amp; batal (!cancel)",
        intro=_INTRO,
        rows=2,
        sample_for=ate.flat_sample_resolver({"store": "Cellyn Store"}),
    )
