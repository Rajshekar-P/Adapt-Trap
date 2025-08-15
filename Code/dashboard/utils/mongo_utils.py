import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import MONGO_URI, DB_NAME, COLLECTION_NAME
from pymongo import MongoClient  # ✅ This line fixes the error


def get_mongo_collection():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]

def fetch_logs(limit=1000):
    collection = get_mongo_collection()
    return list(collection.find().sort("timestamp", -1).limit(limit))
