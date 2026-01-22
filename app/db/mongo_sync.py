from pymongo import MongoClient
from app.core.config import settings

# Koneksi Sync standar
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]

def get_db_sync():
    return db