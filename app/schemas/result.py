from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

class ResultResponse(BaseModel):
    job_id: str
    dataset_id: str
    created_at: datetime
    result: Dict[str, Any]