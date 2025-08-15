from pymongo import MongoClient
import pandas as pd

def get_db():
    client = MongoClient("mongodb://localhost:27017")
    return client["adapttrap"]

def get_normalized_logs():
    db = get_db()
    cursor = db["normalized_logs"].find()
    return pd.DataFrame(list(cursor))

def get_plugin_states():
    db = get_db()
    cursor = db["plugin_states"].find()
    return pd.DataFrame(list(cursor))

def get_agent_actions():
    db = get_db()
    cursor = db["agent_actions"].find().sort("created_at", -1).limit(100)
    return pd.DataFrame(list(cursor))


# === utils/summarize_logs.py ===
def get_summary_metrics(df):
    return {
        "count": len(df),
        "unique_ips": df["ip"].nunique(),
        "tagged": df["tags"].apply(lambda x: len(x) > 0).sum()
    }