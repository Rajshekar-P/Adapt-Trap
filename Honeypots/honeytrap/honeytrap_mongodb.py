#!/usr/bin/env python3

from pymongo import MongoClient
from datetime import datetime
import time
import os

HONEYTRAP_LOG_PATH = '/home/honeytrap/honeytrap/honeytrap-logs/honeytrap.log'
MONGO_HOST = '192.168.186.135'
MONGO_PORT = 27017
MONGO_DB = 'adapttrap'
MONGO_COLLECTION = 'honeytrap_logs'

def connect_mongo():
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    db = client[MONGO_DB]
    collection = db[MONGO_COLLECTION]
    return collection

def tail(f):
    f.seek(0, os.SEEK_END)
    while True:
        line = f.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

def parse_log_line(line):
    # This is a simple example — adjust if you want structured fields
    return {
        'timestamp': datetime.utcnow(),
        'source': 'honeytrap',
        'raw_log': line.strip()
    }

def main():
    print("📡 Starting HoneyTrap MongoDB Logger…")
    collection = connect_mongo()
    with open(HONEYTRAP_LOG_PATH, 'r') as logfile:
        loglines = tail(logfile)
        for line in loglines:
            doc = parse_log_line(line)
            collection.insert_one(doc)
            print(f"✅ Inserted: {doc}")

if __name__ == "__main__":
    main()
