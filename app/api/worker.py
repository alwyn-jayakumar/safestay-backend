from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task, User
from app.auth import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/worker", tags=["worker"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.get("/tasks/{worker_id}")
async def get_worker_tasks(worker_id: int, db: Session = Depends(get_db)):
    return db.query(Task).filter(Task.worker_id == worker_id).all()

@router.put("/accept-task/{task_id}")
async def accept_task(
    task_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    worker = db.query(User).filter(User.email == email).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.worker_id = worker.id
    task.status = "ACCEPTED"
    db.commit()

    return {"message": "You have successfully accepted this task"}

@router.put("/profile")
async def update_profile(
    location: str = Form(...),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    worker = db.query(User).filter(User.email == email).first()
    if not worker:
        raise HTTPException(status_code=404, detail="User not found")

    worker.location = location
    db.commit()
    return {"message": "Profile updated", "location": worker.location}
