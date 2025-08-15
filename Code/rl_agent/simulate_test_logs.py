#!/usr/bin/env python3

import random
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["adapttrap"]
collection = db["normalized_logs"]

# 🔖 Available test tags to simulate
TAGS_POOL = [
    "nmap", "netcat", "brute_force", "ssh_brute", "login_attempt",
    "dir_traversal", "sqli", "rce", "upload", "http", "ssh", "ftp"
]

# 💥 Simulate multiple attacker IPs
ATTACKER_IPS = ["10.20.30.40", "192.168.55.77", "8.8.4.4"]

# 🚀 Insert N logs
N = 50
now = datetime.now(timezone.utc)

for i in range(N):
    ip = random.choice(ATTACKER_IPS)
    port = random.randint(1024, 65535)
    tags = random.sample(TAGS_POOL, k=random.randint(1, 3))
    proto = "http" if "http" in tags else random.choice(["ssh", "ftp", "telnet"])
    timestamp = now - timedelta(seconds=random.randint(0, 1200))

    log = {
        "timestamp": timestamp,
        "source": random.choice(["cowrie", "honeypy", "honeytrap"]),
        "ip": ip,
        "port": port,
        "protocol": proto,
        "tags": tags,
        "raw_log": f"Simulated attack from {ip} with tags {tags}"
    }

    collection.insert_one(log)

print(f"✅ Inserted {N} simulated logs into normalized_logs.")
