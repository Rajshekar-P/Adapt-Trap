#!/usr/bin/env python3
import os
import time
import hashlib
import datetime
import requests
from pymongo import MongoClient, ReturnDocument

# -------------------- CONFIG (env overrides available) --------------------
MONGO_URI     = os.getenv("MONGO_URI", "mongodb://192.168.186.135:27017/?authSource=adapttrap")
DB_NAME       = os.getenv("DB_NAME", "adapttrap")
LOGS_COLL     = os.getenv("LOGS_COLL", "nodepot_logs")
RESULTS_COLL  = os.getenv("RESULTS_COLL", "cape_results")   # for cross-check in dedup

# Host path that maps to the container's /app/uploads (adjust if different)
UPLOADS_DIR   = os.getenv("UPLOADS_DIR", "/home/honeypy/nodepot-lite/uploads")

# CAPE web API base (use .../apiv2). We append the endpoint + trailing slash.
CAPE_URL      = os.getenv("CAPE_URL", "http://192.168.186.139:8000/apiv2")
CAPE_TIMEOUT  = int(os.getenv("CAPE_TIMEOUT", "120"))
CAPE_PRIORITY = os.getenv("CAPE_PRIORITY", "")     # optional
CAPE_MACHINE  = os.getenv("CAPE_MACHINE", "")      # optional
CAPE_OPTIONS  = os.getenv("CAPE_OPTIONS", "")      # optional (e.g., "route=internet")
CAPE_TAGS     = os.getenv("CAPE_TAGS", "")         # optional (e.g., "win10")

# Worker behaviour
POLL_SECS     = float(os.getenv("POLL_SECS", "2.0"))
BATCH         = int(os.getenv("BATCH", "10"))
SCAN_RECENT   = int(os.getenv("SCAN_RECENT", "200"))  # fallback scan size

# De-duplication + lock behaviour
DEDUP_MINUTES       = int(os.getenv("DEDUP_MINUTES", "60"))    # 0 = dedup across all time
LOCK_EXPIRE_MINUTES = int(os.getenv("LOCK_EXPIRE_MINUTES", "10"))  # reclaim stuck "processing" docs after this

# -------------------- helpers --------------------
def _utcnow():
    return datetime.datetime.utcnow()

def _ago(minutes: int):
    return _utcnow() - datetime.timedelta(minutes=minutes)

def _norm_ip(ip):
    if not ip:
        return "unknown"
    return ip.split("::ffff:")[-1]

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def find_file_for_event(doc):
    """Find the uploaded file for a 'file_upload' log entry."""
    if not os.path.isdir(UPLOADS_DIR):
        return None

    stored_as = doc.get("stored_as") or doc.get("storedName") or doc.get("stored_name")
    orig_name = (doc.get("filename") or doc.get("originalName") or doc.get("original_name") or "").strip()
    want_sha  = (doc.get("sha256") or "").lower()

    candidates = []
    if stored_as:
        candidates.append(os.path.join(UPLOADS_DIR, stored_as))
    if want_sha:
        candidates.append(os.path.join(UPLOADS_DIR, want_sha))
        candidates.append(os.path.join(UPLOADS_DIR, f"{want_sha}.bin"))

    for p in candidates:
        if p and os.path.exists(p):
            return p

    try:
        files = [os.path.join(UPLOADS_DIR, x) for x in os.listdir(UPLOADS_DIR)]
        files = [p for p in files if os.path.isfile(p)]
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    except Exception:
        files = []

    if orig_name:
        safe_stub = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in orig_name)[:50]
        for p in files[:SCAN_RECENT]:
            if safe_stub and safe_stub in os.path.basename(p):
                return p

    if want_sha:
        for p in files[:SCAN_RECENT]:
            try:
                if sha256_of(p) == want_sha:
                    return p
            except Exception:
                pass

    return None

def _extract_task_id(resp_json):
    """
    CAPE can return different shapes. Try several.
      {"data":{"task_ids":[41]}, ...}
      {"task_ids":[41], ...}
      {"task_id": 41, ...}
    """
    if not isinstance(resp_json, dict):
        return None
    data = resp_json.get("data")
    if isinstance(data, dict):
        tids = data.get("task_ids")
        if isinstance(tids, list) and tids:
            return tids[0]
        if isinstance(tids, int):
            return tids
    tids = resp_json.get("task_ids")
    if isinstance(tids, list) and tids:
        return tids[0]
    if isinstance(tids, int):
        return tids
    single = resp_json.get("task_id")
    if isinstance(single, int):
        return single
    return None

def submit_to_cape(path, original_name, src_ip, sha256):
    """Submit a file to CAPE and return (task_id, raw_response_text)."""
    url = f"{CAPE_URL.rstrip('/')}/tasks/create/file/"  # NOTE trailing slash

    data = {}
    if CAPE_TAGS:
        data["tags"] = CAPE_TAGS
    if CAPE_PRIORITY:
        data["priority"] = CAPE_PRIORITY
    if CAPE_MACHINE:
        data["machine"] = CAPE_MACHINE
    if CAPE_OPTIONS:
        data["options"] = CAPE_OPTIONS

    with open(path, "rb") as fh:
        files = {"file": (original_name or os.path.basename(path), fh, "application/octet-stream")}
        r = requests.post(url, data=data, files=files, timeout=CAPE_TIMEOUT)
    r.raise_for_status()

    # If CAPE returns {"error": true, ...} treat it as a failure:
    try:
        j = r.json()
        if isinstance(j, dict) and j.get("error"):
            raise RuntimeError(f"CAPE error: {j.get('error_value') or j}")
        task_id = _extract_task_id(j)
    except ValueError:
        # not JSON, let the caller see raw text with task_id=None
        task_id = None

    return task_id, r.text

# -------------------- de-dup helpers --------------------
def _recent_window_clause():
    """Build a time filter if we have a dedup window; otherwise return None."""
    if DEDUP_MINUTES <= 0:
        return None
    since = _ago(DEDUP_MINUTES)
    return {"$or": [
        {"timestamp": {"$gte": since}},
        {"updated_at": {"$gte": since}},
        {"cape_report_time": {"$gte": since}},
        {"ingested_at": {"$gte": since}},
    ]}

def already_forwarded(cli: MongoClient, sha256: str) -> bool:
    """
    True if the same sha256 was already forwarded recently
    (or at any time if timestamps are missing).
    Checks both LOGS_COLL and RESULTS_COLL, and also considers items currently 'processing'.
    """
    if not sha256:
        return False

    db = cli[DB_NAME]
    t_clause = _recent_window_clause()

    # Logs: forwarded OR currently processing with that sha
    log_q = {
        "$and": [
            {"dead": {"$ne": True}},
            {"$or": [{"sha256": sha256}, {"cape_sha256": sha256}]},
            {"$or": [{"forwarded": True}, {"processing": True}]}
        ]
    }
    if t_clause:
        log_q["$and"].append(t_clause)
    if db[LOGS_COLL].count_documents(log_q, limit=1) > 0:
        return True

    # Results (fast)
    res_q = {"sha256": sha256}
    if t_clause:
        res_q = {"$and": [res_q, t_clause]}
    if db[RESULTS_COLL].count_documents(res_q, limit=1) > 0:
        return True

    return False

# -------------------- atomic claim --------------------
def claim_next(coll) -> dict | None:
    """
    Atomically claim one pending upload document for processing.
    Ensures multiple workers don't grab the same doc.
    Stale locks older than LOCK_EXPIRE_MINUTES are ignored/reclaimed.
    """
    stale = _ago(LOCK_EXPIRE_MINUTES)
    return coll.find_one_and_update(
        {
            "event_type": "file_upload",
            "dead": {"$ne": True},
            "$or": [{"forwarded": {"$exists": False}}, {"forwarded": False}],
            "$or": [
                {"processing": {"$exists": False}},
                {"processing": False},
                {"processing_at": {"$lt": stale}},
            ],
        },
        {"$set": {"processing": True, "processing_at": _utcnow()}},
        sort=[("_id", 1)],
        return_document=ReturnDocument.AFTER,
    )

# -------------------- main loop --------------------
def main():
    cli  = MongoClient(MONGO_URI)
    coll = cli[DB_NAME][LOGS_COLL]
    print(f"[*] nodepot → CAPE forwarder started | MONGO={MONGO_URI} | CAPE={CAPE_URL} | DEDUP_MINUTES={DEDUP_MINUTES} | LOCK_EXPIRE_MINUTES={LOCK_EXPIRE_MINUTES}")

    while True:
        processed_in_cycle = 0

        # Claim up to BATCH items atomically
        for _ in range(BATCH):
            doc = claim_next(coll)
            if not doc:
                break

            _id        = doc["_id"]
            ip         = _norm_ip(doc.get("ip") or doc.get("source_ip"))
            orig_name  = doc.get("filename") or doc.get("originalName") or "upload.bin"
            logged_sha = (doc.get("sha256") or "").lower()

            try:
                path = find_file_for_event(doc)
                if not path:
                    coll.find_one_and_update(
                        {"_id": _id},
                        {"$set": {
                            "forwarded": False,
                            "dead": True,  # permanently skip
                            "processing": False,
                            "forward_error": f"file not found in {UPLOADS_DIR}",
                            "updated_at": _utcnow(),
                        }}
                    )
                    print(f"[-] {_id}: file missing (uploads={UPLOADS_DIR}) — marked dead")
                    continue

                try:
                    real_sha = sha256_of(path)
                except Exception as e:
                    real_sha = logged_sha or "unknown"
                    print(f"[!] {_id}: sha256 compute error: {e}")

                # ---- DEDUP CHECK ----
                try:
                    if already_forwarded(cli, real_sha):
                        coll.find_one_and_update(
                            {"_id": _id},
                            {"$set": {
                                "forwarded": False,
                                "dead": True,
                                "processing": False,
                                "duplicate_of_sha256": real_sha,
                                "forward_error": f"dedup: sha256 {real_sha} already forwarded within {DEDUP_MINUTES}m",
                                "updated_at": _utcnow(),
                            }}
                        )
                        print(f"[=] {_id}: dedup — {orig_name} (sha256={real_sha}) already submitted; skipping")
                        continue
                except Exception as e:
                    # Non-fatal: if dedup check fails, continue with submission
                    print(f"[!] {_id}: dedup check error: {e}")

                stored_name = os.path.basename(path)
                task_id, cape_resp = submit_to_cape(path, orig_name, ip, real_sha)

                coll.find_one_and_update(
                    {"_id": _id},
                    {"$set": {
                        "forwarded": True,
                        "processing": False,
                        "cape_task_id": task_id,
                        "cape_response": cape_resp,
                        "cape_sha256": real_sha,
                        "updated_at": _utcnow(),
                    }}
                )

                if task_id is None:
                    print(f"[+] {_id}: forwarded {stored_name} -> CAPE (no task_id parsed). Raw resp:")
                    print(cape_resp)
                else:
                    print(f"[+] {_id}: forwarded {stored_name} -> CAPE task {task_id}")

                processed_in_cycle += 1

            except Exception as e:
                coll.find_one_and_update(
                    {"_id": _id},
                    {"$set": {
                        "forwarded": False,
                        "processing": False,
                        "forward_error": str(e),
                        "updated_at": _utcnow(),
                    }}
                )
                print(f"[-] {_id}: CAPE submit failed: {e}")

        if processed_in_cycle == 0:
            time.sleep(POLL_SECS)

if __name__ == "__main__":
    main()
