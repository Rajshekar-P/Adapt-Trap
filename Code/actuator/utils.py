import os
import json
import subprocess
from datetime import datetime, timezone
from pymongo import MongoClient

# Load honeypot credentials from JSON
CONFIG_PATH = os.path.expanduser("~/adapttrap/Code/configs/honeypot_creds.json")
with open(CONFIG_PATH, "r") as f:
    CREDS = json.load(f)

# IP address of each honeypot
HONEYPOT_HOSTS = {
    "cowrie": "192.168.186.136",
    "honeypy": "192.168.186.137",
    "honeytrap": "192.168.186.138",
    "conpot": "192.168.186.139",
    "nodepot-lite": "192.168.186.137"  # same as honeypy
}

# SSH port for each honeypot
HONEYPOT_PORTS = {
    "cowrie": 22,
    "honeypy": 22,
    "honeytrap": 2222,
    "conpot": 22,
    "nodepot-lite": 22
}

# Get credentials for any honeypot
def get_creds(hp):
    return HONEYPOT_HOSTS[hp], CREDS[hp]["username"], CREDS[hp]["password"], HONEYPOT_PORTS[hp]

# SSH execution with password
def ssh_exec(ip, username, password, command, port=22):
    ssh_cmd = [
        "sshpass", "-p", password,
        "ssh", "-p", str(port),
        "-o", "StrictHostKeyChecking=no",
        f"{username}@{ip}", command
    ]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        return True, result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return False, str(e)

# Log actuator results to MongoDB
def log_action(hp, plugin, act_type, cmd, output, success, action_id):
    error_keywords = ["No such file", "command not found", "Failed", "Error", "permission denied"]
    for keyword in error_keywords:
        if keyword.lower() in output.lower():
            print(f"[❌] Detected failure in output: '{keyword}' → setting success = False")
            success = False
            break

    log_entry = {
        "timestamp": datetime.now(timezone.utc),
        "honeypot": hp,
        "plugin": plugin,
        "action": act_type,
        "command": cmd,
        "result": output,
        "success": success,
        "action_id": action_id
    }

    log_collection = MongoClient("mongodb://localhost:27017/")["adapttrap"]["actuator_logs"]
    log_collection.insert_one(log_entry)
    print("[📝] Logged to actuator_logs.")
