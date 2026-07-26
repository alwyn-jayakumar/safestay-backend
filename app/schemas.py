from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class LoginRequest(BaseModel):
    email: str
    password: str

class TaskCreate(BaseModel):
    title: str
    description: str
    location: str

class ShiftStart(BaseModel):
    task_id: int
    worker_id: int
    client_id: int
    qr_verified: bool
    location_verified: bool
    start_coords: dict  # { lat: number, lng: number }

class ShiftEnd(BaseModel):
    shift_id: int
    end_coords: Optional[dict] = None  # { lat: number, lng: number }

class ActivityLogCreate(BaseModel):
    shift_id: int
    type: str  # MEDICINE, FOOD, ACTIVITY
    description: str
    timestamp: datetime

class ActivityLogResponse(BaseModel):
    id: int
    shift_id: int
    type: str
    description: str
    timestamp: datetime

    class Config:
        from_attributes = True

class ShiftResponse(BaseModel):
    id: int
    task_id: int
    worker_id: int
    client_id: int
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    qr_verified: bool
    location_verified: bool

    class Config:
        from_attributes = True

class StatusUpdateResponse(BaseModel):
    id: int
    shift_id: int
    image_path: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
