#!/usr/bin/env python3
from __future__ import annotations

import re, ipaddress
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any, Dict, Optional, Tuple
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["adapttrap"]
normalized = db["normalized_logs"]

# ------------------------------------------------------------------
# SAFETY: do NOT wipe by default. Set to True only if you intend to rebuild.
# ------------------------------------------------------------------
SAFE_CLEAR = False
if SAFE_CLEAR:
    print("[!] Clearing existing normalized_logs (SAFE_CLEAR=True)")
    normalized.delete_many({})

# Honeypot VM IPs (kept but tagged as internal_honeypot for filtering)
HONEYPOT_IPS = {
    "192.168.186.136",
    "192.168.186.137",
    "192.168.186.138",
    "192.168.186.139",
}
LOCAL_BINDS = {"0.0.0.0", "127.0.0.1"}

sources = {
    "cowrie_logs": "cowrie",
    "honeypy_logs": "honeypy",
    "honeytrap_logs": "honeytrap",
    "conpot_logs": "conpot",
    "nodepot_logs": "nodepot-lite",
}

ip_to_ports = defaultdict(set)

# ---------- helpers ----------
def ipv4_mapped_to_ipv4(ip: str) -> str:
    if isinstance(ip, str) and ip.startswith("::ffff:"):
        cand = ip.split("::ffff:")[-1]
        try:
            ipaddress.ip_address(cand)
            return cand
        except ValueError:
            pass
    return ip

def is_valid_ip(ip: str) -> bool:
    if not isinstance(ip, str):
        return False
    ip = ipv4_mapped_to_ipv4(ip)
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def parse_any_ip_port(text: str) -> Tuple[str, Optional[int]]:
    """
    Best-effort attacker IP/port extraction from free-form logs.

    Handles:
      - Cowrie: "New connection: A.B.C.D:p (X.Y.Z.W:q)"
      - HoneyPy: "FTP connection from A.B.C.D:p"
      - Generic: "A.B.C.D:p"
      - Tuple-style: "('A.B.C.D', p)" or "from ('A.B.C.D', p)"
      - Bracketed: "[..., A.B.C.D]" + "port N"
    """
    text = text or ""

    # 1) Cowrie style
    m = re.search(r"New connection:\s+([\d\.]+):(\d+)\s+\(([\d\.]+):(\d+)\)", text)
    if m:
        a, ap, b, bp = m.groups()
        a, b = ipv4_mapped_to_ipv4(a), ipv4_mapped_to_ipv4(b)
        if a not in HONEYPOT_IPS | LOCAL_BINDS and is_valid_ip(a):
            return a, int(ap)
        if b not in HONEYPOT_IPS | LOCAL_BINDS and is_valid_ip(b):
            return b, int(bp)

    # 2) HoneyPy FTP line
    m = re.search(r"FTP connection from\s+([\d\.]+):(\d+)", text)
    if m:
        ip, p = m.groups()
        ip = ipv4_mapped_to_ipv4(ip)
        if ip not in HONEYPOT_IPS | LOCAL_BINDS and is_valid_ip(ip):
            return ip, int(p)

    # 3) Tuple style "('A.B.C.D', 12345)" (Conpot & generic Python logs)
    m = re.search(r"\('(\d{1,3}(?:\.\d{1,3}){3})'\s*,\s*(\d+)\)", text)
    if m:
        ip, p = m.groups()
        ip = ipv4_mapped_to_ipv4(ip)
        if ip not in HONEYPOT_IPS | LOCAL_BINDS and is_valid_ip(ip):
            return ip, int(p)

    # 4) Generic "A.B.C.D:PORT"
    m = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3}):(\d+)\b", text)
    if m:
        ip, p = m.groups()
        ip = ipv4_mapped_to_ipv4(ip)
        if ip not in HONEYPOT_IPS | LOCAL_BINDS and is_valid_ip(ip):
            return ip, int(p)

    # 5) Standalone IP + "port N"
    m_ip = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", text)
    m_po = re.search(r"port\s+(\d+)", text.lower())
    if m_ip:
        ip = ipv4_mapped_to_ipv4(m_ip.group(1))
        if ip not in HONEYPOT_IPS | LOCAL_BINDS and is_valid_ip(ip):
            return ip, int(m_po.group(1)) if m_po else None

    return "unknown", None

def detect_protocol(text: str, port: Optional[int]) -> str:
    t = (text or "").lower()
    if "ssh" in t or port in {22, 2222}:
        return "ssh"
    if "http" in t or port in {80, 8080, 8800, 9999}:
        return "http"
    if "ftp" in t or port in {21, 2244}:
        return "ftp"
    if "modbus" in t or port in {502, 5020}:
        return "modbus"
    if "bacnet" in t or port in {47808}:
        return "bacnet"
    if port == 23 or "telnet" in t:
        return "telnet"
    return "unknown"

def tag_rules(text: str, ip: str) -> list[str]:
    tags = []
    t = (text or "").lower()
    if any(k in t for k in ("nmap", "masscan")):
        tags.append("nmap")
    if re.search(r"\b(netcat|nc)\b", t):
        tags.append("netcat")
    if "libssh" in t:
        tags.append("libssh")
    if "failed login" in t or "authentication failed" in t:
        tags.append("ssh_brute")
    if "login attempt" in t or "user root" in t:
        tags.append("login_attempt")
    if "upload" in t or "multipart/form-data" in t or "file saved" in t:
        tags.append("upload")
    if ("select" in t and "--" in t) or "union select" in t or " or 1=1" in t:
        tags.append("sqli")
    if "../" in t or "/etc/passwd" in t:
        tags.append("dir_traversal")
    if ip != "unknown" and len(ip_to_ports[ip]) > 10:
        tags.append("port_scan")
    return tags

# ---------- per-source ----------
def finalize_record(ts, src, ip, port, proto, raw, extra_tags=None):
    tags = tag_rules(raw, ip)
    if extra_tags:
        tags.extend([t for t in extra_tags if t not in tags])
    # Tag internal honeypot traffic (kept visible)
    if ip in HONEYPOT_IPS:
        tags.append("internal_honeypot")
    rec = {
        "timestamp": ts,
        "source": src,
        "ip": ip,
        "port": port if port is not None else "unknown",
        "protocol": proto,
        "raw_log": raw,
        "tags": tags,
    }
    return rec

def normalize_nodepot(doc: Dict[str, Any]) -> Dict[str, Any]:
    raw = doc.get("raw_log") or ""
    uri = (doc.get("uri") or "").lower()
    event_type = (doc.get("event_type") or "").lower()
    ts = doc.get("timestamp") or datetime.now(timezone.utc)

    ip_struct = ipv4_mapped_to_ipv4(doc.get("ip", "unknown"))
    ip_parsed, _ = parse_any_ip_port(raw)

    if is_valid_ip(ip_struct):
        ip = ip_struct
    elif is_valid_ip(ip_parsed):
        ip = ip_parsed
    else:
        ip = "unknown"

    extra = []
    if "upload" in event_type or "upload" in uri or "multipart/form-data" in raw.lower():
        extra.append("upload")
    if "login" in event_type or "login attempt" in raw.lower():
        extra.append("login_attempt")
    if any(k in uri for k in ("admin", "upload", "shell", "config", ".php", ".asp", ".jspx", ".aspx")):
        extra.append("suspicious_uri")

    return finalize_record(ts, "nodepot-lite", ip, 80, "http", raw if raw else f"{event_type} {uri}", extra)

def normalize_honeypy(doc: Dict[str, Any]) -> Dict[str, Any]:
    ip = ipv4_mapped_to_ipv4(doc.get("src_ip") or doc.get("ip") or "unknown")
    port = doc.get("src_port") or doc.get("port")
    raw = doc.get("raw_log") or doc.get("message") or ""
    ts = doc.get("timestamp") or datetime.now(timezone.utc)

    if (not is_valid_ip(ip)) or ip in HONEYPOT_IPS | LOCAL_BINDS:
        ip, port = parse_any_ip_port(raw)

    proto = "ftp" if (port in {21, 2244}) or ("ftp" in (raw or "").lower()) else detect_protocol(raw, port)
    return finalize_record(ts, "honeypy",
                           ip if is_valid_ip(ip) else "unknown",
                           int(port) if isinstance(port, (int,)) or (isinstance(port, str) and port.isdigit()) else "unknown",
                           proto, raw, ["ftp_connection"] if proto == "ftp" else None)

def normalize_honeytrap(doc: Dict[str, Any]) -> Dict[str, Any]:
    ip = ipv4_mapped_to_ipv4(doc.get("src_ip") or doc.get("remote_host") or doc.get("ip") or "unknown")
    port = doc.get("src_port") or doc.get("remote_port") or doc.get("port")
    raw = doc.get("raw_log") or doc.get("message") or ""
    ts = doc.get("timestamp") or datetime.now(timezone.utc)

    # skip heartbeats on backfill too
    if "heartbeat" in (raw or "").lower():
        return None

    if (not is_valid_ip(ip)) or ip in HONEYPOT_IPS | LOCAL_BINDS:
        ip, port = parse_any_ip_port(raw)

    proto = detect_protocol(raw, port)
    return finalize_record(ts, "honeytrap",
                           ip if is_valid_ip(ip) else "unknown",
                           int(port) if isinstance(port, (int,)) or (isinstance(port, str) and port.isdigit()) else "unknown",
                           proto, raw, None)

def normalize_conpot(doc: Dict[str, Any]) -> Dict[str, Any]:
    raw = str(doc.get("raw_log", ""))
    ts = doc.get("timestamp") or datetime.now(timezone.utc)

    # Treat obvious startup/noise as non-attacker → still record, but IP stays unknown
    if any(k in raw.lower() for k in (
        "server started on", "serving tcp/ip", "responding to external done/disable signal"
    )):
        return finalize_record(ts, "conpot", "unknown", "unknown", detect_protocol(raw, None), raw, None)

    ip, port = parse_any_ip_port(raw)
    proto = detect_protocol(raw, port)
    return finalize_record(ts, "conpot", ip, port, proto, raw, None)

# ---------- main run ----------
inserted = 0
for coll_name, src in sources.items():
    for doc in db[coll_name].find({}):
        if src == "nodepot-lite":
            norm = normalize_nodepot(doc)
        elif src == "honeypy":
            norm = normalize_honeypy(doc)
        elif src == "honeytrap":
            norm = normalize_honeytrap(doc)
            if norm is None:  # heartbeat skip
                continue
        elif src == "conpot":
            norm = normalize_conpot(doc)
        else:
            raw = str(doc.get("raw_log", ""))
            ts = doc.get("timestamp") or datetime.now(timezone.utc)
            ip, port = parse_any_ip_port(raw)
            if ip != "unknown" and isinstance(port, int):
                ip_to_ports[ip].add(port)
            proto = detect_protocol(raw, port)
            norm = finalize_record(ts, src, ip if is_valid_ip(ip) else "unknown",
                                   port if port is not None else "unknown",
                                   proto, raw, None)

        normalized.insert_one(norm)
        inserted += 1
        if inserted % 1000 == 0:
            print(f"[+] Backfilled {inserted} records...")

print(f"\n✅ Historical normalization complete. Inserted: {inserted}")
