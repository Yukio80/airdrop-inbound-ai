from fastapi import APIRouter
from src.utils.db_manager import DatabaseManager

router = APIRouter()


@router.get("/health")
def health():
    db = DatabaseManager()
    db_connected = True
    signals_count = 0
    last_scan = ""
    try:
        signals_count = db.get_count("signals")
        last_scan = db.get_last_scan_time()
    except Exception:
        db_connected = False

    return {
        "status": "ok" if db_connected else "degraded",
        "db_connected": db_connected,
        "last_scan": last_scan or None,
        "signals_count": signals_count,
        "version": "1.0.0",
    }
