from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, timedelta
from app.schemas.job import JobResponse
from app.db.jobs import get_job, get_dataset_lastest_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return {
        "id": job["_id"],
        "dataset_id": job["dataset_id"],
        "status": job["status"],
        "created_at": job["created_at"],
        "finished_at": job.get("finished_at"),
        "error": job.get("error")
    }

@router.get("/dataset_latest_job/{dataset_id}", response_model=Optional[JobResponse])
async def get_dataset_latest_job(dataset_id: str):
    job = await get_dataset_lastest_job(dataset_id)
    if not job:
        return None

    if job["status"] == "running":
        now = datetime.now()

        threshold = now - timedelta(hours=3)

        # Jika waktu buat job LEBIH LAMA (lebih kecil) dari batas 3 jam lalu
        if job["created_at"] < threshold:
            return None

    return {
        "id": job["_id"],
        "dataset_id": job["dataset_id"],
        "status": job["status"],
        "created_at": job["created_at"],
        "finished_at": job.get("finished_at"),
        "error": job.get("error")
    }