#normalizer_loop.py
#!/usr/bin/env python3

import time
from datetime import datetime, timezone
import re
import ipaddress
from collections import defaultdict
from pymongo import MongoClient
from bson.objectid import ObjectId

# === MongoDB Setup ===
client = MongoClient("mongodb://localhost:27017/")
db = client["adapttrap"]
normalized = db["normalized_logs"]

# === Honeypot IPs to ignore ===
HONEYPOT_IPS = {
    "192.168.186.135",  # adapttrapmain
    "192.168.186.136",  # cowrie
    "192.168.186.137",  # honeypy
    "192.168.186.138",  # honeytrap
    "192.168.186.139",  # conpot
}

# === Honeypot source collections ===
sources = {
    "cowrie_logs": "cowrie",
    "honeypy_logs": "honeypy",
    "honeytrap_logs": "honeytrap",
    "conpot_logs": "conpot",
    "nodepot_logs": "nodepot-lite"
}

# === State tracking ===
last_ids = {}
ip_to_ports = defaultdict(set)
print("🔁 Real-time normalization started... Press Ctrl+C to stop.\n")

# === Utility Functions ===
def is_valid_ip(ip_str):
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def extract_ip_port(log_str):
    match = re.search(r'New connection: ([\d.]+):(\d+) \(([\d.]+):(\d+)\)', log_str)
    if match:
        src_ip, src_port, dst_ip, dst_port = match.groups()
        if src_ip not in HONEYPOT_IPS and is_valid_ip(src_ip):
            return src_ip, int(src_port)
        elif dst_ip not in HONEYPOT_IPS and is_valid_ip(dst_ip):
            return dst_ip, int(dst_port)

    for m in re.finditer(r'([\d.]+):(\d+)', log_str):
        ip, port = m.groups()
        if ip not in HONEYPOT_IPS and is_valid_ip(ip):
            return ip, int(port)

    match_ip = re.search(r'\[.*?,\d+,([\d.]+)\]', log_str)
    match_port = re.search(r'port (\d+)', log_str.lower())
    ip = match_ip.group(1) if match_ip and is_valid_ip(match_ip.group(1)) else "unknown"
    port = int(match_port.group(1)) if match_port else "unknown"
    return ip, port

def detect_protocol(log_str, port=None):
    l = log_str.lower()
    if "ssh" in l or port == 22 or port == 2222:
        return "ssh"
    elif "http" in l or port in [80, 8080, 8808, 9999]:
        return "http"
    elif "ftp" in l or port == 21 or port == 2244:
        return "ftp"
    elif "modbus" in l or port in [502, 5020]:
        return "modbus"
    elif port == 2223:
        return "telnet"
    return "unknown"

def generate_tags(log_str, ip):
    tags = []
    l = log_str.lower()
    if "nmap" in l or "masscan" in l:
        tags.append("nmap")
    if "netcat" in l or "nc" in l:
        tags.append("netcat")
    if "libssh" in l:
        tags.append("libssh")
    if "failed login" in l or "authentication failed" in l:
        tags.append("ssh_brute")
    if "user root" in l or "login attempt" in l:
        tags.append("login_attempt")
    if "upload" in l or "file saved" in l:
        tags.append("upload")
    if "sqli" in l or "select" in l and "--" in l:
        tags.append("sqli")
    if "../" in l or "etc/passwd" in l:
        tags.append("dir_traversal")
    if ip != "unknown" and len(ip_to_ports[ip]) > 10:
        tags.append("port_scan")
    return tags

# === Main Loop ===
try:
    while True:
        for collection_name, source_tag in sources.items():
            collection = db[collection_name]
            query = {}
            if last_ids.get(collection_name):
                query["_id"] = {"$gt": last_ids[collection_name]}

            cursor = collection.find(query).sort("_id", 1)
            for log in cursor:
                last_ids[collection_name] = log["_id"]

                raw_log = str(log.get("raw_log", ""))
                timestamp = log.get("timestamp", datetime.now(timezone.utc))
                ip, port = extract_ip_port(raw_log)

                if ip == "unknown" and port == "unknown":
                    continue

                protocol = detect_protocol(raw_log, port)
                tags = generate_tags(raw_log, ip)

                if ip != "unknown" and isinstance(port, int):
                    ip_to_ports[ip].add(port)

                normalized.insert_one({
                    "timestamp": timestamp,
                    "source": source_tag,
                    "ip": ip,
                    "port": port,
                    "protocol": protocol,
                    "raw_log": raw_log,
                    "tags": tags
                })

                print(f"[+] Normalized: {source_tag} | {ip}:{port} | {protocol} | Tags: {tags}")

        time.sleep(3)  # Poll interval

except KeyboardInterrupt:
    print("\n👋 Stopping normalizer loop. Goodbye.")
