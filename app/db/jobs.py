from datetime import datetime
from app.db.mongo_async import jobs_col

async def create_job(job_id: str, dataset_id: str):
    await jobs_col.insert_one({
        "_id": job_id,
        "dataset_id": dataset_id,
        "status": "queued",  # Ubah status awal jadi 'queued'
        "created_at": datetime.utcnow(),
        "finished_at": None,
        "error": None
    })

async def get_job(job_id: str):
    return await jobs_col.find_one({"_id": job_id})

async def get_dataset_lastest_job(dataset_id: str):
    return await jobs_col.find_one({"dataset_id": dataset_id}, sort=[("created_at", -1)])
    return await jobs_col.find_one({"_id": job_id})