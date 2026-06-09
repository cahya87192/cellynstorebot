"""admin_db_backup.py - Backup & Restore database penuh (midman.db).

Halaman admin untuk mengunduh seluruh file database (cadangan menyeluruh) dan
memulihkannya dari file. Memakai utils.db_backup. Tidak menyentuh cog.

  - /db-backup           : halaman download + form restore
  - /db-backup/download  : unduh file midman.db (GET)
  - /db-backup/restore   : pulihkan dari file upload (POST multipart)
"""
import datetime

from flask import Blueprint, request, session, redirect, flash, Response

from utils import db_backup

db_backup_bp = Blueprint("db_backup_bp", __name__)


def _guard():
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@db_backup_bp.route("/db-backup/download")
def download_db_route():
    g = _guard()
    if g:
        return g
    try:
        data = db_backup.read_db_bytes()
    except OSError:
        flash("File database tidak ditemukan.", "error")
        return redirect("/db-backup")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    resp = Response(data, mimetype="application/octet-stream")
    resp.headers["Content-Disposition"] = f"attachment; filename=midman-{stamp}.db"
    return resp


@db_backup_bp.route("/db-backup/restore", methods=["POST"])
def restore_db_route():
    g = _guard()
    if g:
        return g
    f = request.files.get("dbfile")
    if f is None or not f.filename:
        flash("Pilih file backup (.db) dulu.", "error")
        return redirect("/db-backup")
    data = f.read()
    try:
        result = db_backup.restore_from_bytes(data)
    except ValueError as e:
        flash(f"Gagal restore: {e}", "error")
        return redirect("/db-backup")
    flash(
        f"Database berhasil dipulihkan ({db_backup.human_size(result['size'])}). "
        f"DB lama dicadangkan otomatis. Disarankan restart bot.",
        "success",
    )
    return redirect("/db-backup")


@db_backup_bp.route("/db-backup")
def page_db_backup():
    g = _guard()
    if g:
        return g
    from admin import render_page

    size = db_backup.human_size(db_backup.db_size())

    content = """
<div class="page-header">
  <div class="page-title">Backup Database <small>Cadangkan / pulihkan seluruh data (midman.db)</small></div>
</div>
<div class="card"><div class="card-body">
  <div class="note" style="margin-bottom:1rem;">
    Ini backup <b>seluruh database</b> (produk, stok, tiket, transaksi, rating, teks, dst) —
    beda dengan "Backup Teks" yang cuma teks editor. Ukuran DB sekarang: <b>DB_SIZE</b>.
  </div>

  <div style="margin-bottom:1.4rem;">
    <div style="font-weight:700;margin-bottom:.5rem;">1. Unduh backup penuh</div>
    <a href="/db-backup/download" class="btn btn-primary btn-sm">⬇️ Download midman.db</a>
  </div>

  <div style="border-top:1px solid var(--border);padding-top:1.2rem;">
    <div style="font-weight:700;margin-bottom:.5rem;">2. Pulihkan dari file</div>
    <div class="note" style="margin-bottom:.7rem;color:var(--warning);">
      ⚠️ Restore akan <b>menimpa seluruh data sekarang</b> dengan isi file. DB lama otomatis
      dicadangkan (<code>.bak-...</code>). Lakukan saat bot idle, lalu <b>restart bot</b> setelahnya.
    </div>
    <form method="post" action="/db-backup/restore" enctype="multipart/form-data"
          onsubmit="return confirm('Yakin pulihkan database? Semua data sekarang akan ditimpa.');">
      <div class="form-group">
        <input type="file" name="dbfile" accept=".db,application/octet-stream" required />
      </div>
      <button type="submit" class="btn btn-ghost btn-sm">⬆️ Restore database</button>
    </form>
  </div>
</div></div>"""
    content = content.replace("DB_SIZE", size)
    return render_page(content)
