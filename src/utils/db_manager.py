import sqlite3
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="airdrop_bot.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Table for discovered opportunities
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    protocol TEXT PRIMARY KEY,
                    chain TEXT,
                    tvl REAL,
                    score REAL,
                    status TEXT DEFAULT 'pending',
                    last_updated TIMESTAMP
                )
            ''')
            # Table for executed transactions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallet TEXT,
                    protocol TEXT,
                    action TEXT,
                    tx_hash TEXT,
                    timestamp TIMESTAMP
                )
            ''')
            conn.commit()

    def save_signal(self, signal):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO signals (protocol, chain, tvl, score, status, last_updated)
                VALUES (?, ?, ?, ?, 'pending', ?)
            ''', (signal['protocol'], signal.get('chain'), signal.get('tvl'),
                  signal.get('score'), datetime.now()))
            cursor.execute('''
                UPDATE signals SET chain=?, tvl=?, score=?, last_updated=?
                WHERE protocol=?
            ''', (signal.get('chain'), signal.get('tvl'), signal.get('score'),
                  datetime.now(), signal['protocol']))
            conn.commit()

    def get_pending_signals(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM signals WHERE status = 'pending'")
            return [dict(row) for row in cursor.fetchall()]

    def update_signal_status(self, protocol, status):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE signals SET status = ? WHERE protocol = ?", (status, protocol))
            conn.commit()

    def log_transaction(self, wallet, protocol, action, tx_hash):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions (wallet, protocol, action, tx_hash, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (wallet, protocol, action, tx_hash, datetime.now()))
            conn.commit()
    
    def get_signal_status(self, protocol):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM signals WHERE protocol = ?", (protocol,))
            row = cursor.fetchone()
            return row['status'] if row else None
