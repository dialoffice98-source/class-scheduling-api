from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobResponse(BaseModel):
    id: str
    dataset_id: str
    status: str
    created_at: datetime
    finished_at: Optional[datetime]
    error: Optional[str]