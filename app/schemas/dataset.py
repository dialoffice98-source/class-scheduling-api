from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class DatasetCreate(BaseModel):
    name: str
    course_dict: Dict[str, Any]
    room_dict: Dict[str, Any]
    faculty_preference_dict: Optional[Dict[str, Any]] = None
    faculty_unavailability_dict: Optional[Dict[str, Any]] = None
    settings: Dict[str, Any]
    quick_scheduling: bool

class DatasetResponse(DatasetCreate):
    id: str
    created_at: datetime