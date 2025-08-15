# main_actuator.py
import time
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

from actuator.cowrie_actions import handle_cowrie_action
from actuator.honeypy_actions import handle_honeypy_action
from actuator.honeytrap_actions import handle_honeytrap_action
from actuator.conpot_actions import handle_conpot_action
from actuator.nodepot_actions import handle_nodepot_action
from actuator.utils import log_action

client = MongoClient("mongodb://localhost:27017/")
db = client["adapttrap"]
action_collection = db["agent_actions"]

last_action_id = None

# ✅ Centralized plugin → honeypot → handler mapping
PLUGIN_HANDLER_MAP = {
    # Cowrie
    "telnet":       ("cowrie", handle_cowrie_action),
    "ssh":          ("cowrie", handle_cowrie_action),

    # HoneyPy
    "ftp":          ("honeypy", handle_honeypy_action),

    # Honeytrap
    "tcp":          ("honeytrap", handle_honeytrap_action),
    "udp":          ("honeytrap", handle_honeytrap_action),
    "mysql":        ("honeytrap", handle_honeytrap_action),
    "http":         ("honeytrap", handle_honeytrap_action),

    # Conpot
    "modbus":       ("conpot", handle_conpot_action),
    "enip":         ("conpot", handle_conpot_action),
    "s7comm":       ("conpot", handle_conpot_action),
    "ipmi":         ("conpot", handle_conpot_action),
    "snmp":         ("conpot", handle_conpot_action),
    "bacnet":       ("conpot", handle_conpot_action),
    "http":         ("conpot", handle_conpot_action),
    
    #modepot-lite
    "node-web":     ("nodepot-lite", handle_nodepot_action),

    # Raw triggers
    "honeytrap":    ("honeytrap", handle_honeytrap_action),
    "conpot":       ("conpot", handle_conpot_action)
}

def apply_action(action_doc):
    global last_action_id
    action = action_doc.get("selected_action", {})
    plugin = action.get("plugin")
    act_type = action.get("action")

    if plugin in PLUGIN_HANDLER_MAP:
        hp, handler = PLUGIN_HANDLER_MAP[plugin]
        success, result, cmd = handler(act_type, plugin)
    else:
        print(f"[!] Unsupported plugin: {plugin}")
        return

    db.agent_actions.update_one(
        {"_id": action_doc["_id"]},
        {"$set": {"processed": True, "processed_at": datetime.now(timezone.utc)}}
    )
    log_action(hp, plugin, act_type, cmd, result, success, action_doc["_id"])

def watch_and_apply_actions():
    print("[*] Watching MongoDB for actions...")
    global last_action_id
    while True:
        now = datetime.now(timezone.utc)

        latest = action_collection.find_one(
            {
                "processed": {"$ne": True},
                "created_at": {"$gte": now - timedelta(minutes=2)}
            },
            sort=[("_id", -1)]
        )

        if latest:
            if str(latest['_id']) != str(last_action_id):
                last_action_id = latest['_id']
                apply_action(latest)
        else:
            print("[=] No new action.")

        time.sleep(10)

if __name__ == "__main__":
    watch_and_apply_actions()
