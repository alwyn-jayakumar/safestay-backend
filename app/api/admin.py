import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/pending-workers")
async def get_pending_workers(db: Session = Depends(get_db)):
    workers = db.query(User).filter(User.role == 'WORKER', User.is_verified == False).all()
    return workers

@router.patch("/verify-worker/{user_id}")
async def verify_worker(user_id: int, db: Session = Depends(get_db)):
    worker = db.query(User).filter(User.id == user_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    worker.is_verified = True
    db.commit()
    return {"message": f"Worker {worker.full_name} verified successfully"}

@router.get("/stats")
async def get_admin_stats(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    pending_workers = db.query(User).filter(User.role == 'WORKER', User.is_verified == False).count()
    active_tasks = 0
    return {
        "total_users": total_users,
        "pending_workers": pending_workers,
        "active_tasks": active_tasks
    }

@router.delete("/reject-worker/{user_id}")
async def reject_worker(user_id: int, db: Session = Depends(get_db)):
    worker = db.query(User).filter(User.id == user_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    if worker.id_proof_path and os.path.exists(worker.id_proof_path):
        os.remove(worker.id_proof_path)
    if worker.profile_pic_path and os.path.exists(worker.profile_pic_path):
        os.remove(worker.profile_pic_path)

    db.delete(worker)
    db.commit()
    return {"message": f"Worker {worker.full_name} and their documents removed successfully"}
