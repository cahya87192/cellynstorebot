"""Backup & restore semua teks bot yang editable (cadangan / pindah server).

Mengumpulkan SEMUA kunci `bot_state` yang dipakai editor teks panel admin, plus
tabel `lainnya_category_info` (deskripsi & S&K per kategori). Export hanya
menyertakan nilai yang SUDAH dikustomisasi (ada di DB) supaya hasilnya ringkas &
bermakna ("ini override-ku"). Import hanya menulis kunci yang DIKENAL (mencegah
injeksi key sembarangan).

Modul ini self-contained terhadap data (mengimpor modul utils teks yang murni) dan
hanya menyentuh SQLite -> gampang diuji tanpa discord.
"""
import datetime
import json

BACKUP_VERSION = 1


def _simple_specs():
    """Daftar dict SPECS gaya seragam (tiap entry punya 'key')."""
    from utils import afk, warranty_text, queue_text, order_text, review_text
    from utils import midman_text, vilog_text, gp_text, robux_text, ml_text
    from utils import lainnya_text, faq_text, sub_followup_text, top_spender_text
    from utils import help_text, badge_profile_text
    from utils import product_search_text
    return [
        afk.AFK_SPECS,
        warranty_text.WARRANTY_SPECS,
        queue_text.QUEUE_SPECS,
        order_text.ORDER_SPECS,
        review_text.REVIEW_SPECS,
        midman_text.MIDMAN_SPECS,
        vilog_text.VILOG_SPECS,
        gp_text.GP_SPECS,
        robux_text.ROBUX_SPECS,
        ml_text.ML_SPECS,
        lainnya_text.LAINNYA_SPECS,
        faq_text.FAQ_TEXT_SPECS,
        sub_followup_text.SUB_FOLLOWUP_SPECS,
        top_spender_text.TOP_SPENDER_SPECS,
        help_text.HELP_SPECS,
        badge_profile_text.BADGE_PROFILE_SPECS,
        product_search_text.PRODUCT_SEARCH_SPECS,
    ]


def collect_keys():
    """Set semua kunci bot_state yang dikelola editor teks."""
    keys = set()
    for specs in _simple_specs():
        for spec in specs.values():
            keys.add(spec["key"])
    # welcome: embed (title/desc), teks tunggal, dan DM
    from utils import welcome as wl
    for spec in wl.MSG_SPECS.values():
        keys.add(spec["title_key"])
        keys.add(spec["desc_key"])
    for spec in wl.TEXT_SPECS.values():
        keys.add(spec["key"])
    keys.update(wl.DM_KEYS)
    # store_status: label buka/tutup
    from utils import store_status as ss
    keys.add(ss.OPEN_LABEL_KEY)
    keys.add(ss.CLOSE_LABEL_KEY)
    return keys


def export_data():
    """Bangun envelope backup (hanya nilai yang dikustomisasi)."""
    from utils.db import get_conn
    keys = collect_keys()
    state = {}
    cats = []
    conn = get_conn()
    try:
        for r in conn.execute("SELECT key, value FROM bot_state").fetchall():
            if r["key"] in keys:
                state[r["key"]] = r["value"]
    except Exception:
        pass
    try:
        for r in conn.execute(
            "SELECT category, description, terms FROM lainnya_category_info"
        ).fetchall():
            cats.append({
                "category": r["category"],
                "description": r["description"] or "",
                "terms": r["terms"] or "",
            })
    except Exception:
        pass
    conn.close()
    return {
        "version": BACKUP_VERSION,
        "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "bot_state": state,
        "lainnya_category": cats,
    }


def export_json():
    """Envelope backup sebagai string JSON rapi."""
    return json.dumps(export_data(), ensure_ascii=False, indent=2)


def import_data(payload):
    """Terapkan backup. Hanya kunci dikenal yang ditulis.

    Return ringkasan: {applied, skipped, categories}.
    Raise ValueError bila format tidak valid.
    """
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            raise ValueError("JSON tidak valid.")
    if not isinstance(payload, dict):
        raise ValueError("Format backup tidak valid.")

    keys = collect_keys()
    state = payload.get("bot_state") or {}
    cats = payload.get("lainnya_category") or []
    if not isinstance(state, dict):
        raise ValueError("Bagian 'bot_state' harus berupa objek.")

    applied = 0
    skipped = 0
    from utils.db import get_conn
    conn = get_conn()
    c = conn.cursor()
    for k, v in state.items():
        if k not in keys:
            skipped += 1
            continue
        if v is None or str(v).strip() == "":
            c.execute("DELETE FROM bot_state WHERE key=?", (k,))
        else:
            c.execute(
                "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?,?)",
                (k, str(v)),
            )
        applied += 1
    conn.commit()
    conn.close()

    ncat = 0
    if isinstance(cats, list) and cats:
        from utils import lainnya_category as lc
        for it in cats:
            if not isinstance(it, dict):
                continue
            cat = (it.get("category") or "").strip()
            if not cat:
                continue
            desc = it.get("description") or ""
            terms = it.get("terms") or ""
            if not (desc.strip() or terms.strip()):
                continue
            lc.save_info(cat, description=desc, terms=terms)
            ncat += 1

    return {"applied": applied, "skipped": skipped, "categories": ncat}



def reset_all():
    """Hapus SEMUA kustomisasi teks -> kembali ke default bawaan.

    Menghapus semua kunci bot_state yang dikelola editor + seluruh baris tabel
    `lainnya_category_info` (cog kembali memakai default statis CATEGORY_INFO).
    Return ringkasan: {removed, categories_cleared}.
    """
    from utils.db import get_conn
    keys = collect_keys()
    conn = get_conn()
    c = conn.cursor()
    removed = 0
    for k in keys:
        cur = c.execute("DELETE FROM bot_state WHERE key=?", (k,))
        rc = cur.rowcount
        if rc and rc > 0:
            removed += rc
    categories_cleared = 0
    try:
        cur = c.execute("DELETE FROM lainnya_category_info")
        rc = cur.rowcount
        if rc and rc > 0:
            categories_cleared = rc
    except Exception:
        pass
    conn.commit()
    conn.close()
    return {"removed": removed, "categories_cleared": categories_cleared}
