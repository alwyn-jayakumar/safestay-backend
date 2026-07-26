from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task, User
from app.auth import SECRET_KEY, ALGORITHM
from app.schemas import TaskCreate

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(tags=["tasks"])

@router.post("/tasks/create")
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email: str = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_task = Task(
        title=task.title,
        description=task.description,
        location=task.location,
        client_id=user.id,
        status="PENDING"
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return {"message": "Task created successfully", "task_id": new_task.id}

@router.get("/tasks/available")
async def get_available_tasks(db: Session = Depends(get_db)):
    return db.query(Task).filter(Task.status == "PENDING").all()
