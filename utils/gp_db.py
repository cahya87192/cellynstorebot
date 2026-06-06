from utils.db import get_conn

def load_gp_tickets():
    conn = get_conn()
    c = conn.cursor()
    # Defensif: pastikan kolom ticket_number ada sebelum baca (gp_tickets dibuat
    # di cogs/gp.py, bukan di db.init_db) supaya nomor tiket bertahan pasca-restart.
    try:
        c.execute("ALTER TABLE gp_tickets ADD COLUMN ticket_number INTEGER")
        conn.commit()
    except Exception:
        pass
    try:
        c.execute("SELECT * FROM gp_tickets")
        rows = c.fetchall()
    except Exception:
        rows = []
    conn.close()
    tickets = {}
    for row in rows:
        keys = row.keys()
        tickets[row["channel_id"]] = {
            "channel_id":    row["channel_id"],
            "user_id":       row["user_id"],
            "robux":         row["robux"],
            "gp_price":      row["gp_price"],
            "rate":          row["rate"],
            "total":         row["total"],
            "paid":          bool(row["paid"]),
            "gp_link":       row["gp_link"],
            "admin_id":      row["admin_id"],
            "opened_at":     row["opened_at"],
            "warned":        bool(row["warned"]) if row["warned"] is not None else False,
            "warn_message_id": row["warn_message_id"],
            "last_activity": row["last_activity"],
            "ticket_number": row["ticket_number"] if "ticket_number" in keys and row["ticket_number"] is not None else 0,
        }
    return tickets

def save_gp_ticket(ticket):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE gp_tickets ADD COLUMN ticket_number INTEGER")
        conn.commit()
    except Exception:
        pass
    c.execute("""
        INSERT OR REPLACE INTO gp_tickets
        (channel_id, user_id, robux, gp_price, rate, total,
         paid, gp_link, admin_id, opened_at, warned, warn_message_id, last_activity, ticket_number)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        ticket["channel_id"],
        ticket["user_id"],
        ticket["robux"],
        ticket["gp_price"],
        ticket["rate"],
        ticket["total"],
        1 if ticket.get("paid") else 0,
        ticket.get("gp_link"),
        ticket.get("admin_id"),
        ticket["opened_at"],
        1 if ticket.get("warned") else 0,
        ticket.get("warn_message_id"),
        ticket.get("last_activity"),
        ticket.get("ticket_number") or 0,
    ))
    conn.commit()
    conn.close()

def delete_gp_ticket(channel_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM gp_tickets WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()

def get_gp_rate():
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("SELECT value FROM bot_state WHERE key = 'gp_rate'")
        row = c.fetchone()
        return int(row["value"]) if row else 0
    except Exception:
        return 0
    finally:
        conn.close()

def set_gp_rate(rate: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES ('gp_rate', ?)", (str(rate),))
    conn.commit()
    conn.close()
