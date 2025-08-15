# utils/health_check.py
from pymongo import MongoClient
from datetime import datetime, timezone
import socket
from pymongo import MongoClient
from utils.remote_health import cowrie, honeypy, honeytrap, conpot, nodepot_lite

def check_mongodb():
    try:
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=1000)
        client.server_info()
        return "✅ Connected", "green"
    except Exception:
        return "❌ Down", "red"

def check_latest_action():
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client["adapttrap"]
        latest = db["agent_actions"].find_one(sort=[("created_at", -1)])
        if latest:
            return f"🕒 {latest.get('created_at')}", "green"
        return "⚠️ No actions yet", "orange"
    except Exception:
        return "❌ Error", "red"

def run_health_checks():
    return {
        "MongoDB":       check_mongodb(),
        "Cowrie SSH":    cowrie(),
        "HoneyPy FTP":   honeypy(),
        "Honeytrap TCP": honeytrap(),
        "Conpot Modbus": conpot(),        # green if Modbus or Bacnet
        "Nodepot-lite":  nodepot_lite(),
        "RL Model":      check_latest_action(),
    }
