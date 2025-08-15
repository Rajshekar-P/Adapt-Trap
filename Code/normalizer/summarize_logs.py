#!/usr/bin/env python3

from pymongo import MongoClient
from collections import Counter
from datetime import datetime, timedelta
import pandas as pd

# MongoDB connection
MONGO_URI = "mongodb://127.0.0.1:27017/"
DB_NAME = "adapttrap"
COLLECTION_NAME = "normalized_logs"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

print("\n--- Honeypot Attack Summary ---")

# 1. Logs per honeypot source
print("\n📊 Logs by Honeypot Source:")
source_cursor = collection.aggregate([
    {"$group": {"_id": "$source", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
])
for item in source_cursor:
    source = item['_id'] if item['_id'] else 'unknown'
    print(f"  {source}: {item['count']} logs")

# 2. Top Protocols used
print("\n📡 Top Protocols:")
protocol_cursor = collection.aggregate([
    {"$group": {"_id": "$protocol", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
])
for item in protocol_cursor:
    proto = item['_id'] if item['_id'] else 'unknown'
    print(f"  {proto}: {item['count']}")

# 3. Top 10 targeted ports
print("\n🎯 Top 10 Targeted Ports:")
port_cursor = collection.aggregate([
    {"$group": {"_id": "$port", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 10}
])
for item in port_cursor:
    port = str(item['_id']) if item['_id'] != "" else "unknown"
    print(f"  Port {port}: {item['count']} times")

# 4. Top 10 attacker IPs
print("\n🚨 Top 10 Attacker IPs:")
ip_cursor = collection.aggregate([
    {"$group": {"_id": "$ip", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 10}
])
for item in ip_cursor:
    ip = item['_id'] if item['_id'] else 'unknown'
    print(f"  IP {ip}: {item['count']} attacks")

# 5. Tags Breakdown
print("\n🏷️ Top Tags (Attack Techniques/Tools):")
tag_cursor = collection.aggregate([
    {"$unwind": "$tags"},
    {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 10}
])
for item in tag_cursor:
    tag = item['_id'] if item['_id'] else 'unknown'
    print(f"  {tag}: {item['count']}")

client.close()
