"""SQLite persistence for invoice-chaser."""
import sqlite3
from pathlib import Path
from datetime import datetime, date

DB = Path(__file__).parent / "chaser.db"


def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            plan        TEXT NOT NULL DEFAULT 'free',
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            client_name     TEXT NOT NULL,
            client_email    TEXT NOT NULL,
            amount          REAL NOT NULL,
            currency        TEXT NOT NULL DEFAULT 'GBP',
            description     TEXT NOT NULL DEFAULT '',
            due_date        TEXT NOT NULL,
            invoice_ref     TEXT NOT NULL DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'unpaid',
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chases (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id  INTEGER NOT NULL REFERENCES invoices(id),
            day         INTEGER NOT NULL,
            sent_at     TEXT,
            status      TEXT NOT NULL DEFAULT 'pending'
        );
        """)


def get_or_create_user(email: str, name: str) -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if row:
            return dict(row)
        c.execute("INSERT INTO users (email, name) VALUES (?,?)", (email, name))
        row = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return dict(row)


def add_invoice(user_id: int, client_name: str, client_email: str,
                amount: float, due_date: str, description: str = "",
                invoice_ref: str = "", currency: str = "GBP") -> int:
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO invoices
               (user_id, client_name, client_email, amount, currency,
                description, due_date, invoice_ref)
               VALUES (?,?,?,?,?,?,?,?)""",
            (user_id, client_name, client_email, amount, currency,
             description, due_date, invoice_ref)
        )
        inv_id = cur.lastrowid
        # Schedule chases at day 1, 3, 7 after due date
        for day in [1, 3, 7]:
            c.execute(
                "INSERT INTO chases (invoice_id, day) VALUES (?,?)",
                (inv_id, day)
            )
        return inv_id


def get_invoices(user_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM invoices WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def mark_paid(invoice_id: int):
    with _conn() as c:
        c.execute("UPDATE invoices SET status='paid' WHERE id=?", (invoice_id,))
        c.execute("UPDATE chases SET status='cancelled' WHERE invoice_id=? AND status='pending'",
                  (invoice_id,))


def get_pending_chases() -> list[dict]:
    """Return chases where due date + day offset <= today and status=pending."""
    today = date.today().isoformat()
    with _conn() as c:
        rows = c.execute("""
            SELECT ch.id, ch.day, ch.invoice_id,
                   i.client_name, i.client_email, i.amount, i.currency,
                   i.description, i.due_date, i.invoice_ref, i.status as inv_status,
                   u.name as user_name, u.email as user_email
            FROM chases ch
            JOIN invoices i ON i.id = ch.invoice_id
            JOIN users u ON u.id = i.user_id
            WHERE ch.status = 'pending'
              AND i.status = 'unpaid'
              AND date(i.due_date, '+' || ch.day || ' days') <= ?
        """, (today,)).fetchall()
        return [dict(r) for r in rows]


def mark_chase_sent(chase_id: int):
    with _conn() as c:
        c.execute(
            "UPDATE chases SET status='sent', sent_at=datetime('now') WHERE id=?",
            (chase_id,)
        )


def stats(user_id: int) -> dict:
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM invoices WHERE user_id=?", (user_id,)).fetchone()[0]
        unpaid = c.execute("SELECT COUNT(*) FROM invoices WHERE user_id=? AND status='unpaid'", (user_id,)).fetchone()[0]
        value = c.execute("SELECT COALESCE(SUM(amount),0) FROM invoices WHERE user_id=? AND status='unpaid'", (user_id,)).fetchone()[0]
        return {"total": total, "unpaid": unpaid, "unpaid_value": value}
