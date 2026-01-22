from app.db.mongo_async import jobs_col, datasets_col, results_col

async def create_indexes():
    # JOBS
    await jobs_col.create_index("dataset_id")
    await jobs_col.create_index("status")
    await jobs_col.create_index("created_at")

    # DATASETS
    await datasets_col.create_index("created_at")

    # RESULTS
    await results_col.create_index("job_id", unique=True)