#!/usr/bin/env python3

import time
from pymongo import MongoClient
from bson.objectid import ObjectId

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["adapttrap"]
normalized = db["normalized_logs"]

print("📡 Watching normalized_logs in real-time...\n")

last_seen_id = None
try:
    while True:
        query = {}
        if last_seen_id:
            query["_id"] = {"$gt": last_seen_id}

        cursor = normalized.find(query).sort("_id", 1)
        new_count = 0

        for doc in cursor:
            last_seen_id = doc["_id"]
            new_count += 1

            print(f"\n🆕 [{doc.get('timestamp')}] {doc.get('source')} → {doc.get('ip')}:{doc.get('port')}")
            print(f"   Protocol: {doc.get('protocol')}")
            print(f"   Tags    : {doc.get('tags')}")
            print(f"   Raw Log : {doc.get('raw_log')}")
            print("-" * 60)

        if new_count == 0:
            print(".", end="", flush=True)

        time.sleep(2)

except KeyboardInterrupt:
    print("\n👋 Monitoring stopped.")
