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
                    timestamp TIMESTAMP,
                    metadata TEXT
                )
            ''')
            # Migration: add metadata column if missing
            try:
                cursor.execute("ALTER TABLE transactions ADD COLUMN metadata TEXT")
            except sqlite3.OperationalError:
                pass # Column already exists
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

    def log_transaction(self, wallet, protocol, action, tx_hash, metadata: str = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions (wallet, protocol, action, tx_hash, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (wallet, protocol, action, tx_hash, datetime.now(), metadata))
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

    def get_all_signals(self) -> list:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM signals")
            return [dict(row) for row in cursor.fetchall()]

    def ensure_alerts_table(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    wallet TEXT,
                    protocol TEXT,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at TIMESTAMP,
                    metadata TEXT
                )
            ''')
            conn.commit()

    def save_alert(self, alert_type: str, message: str, severity: str,
                   wallet: str = None, protocol: str = None,
                   metadata: dict = None) -> int:
        self.ensure_alerts_table()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_alerts (alert_type, wallet, protocol, message, severity, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (alert_type, wallet, protocol, message, severity,
                  json.dumps(metadata) if metadata else None))
            conn.commit()
            return cursor.lastrowid

    def get_unread_alerts(self, limit: int = 20) -> list:
        self.ensure_alerts_table()
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM user_alerts
                WHERE acknowledged_at IS NULL
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_alerts_for_wallet(self, address: str, acknowledged: bool = False, limit: int = 20) -> list:
        self.ensure_alerts_table()
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if acknowledged:
                cursor.execute('''
                    SELECT * FROM user_alerts
                    WHERE wallet = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (address, limit))
            else:
                cursor.execute('''
                    SELECT * FROM user_alerts
                    WHERE wallet = ? AND acknowledged_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (address, limit))
            return [dict(row) for row in cursor.fetchall()]

    def acknowledge_alert(self, alert_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_alerts SET acknowledged_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (alert_id,))
            conn.commit()

    def get_last_tx_for_wallet(self, wallet: str, chain: str = None) -> dict:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if chain:
                cursor.execute('''
                    SELECT * FROM transactions
                    WHERE wallet = ? AND protocol = ? AND tx_hash IS NOT NULL
                    ORDER BY timestamp DESC LIMIT 1
                ''', (wallet, chain))
            else:
                cursor.execute('''
                    SELECT * FROM transactions
                    WHERE wallet = ? AND tx_hash IS NOT NULL
                    ORDER BY timestamp DESC LIMIT 1
                ''', (wallet,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_active_days_for_wallet(self, wallet: str, days: int = 7) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(DISTINCT DATE(timestamp)) as active_days
                FROM transactions
                WHERE wallet = ? AND timestamp >= datetime('now', ? || ' days')
            ''', (wallet, f'-{days}'))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_protocol_interaction_days(self, wallet: str, protocol: str, days: int = 30) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM transactions
                WHERE wallet = ? AND protocol = ? AND timestamp >= datetime('now', ? || ' days')
            ''', (wallet, protocol, f'-{days}'))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_count(self, table: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_last_scan_time(self) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(last_updated) FROM signals")
            row = cursor.fetchone()
            return row[0] if row and row[0] else ""

    def get_unique_protocols_for_wallet(self, wallet: str) -> list:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT protocol FROM transactions
                WHERE wallet = ?
            ''', (wallet,))
            return [row[0] for row in cursor.fetchall()]
