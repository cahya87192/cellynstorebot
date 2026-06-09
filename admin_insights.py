"""admin_insights.py - Analitik & monitor untuk Admin Panel.

Blueprint terpisah (pola sama dgn admin_embed.py) berisi halaman baru:
  - /transactions            : riwayat transaksi (filter + search + pagination)
  - /transactions/export.csv : unduh CSV sesuai filter aktif
  - /tickets                 : monitor tiket aktif semua layanan (live)
  - /admins                  : leaderboard performa admin

Untuk menghindari circular import, render_page/ICONS di-import LAZILY di dalam
tiap view (admin.py meng-import blueprint ini saat startup, sebelum render_page
terdefinisi).
"""
import os
import html
import sqlite3
import csv
import io
import datetime

from flask import Blueprint, request, session, redirect, Response

from utils import member_names

insights_bp = Blueprint("insights_bp", __name__)
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "midman.db")

LAYANAN_LABEL = {
    "midman": "Midman", "robux": "Robux", "ml": "Mobile Legends",
    "ff": "Free Fire", "gp": "Gamepass", "jualbeli": "Jual Beli",
    "vilog": "Vilog", "lainnya": "Lainnya",
}

# (tabel tiket, kolom user, label layanan) untuk monitor tiket aktif.
TICKET_TABLES = [
    ("tickets", "pihak1_id", "midman"),
    ("gp_tickets", "user_id", "gp"),
    ("robux_tickets", "user_id", "robux"),
    ("vilog_tickets", "user_id", "vilog"),
    ("ml_tickets", "user_id", "ml"),
    ("jb_tickets", "p1_id", "jualbeli"),
    ("lainnya_tickets", "user_id", "lainnya"),
]


def _conn():
    c = sqlite3.connect(DB_FILE)
    c.row_factory = sqlite3.Row
    return c



def _rupiah(n):
    try:
        return "Rp " + f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp 0"


def _esc(v):
    return html.escape(str(v if v is not None else ""))


def _who(uid, nm):
    """Render identitas: nama (kalau ada di cache) + id kecil; fallback id mentah."""
    if not uid:
        return "-"
    name = nm.get(str(uid))
    if name:
        return (f"{_esc(name)} <span class='text-muted' style='font-size:.72rem;'>"
                f"#{_esc(uid)}</span>")
    return f"<code>{_esc(uid)}</code>"


def _guard():
    """Return None bila login OK, selain itu Response redirect ke /login."""
    if not session.get("logged_in"):
        return redirect("/login")
    return None


def _layanan_options(selected):
    opts = ['<option value="">Semua layanan</option>']
    for key, label in LAYANAN_LABEL.items():
        sel = " selected" if key == selected else ""
        opts.append(f'<option value="{key}"{sel}>{label}</option>')
    return "".join(opts)


def _build_tx_filters(args):
    """Bangun WHERE + params dari query string (layanan, q, dari, sampai)."""
    where, params = [], []
    layanan = (args.get("layanan") or "").strip()
    q = (args.get("q") or "").strip()
    dari = (args.get("dari") or "").strip()
    sampai = (args.get("sampai") or "").strip()
    if layanan:
        where.append("layanan = ?")
        params.append(layanan)
    if q:
        where.append("(item LIKE ? OR CAST(user_id AS TEXT) LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if dari:
        where.append("date(closed_at) >= date(?)")
        params.append(dari)
    if sampai:
        where.append("date(closed_at) <= date(?)")
        params.append(sampai)
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    return clause, params, {"layanan": layanan, "q": q, "dari": dari, "sampai": sampai}



@insights_bp.route("/transactions")
def page_transactions():
    g = _guard()
    if g:
        return g
    from admin import render_page, ICONS  # lazy import (hindari circular)

    page = max(1, int(request.args.get("page", 1) or 1))
    per_page = 25
    clause, params, f = _build_tx_filters(request.args)

    conn = _conn()
    c = conn.cursor()
    total_rows = c.execute(f"SELECT COUNT(*) FROM transaction_log{clause}", params).fetchone()[0]
    sum_omzet = c.execute(f"SELECT COALESCE(SUM(nominal),0) FROM transaction_log{clause}", params).fetchone()[0]
    rows = c.execute(
        f"SELECT id, closed_at, layanan, item, nominal, qty, user_id, admin_id "
        f"FROM transaction_log{clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [per_page, (page - 1) * per_page],
    ).fetchall()
    conn.close()

    total_pages = max(1, (total_rows + per_page - 1) // per_page)

    nm = member_names.name_map(
        [r["user_id"] for r in rows] + [r["admin_id"] for r in rows]
    )
    body = ""
    for r in rows:
        tgl = (r["closed_at"] or "")[:16].replace("T", " ")
        lay = LAYANAN_LABEL.get(r["layanan"], (r["layanan"] or "-").title())
        buyer = _who(r["user_id"], nm)
        admin = _who(r["admin_id"], nm)
        body += (
            f"<tr><td>{r['id']}</td><td>{_esc(tgl)}</td>"
            f"<td><span class='badge badge-ml'>{_esc(lay)}</span></td>"
            f"<td>{_esc(r['item'] or '-')}</td><td>{r['qty'] or 1}</td>"
            f"<td>{_rupiah(r['nominal'])}</td><td>{buyer}</td><td>{admin}</td></tr>"
        )
    if not body:
        body = "<tr><td colspan='8' class='empty'>Tidak ada transaksi yang cocok.</td></tr>"

    # querystring tanpa 'page' untuk link pagination
    qs = "&".join(
        f"{k}={html.escape(v)}" for k, v in (("layanan", f["layanan"]), ("q", f["q"]),
        ("dari", f["dari"]), ("sampai", f["sampai"])) if v
    )
    qs_amp = ("&" + qs) if qs else ""
    prev_dis = "disabled" if page <= 1 else ""
    next_dis = "disabled" if page >= total_pages else ""
    export_qs = ("?" + qs) if qs else ""

    content = f"""
<div class="page-header">
  <div class="page-title">Transaksi <small>{total_rows} transaksi - omzet {_rupiah(sum_omzet)} (sesuai filter)</small></div>
  <div class="page-actions">
    <a class="btn btn-ghost" href="/transactions/export.csv{export_qs}">{ICONS.get('money','')} Export CSV</a>
  </div>
</div>
<div class="card">
  <div class="card-body">
    <form method="get" action="/transactions" class="form-grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr));align-items:end;">
      <div class="form-group"><label>Cari (item / user id)</label><input type="text" name="q" value="{_esc(f['q'])}" placeholder="mis. Spotify"></div>
      <div class="form-group"><label>Layanan</label><select name="layanan">{_layanan_options(f['layanan'])}</select></div>
      <div class="form-group"><label>Dari</label><input type="date" name="dari" value="{_esc(f['dari'])}"></div>
      <div class="form-group"><label>Sampai</label><input type="date" name="sampai" value="{_esc(f['sampai'])}"></div>
      <div class="form-group"><button type="submit" class="btn btn-primary">Filter</button></div>
    </form>
  </div>
</div>
<div class="card">
  <div class="table-wrapper">
    <table>
      <thead><tr><th>ID</th><th>Waktu (UTC)</th><th>Layanan</th><th>Item</th><th>Qty</th><th>Nominal</th><th>Buyer</th><th>Admin</th></tr></thead>
      <tbody>{body}</tbody>
    </table>
  </div>
  <div class="card-body" style="display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;">
    <span class="text-muted">Halaman {page} / {total_pages}</span>
    <div style="display:flex;gap:.5rem;">
      <a class="btn btn-ghost btn-sm {prev_dis}" href="/transactions?page={page-1}{qs_amp}">Sebelumnya</a>
      <a class="btn btn-ghost btn-sm {next_dis}" href="/transactions?page={page+1}{qs_amp}">Berikutnya</a>
    </div>
  </div>
</div>"""
    return render_page(content)


@insights_bp.route("/transactions/export.csv")
def export_transactions():
    g = _guard()
    if g:
        return g
    clause, params, _ = _build_tx_filters(request.args)
    conn = _conn()
    rows = conn.execute(
        f"SELECT id, closed_at, layanan, item, qty, nominal, user_id, admin_id "
        f"FROM transaction_log{clause} ORDER BY id DESC",
        params,
    ).fetchall()
    conn.close()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "closed_at", "layanan", "item", "qty", "nominal", "user_id", "admin_id"])
    for r in rows:
        w.writerow([r["id"], r["closed_at"], r["layanan"], r["item"],
                    r["qty"] or 1, r["nominal"] or 0, r["user_id"], r["admin_id"]])
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=transaksi_{stamp}.csv"},
    )



@insights_bp.route("/admins")
def page_admins():
    g = _guard()
    if g:
        return g
    from admin import render_page  # lazy import (hindari circular)

    conn = _conn()
    rows = conn.execute(
        """
        SELECT admin_id,
               COUNT(*) AS total,
               COALESCE(SUM(nominal),0) AS omzet,
               COALESCE(AVG(NULLIF(durasi_detik,0)),0) AS avg_durasi
        FROM transaction_log
        WHERE admin_id IS NOT NULL
        GROUP BY admin_id
        ORDER BY total DESC
        """
    ).fetchall()
    conn.close()

    def _dur(secs):
        secs = int(secs or 0)
        if secs <= 0:
            return "-"
        if secs >= 3600:
            return f"{secs // 3600}j {secs % 3600 // 60}m"
        if secs >= 60:
            return f"{secs // 60}m"
        return f"{secs}s"

    nm = member_names.name_map([r["admin_id"] for r in rows])
    body = ""
    for i, r in enumerate(rows, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"#{i}")
        body += (
            f"<tr><td>{medal}</td><td>{_who(r['admin_id'], nm)}</td>"
            f"<td>{r['total']}</td><td>{_rupiah(r['omzet'])}</td>"
            f"<td>{_dur(r['avg_durasi'])}</td></tr>"
        )
    if not body:
        body = "<tr><td colspan='5' class='empty'>Belum ada data transaksi dengan admin.</td></tr>"

    content = f"""
<div class="page-header">
  <div class="page-title">Performa Admin <small>Ranking staff berdasarkan transaksi selesai</small></div>
</div>
<div class="card">
  <div class="table-wrapper">
    <table>
      <thead><tr><th>#</th><th>Admin</th><th>Transaksi</th><th>Omzet</th><th>Rata-rata Durasi</th></tr></thead>
      <tbody>{body}</tbody>
    </table>
  </div>
</div>
<div class="note">Durasi dihitung dari lama tiket dibuka sampai ditutup (kolom durasi_detik pada transaction_log).</div>"""
    return render_page(content)


@insights_bp.route("/tickets")
def page_tickets():
    g = _guard()
    if g:
        return g
    from admin import render_page

    now = datetime.datetime.now(datetime.timezone.utc)
    # handling map (siapa yang sedang !pay) dari bot_state
    handling = {}
    conn = _conn()
    try:
        raw = conn.execute("SELECT value FROM bot_state WHERE key='queue_handling_map'").fetchone()
        if raw and raw[0]:
            import json
            data = json.loads(raw[0])
            if isinstance(data, dict):
                handling = {str(k): v for k, v in data.items()}
    except Exception:
        handling = {}

    items = []
    for table, ucol, layanan in TICKET_TABLES:
        try:
            rows = conn.execute(
                f"SELECT channel_id, {ucol} AS uid, opened_at FROM {table}"
            ).fetchall()
        except Exception:
            continue
        for r in rows:
            items.append({
                "channel_id": r["channel_id"],
                "uid": r["uid"],
                "opened_at": r["opened_at"],
                "layanan": layanan,
            })
    conn.close()

    def _age(opened):
        if not opened:
            return "-"
        try:
            dt = datetime.datetime.fromisoformat(str(opened))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
        except Exception:
            return "-"
        secs = int((now - dt).total_seconds())
        if secs < 0:
            secs = 0
        if secs >= 3600:
            return f"{secs // 3600}j {secs % 3600 // 60}m"
        if secs >= 60:
            return f"{secs // 60}m"
        return f"{secs}s"

    def _sortkey(it):
        try:
            return str(it["opened_at"] or "")
        except Exception:
            return ""
    items.sort(key=_sortkey)

    diproses = sum(1 for it in items if str(it["channel_id"]) in handling)
    menunggu = len(items) - diproses

    nm = member_names.name_map(
        [it["uid"] for it in items] + list(handling.values())
    )
    body = ""
    for it in items:
        cid = str(it["channel_id"])
        is_proc = cid in handling
        status = ("<span class='badge badge-aktif'>Diproses</span>"
                  if is_proc else "<span class='badge badge-boost'>Menunggu</span>")
        admin = _who(handling[cid], nm) if is_proc and handling.get(cid) else "-"
        lay = LAYANAN_LABEL.get(it["layanan"], it["layanan"].title())
        buyer = _who(it["uid"], nm)
        body += (
            f"<tr><td><span class='badge badge-ml'>{_esc(lay)}</span></td>"
            f"<td>{buyer}</td><td>{_age(it['opened_at'])}</td>"
            f"<td>{status}</td><td>{admin}</td>"
            f"<td><code>{cid}</code></td></tr>"
        )
    if not body:
        body = "<tr><td colspan='6' class='empty'>Tidak ada tiket aktif saat ini.</td></tr>"

    content = f"""
<div class="page-header">
  <div class="page-title">Tiket Aktif <small>Pantauan langsung - halaman auto-refresh 30 detik</small></div>
</div>
<div class="stats-grid">
  <div class="stat-card gold"><div class="stat-label">Total Aktif</div><div class="stat-value">{len(items)}</div><div class="stat-sub">semua layanan</div></div>
  <div class="stat-card green"><div class="stat-label">Sedang Diproses</div><div class="stat-value">{diproses}</div><div class="stat-sub">admin sudah !pay</div></div>
  <div class="stat-card robux"><div class="stat-label">Menunggu</div><div class="stat-value">{menunggu}</div><div class="stat-sub">belum ditangani</div></div>
</div>
<div class="card">
  <div class="table-wrapper">
    <table>
      <thead><tr><th>Layanan</th><th>Buyer</th><th>Umur</th><th>Status</th><th>Admin</th><th>Channel ID</th></tr></thead>
      <tbody>{body}</tbody>
    </table>
  </div>
</div>
<script>setTimeout(function(){{location.reload();}}, 30000);</script>"""
    return render_page(content)
