#!/usr/bin/env python3

from pymongo import MongoClient
from datetime import datetime
import re

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["adapttrap"]
src = db["honeytrap_logs"]
dst = db["normalized_logs"]

print("[*] Parsing Honeytrap logs from Docker...")

HONEYPOT_IPS = {
    "192.168.186.135",  # Adapttrapmain
    "192.168.186.138",  # Honeytrap VM
}

def tag_log(entry):
    raw = entry.get("raw_log", "").lower()
    if "password" in raw or "authentication" in raw:
        return "brute-force"
    elif "telnet.command" in entry:
        return "session-command"
    return "unknown"

inserted = 0

for doc in src.find():
    src_ip = doc.get("source-ip", "")
    dst_ip = doc.get("destination-ip", "")
    src_port = doc.get("source-port", "")
    dst_port = doc.get("destination-port", "")
    proto = "tcp"
    
    if src_ip in HONEYPOT_IPS:
        continue  # skip internal logs

    normalized = {
        "timestamp": doc.get("timestamp", datetime.utcnow()),
        "source": "honeytrap",
        "ip": src_ip,
        "port": int(src_port) if str(src_port).isdigit() else None,
        "protocol": proto,
        "raw_log": doc.get("raw_log", ""),
        "tag": tag_log(doc),
        "log_source": "docker"
    }

    dst.insert_one(normalized)
    inserted += 1

print(f"[+] Normalized and inserted {inserted} Docker logs into 'normalized_logs'")
