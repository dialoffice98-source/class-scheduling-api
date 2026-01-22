from fastapi import APIRouter, HTTPException
from app.db.datasets import get_dataset
from app.db.jobs import create_job, get_dataset_lastest_job
from app.workers.tasks import run_scheduler_task # Import Task Celery
import uuid

router = APIRouter(prefix="/schedule", tags=["Scheduler"])

@router.post("/{dataset_id}")
async def run_schedule(dataset_id: str):
    # Ambil job terakhir dari database
    last_job = await get_dataset_lastest_job(dataset_id)
    
    # Cek:
    # 1. Apakah 'last_job' ditemukan? (Kalau None berarti belum pernah ada job, boleh lanjut)
    # 2. Jika ada, apakah statusnya "queued" atau "running"?
    if last_job:
        status = last_job.get("status") # Ambil value status
        
        if status in ["queued", "running"]:
            # JANGAN LANJUT. Lempar Error ke Frontend.
            # 400 = Bad Request, atau bisa pakai 409 = Conflict
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot start new schedule. Last job is still {status}."
            )
    
    # 1. Cek Dataset (Async)
    dataset = await get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    # 2. Buat Job ID
    job_id = str(uuid.uuid4())

    # 3. Simpan Job awal di DB (Async)
    await create_job(job_id, dataset_id)

    # 4. Trigger Celery Task (Fire-and-forget)
    # .delay() mengirim pesan ke Redis
    run_scheduler_task.delay(job_id, dataset_id)

    return {
        "job_id": job_id,
        "status": "queued"
    }