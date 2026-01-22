from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]

# Collections
jobs_col = db["jobs"]
datasets_col = db["datasets"]
results_col = db["results"]