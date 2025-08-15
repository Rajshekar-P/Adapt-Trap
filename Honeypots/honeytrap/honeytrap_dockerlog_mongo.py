#!/usr/bin/env python3

import subprocess
import time
from pymongo import MongoClient
from datetime import datetime
import re

print("[*] Parsing Honeytrap logs from Docker...")

# MongoDB connection
client = MongoClient("mongodb://192.168.186.135:27017/")
db = client["adapttrap"]
collection = db["honeytrap_logs"]

# Start docker log stream with -f
proc = subprocess.Popen(
    ["docker", "logs", "-f", "honeytrap_honeytrap_1"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Simple regex patterns to extract fields
def extract_fields(line):
    doc = {
        "raw_log": line.strip(),
        "timestamp": datetime.utcnow(),
        "source": "honeytrap"
    }

    # Extract key=value fields (telnet.username=..., etc.)
    kv_pairs = re.findall(r'(\b[\w.-]+)=([^,]+)', line)
    for key, value in kv_pairs:
        doc[key.strip()] = value.strip()

    return doc

# Read line by line and insert
for line in proc.stdout:
    if not line.strip():
        continue
    try:
        doc = extract_fields(line)
        collection.insert_one(doc)
        print(f"[+] Inserted: {doc['raw_log']}")
    except Exception as e:
        print(f"[!] Error inserting log: {e}")
        continue
