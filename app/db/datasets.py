from datetime import datetime
from bson import ObjectId
from app.db.mongo_async import datasets_col

async def create_dataset(payload: dict) -> str:
    payload["created_at"] = datetime.utcnow()
    # Motor return InsertOneResult, kita ambil inserted_id
    res = await datasets_col.insert_one(payload)
    return str(res.inserted_id)

async def get_dataset(dataset_id: str):
    try:
        oid = ObjectId(dataset_id)
    except:
        return None
    return await datasets_col.find_one({"_id": oid})

async def list_datasets():
    # Motor cursor perlu di-to_list atau di-iterate dengan async for
    cursor = datasets_col.find().sort("created_at", -1)
    return await cursor.to_list(length=100)