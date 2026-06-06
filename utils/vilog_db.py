from utils.db import get_conn

def load_vilog_tickets():
    conn = get_conn()
    c = conn.cursor()
    # Defensif: pastikan kolom ticket_number ada (loader dipanggil di __init__ cog
    # sebelum save_*), supaya nomor tiket bertahan setelah restart.
    try:
        c.execute('ALTER TABLE vilog_tickets ADD COLUMN ticket_number INTEGER')
        conn.commit()
    except Exception:
        pass
    c.execute('SELECT * FROM vilog_tickets')
    rows = c.fetchall()
    conn.close()
    tickets = {}
    for row in rows:
        keys = row.keys()
        tickets[row['channel_id']] = {
            'channel_id': row['channel_id'],
            'user_id': row['user_id'],
            # Backward compat: older rows might store email in username_roblox
            'email': row['email'] or row['username_roblox'],
            'password': row['password'],
            'backup_codes': row['backup_codes'] or '',
            'premium': bool(row['premium']) if row['premium'] is not None else False,
            'boost': {'nama': row['boost_nama'], 'robux': row['boost_robux']},
            'metode': row['metode'],
            'nominal': row['nominal'],
            'admin_id': row['admin_id'],
            'opened_at': row['opened_at'],
            'warned': bool(row['warned']) if row['warned'] is not None else False,
            'ticket_number': row['ticket_number'] if 'ticket_number' in keys and row['ticket_number'] is not None else 0,
        }
    return tickets

def save_vilog_ticket(ticket):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE vilog_tickets ADD COLUMN ticket_number INTEGER')
        conn.commit()
    except Exception:
        pass
    c.execute('''
        INSERT OR REPLACE INTO vilog_tickets
        (channel_id, user_id, username_roblox, password, email, backup_codes, premium, boost_nama, boost_robux, metode, nominal, admin_id, opened_at, warned, ticket_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        ticket['channel_id'],
        ticket['user_id'],
        ticket.get('username_roblox'),
        ticket.get('password'),
        ticket.get('email'),
        ticket.get('backup_codes'),
        1 if ticket.get('premium') else 0,
        ticket['boost']['nama'],
        ticket['boost']['robux'],
        ticket['metode'],
        ticket.get('nominal'),
        ticket.get('admin_id'),
        ticket['opened_at'],
        1 if ticket.get('warned') else 0,
        ticket.get('ticket_number') or 0,
    ))
    conn.commit()
    conn.close()

def delete_vilog_ticket(channel_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM vilog_tickets WHERE channel_id = ?', (channel_id,))
    conn.commit()
    conn.close()
