from celery import Task
from datetime import datetime
from bson import ObjectId
from app.core.celery_app import celery
from app.db.mongo_sync import get_db_sync
# Import fungsi berat Anda
from app.services.class_scheduling_main.source.class_scheduling import class_scheduling 

class SchedulingTask(Task):
    """Abstract task class untuk handling error database connection jika perlu"""
    pass

@celery.task(bind=True, base=SchedulingTask, name="run_scheduler_task")
def run_scheduler_task(self, job_id: str, dataset_id: str):
    db = get_db_sync()
    jobs_col = db["jobs"]
    datasets_col = db["datasets"]
    results_col = db["results"]

    # 1. Update Status -> RUNNING
    jobs_col.update_one(
        {"_id": job_id},
        {"$set": {"status": "running", "updated_at": datetime.utcnow()}}
    )

    try:
        # 2. Ambil Dataset (Sync)
        oid = ObjectId(dataset_id)
        dataset = datasets_col.find_one({"_id": oid}) # Pastikan tipe ID sesuai (ObjectId vs Str)
        if not dataset:
            raise ValueError(f"Dataset {oid} not found")

        # 3. Jalankan PROSES BERAT (CPU Bound)
        # Tidak memblokir FastAPI karena ini berjalan di proses worker terpisah
        result_data = class_scheduling(
            course_dict=dataset["course_dict"],
            room_dict=dataset["room_dict"],
            settings=dataset["settings"],
            faculty_preference_dict=dataset.get("faculty_preference_dict"),
            faculty_unavailability_dict=dataset.get("faculty_unavailability_dict"),
            quick_scheduling=dataset.get("quick_scheduling", False),
            verbose=False
        )

        # 4. Simpan Result
        results_col.insert_one({
            "job_id": job_id,
            "dataset_id": dataset_id,
            "created_at": datetime.utcnow(),
            "result": result_data
        })

        # 5. Update Status -> DONE
        jobs_col.update_one(
            {"_id": job_id},
            {"$set": {
                "status": "done", 
                "finished_at": datetime.utcnow()
            }}
        )
        return "OK"

    except Exception as e:
        # 6. Handle Error -> FAILED
        jobs_col.update_one(
            {"_id": job_id},
            {"$set": {
                "status": "failed", 
                "error": str(e),
                "finished_at": datetime.utcnow()
            }}
        )
        # Re-raise agar tercatat di log Celery
        raise e