import sqlite3
import time
from contextlib import contextmanager


@contextmanager
def db(path="server.db"):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER PRIMARY KEY,
                amount INTEGER DEFAULT 0,
                last_daily INTEGER DEFAULT 0
            );
            """
        )


def get_balance(user_id):
    with db() as c:
        row = c.execute("SELECT * FROM balances WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            c.execute("INSERT INTO balances (user_id) VALUES (?)", (user_id,))
            return {"amount": 0, "last_daily": 0}
        return dict(row)


def add(user_id, amount):
    get_balance(user_id)
    with db() as c:
        c.execute("UPDATE balances SET amount=amount+? WHERE user_id=?", (amount, user_id))


def set_last_daily(user_id, ts):
    get_balance(user_id)
    with db() as c:
        c.execute("UPDATE balances SET last_daily=? WHERE user_id=?", (ts, user_id))


def top(limit=10):
    with db() as c:
        return c.execute(
            "SELECT user_id, amount FROM balances ORDER BY amount DESC LIMIT ?", (limit,)
        ).fetchall()
