#!/usr/bin/env python3

from pymongo import MongoClient
from datetime import datetime, timezone
import time
import os

MONGO_URI = "mongodb://192.168.186.135:27017"
DB_NAME = "adapttrap"
COLLECTION_NAME = "cowrie_logs"
LOG_PATH = "/home/cowrie/cowrie/var/log/cowrie/cowrie.log"

def tail(f):
    f.seek(0, 2)  # move to end of file
    while True:
        line = f.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

def wait_for_logfile(path, retries=30, delay=2):
    print(f"⏳ Waiting for log file: {path}")
    for i in range(retries):
        if os.path.exists(path):
            print("✅ Log file found.")
            return
        time.sleep(delay)
    raise FileNotFoundError(f"❌ Log file not found after {retries * delay} seconds: {path}")

def main():
    print("📡 Starting Cowrie MongoDB Logger…")
    wait_for_logfile(LOG_PATH)

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll = db[COLLECTION_NAME]

    with open(LOG_PATH, 'r') as logfile:
        loglines = tail(logfile)
        for line in loglines:
            doc = {
                "timestamp": datetime.now(timezone.utc),  # Fixed timezone warning
                "source": "cowrie",
                "raw_log": line.strip()
            }
            coll.insert_one(doc)
            print(f"Inserted: {doc}")

if __name__ == "__main__":
    main()
