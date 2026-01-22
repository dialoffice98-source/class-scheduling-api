from pymongo import MongoClient
from app.core.config import settings

client = MongoClient(settings.mongo_uri)

db = client[settings.mongo_db_name]

datasets_col = db["datasets"]
jobs_col = db["jobs"]
results_col = db["results"]