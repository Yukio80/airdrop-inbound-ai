import json, time
from datetime import datetime
from pathlib import Path
import requests
from typing import List, Optional, Dict, Any
from models import QuestTask

GALXE_API = "https://graphigo.prd.galaxy.eco/query"

class GalxeClient:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"Content-Type": "application/json"})

    def _query(self, q):
        r = self.s.post(GALXE_API, json={"query": q}, timeout=15)
        return r.json()

    def active_campaigns(self, first=200):
        q = "{ campaigns(input: {first: %d}) { list { id name status } totalCount } }" % first
        data = self._query(q)
        camps = (data.get("data") or {}).get("campaigns")
        if not camps:
            return []
        return camps.get("list", [])

    def check_eligibility(self, quest_id, address):
        q = '{ campaign(id: "%s") { credentialGroups(address: "%s") { conditions { eligible } } } }' % (quest_id, address.lower())
        return self._query(q)

    def get_completable_tasks(self, wallet_address: str) -> List[QuestTask]:
        """
        Fetch all on-chain and contract interaction tasks the wallet can complete.
        """
        campaigns = self.active_campaigns()
        tasks = []
        
        for c in campaigns:
            if c.get("status") != "Active":
                continue
                
            cid = c["id"]
            # Detailed query for tasks
            q = '{ campaign(id: "%s") { id name tasks { id type title contractAddress calldata } } }' % cid
            res = self._query(q)
            camp = (res.get("data") or {}).get("campaign")
            if not camp: continue
            
            for t in camp.get("tasks", []):
                t_type = t.get("type")
                if t_type in ["ON_CHAIN", "CONTRACT_INTERACTION"]:
                    tasks.append(QuestTask(
                        campaign_id=cid,
                        task_id=t["id"],
                        task_type=t_type,
                        contract_address=t.get("contractAddress", ""),
                        calldata_template=t.get("calldata", "")
                    ))
        return tasks

    def mark_task_attempted(self, task_id: str, tx_hash: str, db_path: str = "airdrop_bot.db"):
        """
        Persist task attempt to SQLite.
        """
        from utils.db_manager import DatabaseManager
        db = DatabaseManager(db_path)
        
        # We need to add a galxe_tasks table to db_manager
        # For now, we use a raw connection to avoid changing db_manager yet
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS galxe_attempts (
                    task_id TEXT PRIMARY KEY,
                    tx_hash TEXT,
                    timestamp TIMESTAMP,
                    status TEXT
                )
            ''')
            conn.execute('''
                INSERT OR REPLACE INTO galxe_attempts (task_id, tx_hash, timestamp, status)
                VALUES (?, ?, ?, ?)
            ''', (task_id, tx_hash, datetime.now().isoformat(), "attempted"))
            conn.commit()

    def scan_eligible(self, address):
        campaigns = self.active_campaigns()
        active = [c for c in campaigns if c.get("status") == "Active"]
        total = len(active)
        open_camps = []
        blocked = 0

        for c in active:
            cid = c["id"]
            try:
                elig = self.check_eligibility(cid, address)
                camp = (elig.get("data") or {}).get("campaign")
                groups = camp.get("credentialGroups", []) if camp else []

                if not groups:
                    open_camps.append({"id": cid, "name": c["name"]})
                else:
                    blocked += 1
            except:
                pass
            time.sleep(0.3)

        return {
            "total": total,
            "open": len(open_camps),
            "blocked": blocked,
            "open_list": open_camps,
            "timestamp": datetime.now().isoformat(),
        }

    def scan_and_persist(self, address, db_path="airdrop_bot.db"):
        from utils.db_manager import DatabaseManager
        db = DatabaseManager(db_path)
        result = self.scan_eligible(address)
        db.save_galxe_scan(result)
        return result

ROOT = Path(__file__).parent.parent.parent
DB_PATH = ROOT / "airdrop_bot.db"

def run_galxe_scan(address, db_path=None):
    db_path = db_path or DB_PATH
    g = GalxeClient()
    return g.scan_and_persist(address, str(db_path))
