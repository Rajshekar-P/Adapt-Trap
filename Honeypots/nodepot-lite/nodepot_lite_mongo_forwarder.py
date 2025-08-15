import subprocess
import time
import pymongo
import re
from datetime import datetime

# MongoDB setup
client = pymongo.MongoClient("mongodb://192.168.186.135:27017/")
db = client["adapttrap"]
collection = db["nodepot_logs"]

# ✅ Updated Regex Pattern
log_pattern = re.compile(r"\[(.*?)\]\s+(?:::ffff:)?(\d+\.\d+\.\d+\.\d+)\s+(\w+)\s+(\/.*)")

print("[*] Starting log forwarder for Nodepot Lite...")

process = subprocess.Popen(
    ["docker", "exec", "-i", "nodepot-lite", "tail", "-F", "/app/honeypot.log"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    universal_newlines=True
)

for line in process.stdout:
    line = line.strip()
    print("[+] Log:", line)

    match = log_pattern.match(line)
    if match:
        ts_raw, ip, method, uri = match.groups()
        try:
            timestamp = datetime.strptime(ts_raw, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            print("[-] Timestamp format error:", ts_raw)
            continue

        doc = {
            "timestamp": timestamp,
            "source": "nodepot-lite",
            "ip": ip,
            "method": method,
            "uri": uri,
            "raw_log": line
        }
        collection.insert_one(doc)
        print("[✓] Inserted into MongoDB:", doc)
    else:
        print("[-] Could not parse:", line)
