from fastapi import APIRouter, HTTPException
from app.schemas.result import ResultResponse
from app.db.results import get_result

router = APIRouter(prefix="/results", tags=["Results"])

@router.get("/{job_id}", response_model=ResultResponse)
async def get_result_by_job(job_id: str):
    result = await get_result(job_id=job_id)

    if not result:
        raise HTTPException(404, "Result not found")

    return {
        "job_id": result["job_id"], # Di DB _id nya string job_id
        "dataset_id": result["dataset_id"],
        "created_at": result["created_at"],
        "result": result["result"]
    }

@router.get("/dataset/{dataset_id}", response_model=ResultResponse)
async def get_result_by_dataset(dataset_id: str):
    result = await get_result(dataset_id=dataset_id)

    if not result:
        raise HTTPException(404, "Result not found")

    return {
        "job_id": result["job_id"], # Di DB _id nya string job_id
        "dataset_id": result["dataset_id"],
        "created_at": result["created_at"],
        "result": result["result"]
    }