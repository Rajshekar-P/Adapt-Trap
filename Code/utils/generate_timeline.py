import json
from datetime import datetime

# Change to your JSON file path
INPUT_FILE = "session_7050ab501e43.json"

def parse_timestamp(ts_str):
    """
    Parse the ISO8601 timestamp to a datetime object.
    Example: '2025-07-21T23:45:02.302760Z'
    """
    return datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%fZ")

def load_records(filename):
    with open(filename, 'r') as f:
        return [json.loads(line) for line in f]

def generate_timeline(records):
    # Sort records by timestamp
    records.sort(key=lambda r: r['timestamp'])
    print(f"\nTimeline for session: {records[0]['session']}\n")
    for r in records:
        ts = parse_timestamp(r['timestamp'])
        cmd = r.get('input', '').strip()
        src_ip = r.get('src_ip', '')
        print(f"[{ts}] {src_ip} ran command: {cmd or '<empty>'}")

if __name__ == "__main__":
    records = load_records(INPUT_FILE)
    if not records:
        print("No records found.")
    else:
        generate_timeline(records)
