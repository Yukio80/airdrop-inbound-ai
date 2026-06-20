import json, sqlite3
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
                UPDATE signals SET chain=?, tvl=?, score=?, status='pending', last_updated=?
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

    def save_galxe_scan(self, result):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS galxe_scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total INTEGER,
                    open_count INTEGER,
                    blocked INTEGER,
                    open_list TEXT,
                    timestamp TIMESTAMP
                )
            ''')
            cursor.execute('''
                INSERT INTO galxe_scans (total, open_count, blocked, open_list, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (result["total"], result["open"], result["blocked"],
                  json.dumps(result["open_list"]), result["timestamp"]))
            conn.commit()

    def get_last_galxe_scan(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS galxe_scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total INTEGER,
                    open_count INTEGER,
                    blocked INTEGER,
                    open_list TEXT,
                    timestamp TIMESTAMP
                )
            ''')
            cursor.execute("SELECT * FROM galxe_scans ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d["open_list"] = json.loads(d["open_list"])
                return d
            return None
    
    def get_signal_status(self, protocol):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM signals WHERE protocol = ?", (protocol,))
            row = cursor.fetchone()
            return row['status'] if row else None
