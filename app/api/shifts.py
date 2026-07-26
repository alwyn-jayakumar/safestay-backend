from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session
from datetime import datetime
import os
import uuid

from app.database import get_db
from app.models import Shift, Task, User, ActivityLog, StatusUpdate
from app.auth import SECRET_KEY, ALGORITHM
from app.schemas import ShiftStart, ShiftEnd, ActivityLogCreate, ShiftResponse, ActivityLogResponse, StatusUpdateResponse

router = APIRouter(prefix="/shifts", tags=["shifts"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/start", response_model=ShiftResponse)
async def start_shift(
    shift_data: ShiftStart,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Start a new shift after QR verification"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    worker = db.query(User).filter(User.email == email).first()
    
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Verify task exists and matches worker
    task = db.query(Task).filter(Task.id == shift_data.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if there's already an active shift for this task
    existing_shift = db.query(Shift).filter(
        Shift.task_id == shift_data.task_id,
        Shift.status == "ACTIVE"
    ).first()
    
    if existing_shift:
        raise HTTPException(status_code=400, detail="An active shift already exists for this task")
    
    # Create new shift
    new_shift = Shift(
        task_id=shift_data.task_id,
        worker_id=shift_data.worker_id,
        client_id=shift_data.client_id,
        status="ACTIVE",
        start_coords_lat=shift_data.start_coords.get("lat"),
        start_coords_lng=shift_data.start_coords.get("lng"),
        qr_verified=shift_data.qr_verified,
        location_verified=shift_data.location_verified
    )
    
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    
    return new_shift


@router.post("/end", response_model=ShiftResponse)
async def end_shift(
    shift_data: ShiftEnd,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """End an active shift"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    worker = db.query(User).filter(User.email == email).first()
    
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    shift = db.query(Shift).filter(Shift.id == shift_data.shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    if shift.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Shift is not active")
    
    # Update shift
    shift.status = "COMPLETED"
    shift.end_time = datetime.utcnow()
    if shift_data.end_coords:
        shift.end_coords_lat = shift_data.end_coords.get("lat")
        shift.end_coords_lng = shift_data.end_coords.get("lng")
    
    # Mark task as completed
    task = db.query(Task).filter(Task.id == shift.task_id).first()
    if task:
        task.status = "COMPLETED"
    
    db.commit()
    db.refresh(shift)
    
    return shift


@router.get("/active/{task_id}", response_model=ShiftResponse)
async def get_active_shift(
    task_id: int,
    db: Session = Depends(get_db)
):
    """Get active shift for a task"""
    shift = db.query(Shift).filter(
        Shift.task_id == task_id,
        Shift.status == "ACTIVE"
    ).first()
    
    if not shift:
        raise HTTPException(status_code=404, detail="No active shift found")
    
    return shift


@router.get("/{shift_id}", response_model=ShiftResponse)
async def get_shift(
    shift_id: int,
    db: Session = Depends(get_db)
):
    """Get shift details"""
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    return shift


@router.post("/activity/log", response_model=ActivityLogResponse)
async def log_activity(
    activity: ActivityLogCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Log a care activity during shift"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify shift exists and is active
    shift = db.query(Shift).filter(Shift.id == activity.shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    if shift.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Shift is not active")
    
    # Create activity log
    new_log = ActivityLog(
        shift_id=activity.shift_id,
        type=activity.type,
        description=activity.description,
        timestamp=activity.timestamp
    )
    
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    return new_log


@router.get("/{shift_id}/logs", response_model=list[ActivityLogResponse])
async def get_activity_logs(
    shift_id: int,
    db: Session = Depends(get_db)
):
    """Get all activity logs for a shift"""
    logs = db.query(ActivityLog).filter(ActivityLog.shift_id == shift_id).all()
    return logs


@router.post("/{shift_id}/status-update", response_model=StatusUpdateResponse)
async def upload_status_update(
    shift_id: int,
    file: UploadFile = File(...),
    notes: str = Form(None),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Upload a caretaker status image during shift"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify shift exists and is active
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    if shift.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Shift is not active")
    
    # Save uploaded file
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"status_{shift_id}_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Create status update record
    status_update = StatusUpdate(
        shift_id=shift_id,
        image_path=f"/uploads/{unique_filename}",
        notes=notes
    )
    
    db.add(status_update)
    db.commit()
    db.refresh(status_update)
    
    return status_update


@router.get("/{shift_id}/status-updates", response_model=list[StatusUpdateResponse])
async def get_status_updates(
    shift_id: int,
    db: Session = Depends(get_db)
):
    """Get all status update images for a shift"""
    updates = db.query(StatusUpdate).filter(StatusUpdate.shift_id == shift_id).all()
    return updates
