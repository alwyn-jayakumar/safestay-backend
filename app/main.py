from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid

# Import your own files
from .database import engine, get_db, Base
from .models import User, Task
from .auth import hash_password, verify_password, create_access_token
from pydantic import BaseModel

from .auth import ALGORITHM, SECRET_KEY
from jose import jwt
from fastapi.security import OAuth2PasswordBearer

# Create the tables if they don't exist

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app = FastAPI(title="SafeStay API")

# VERY IMPORTANT: Allow your React app to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Your Vite port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/uploads",
    StaticFiles(directory=r"D:\New folder\New folder\New folder\New folder\New folder\safestay-backend\uploads"),
    name="uploads"
)

@app.get("/")
def read_root():
    return {"message": "SafeStay Backend is Running"}

@app.post("/auth/signup")
async def signup(
    fullName: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    location: Optional[str] = Form(None),
    aadhaar: Optional[str] = Form(None),
    id_file: Optional[UploadFile] = File(None),
    profile_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    
    # 1. Check if user already exists
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Handle File Upload (Save Aadhaar to 'uploads' folder)
    id_path = None
    if id_file:
        file_ext = id_file.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_ext}"
        id_path = os.path.join("uploads", file_name)
        id_path = id_path.replace("\\", "/")
        with open(id_path, "wb") as buffer:
            buffer.write(await id_file.read())

    profile_path = None
    if profile_file:
        profile_path = os.path.join('uploads', f"profile_{email}_{profile_file.filename}")
        profile_path = profile_path.replace("\\", "/") 
        with open(profile_path, "wb") as buffer:
            buffer.write(await profile_file.read())

    # 3. Save User to MSSQL
    # (Note: In a real app, use passlib to hash 'password' before saving!)
    new_user = User(
        full_name=fullName,
        email=email,
        password_hash=hash_password(password),
        role=role,
        location=location,
        aadhaar_number=aadhaar,
        id_proof_path=id_path,
        profile_pic_path=profile_path
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Signup successful", "user_id": new_user.id}

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/login")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    # 1. Find User
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid Email or Password")

    # 2. Check Password
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid Email or Password")

    # 3. Create Token
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "id": user.id}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.full_name,
            "role": user.role
        }
    }

# Add this endpoint to your main.py
# 1. Client creates a request
class TaskCreate(BaseModel):
    title: str
    description: str
    location: str

@app.post("/tasks/create")
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
    

@app.get("/client/my-tasks")
async def get_client_tasks(
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
):
    # 1. Identify the user from the token
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email: str = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 2. Fetch tasks created by this specific client
    # We order by created_at desc so the newest request appears at the top
    tasks = db.query(Task).filter(Task.client_id == user.id).order_by(Task.created_at.desc()).all()
    
    return tasks


# 2. Worker sees available tasks in their area
@app.get("/tasks/available")
async def get_available_tasks(db: Session = Depends(get_db)):
    return db.query(Task).filter(Task.status == "PENDING").all()

@app.get("/worker/tasks")
async def get_worker_tasks(worker_id: int, db: Session = Depends(get_db)):
    # In a real app, you'd get 'worker_id' from the JWT token
    tasks = db.query(Task).filter(Task.worker_id == worker_id).all()
    return tasks

# @app.put("/worker/update-task/{task_id}")
# async def update_task_status(
#     task_id: int, 
#     status: str, # Send "COMPLETED" or "ACCEPTED"
#     db: Session = Depends(get_db)
# ):
#     task = db.query(Task).filter(Task.id == task_id).first()
#     if not task:
#         raise HTTPException(status_code=404, detail="Task not found")
    
#     task.status = status # Using the 'status' column we defined in the Task model
#     db.commit()
#     return {"status": "success", "message": f"Task updated to {status}"}

@app.put("/worker/accept-task/{task_id}")
async def accept_task(
    task_id: int, 
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
):
    # 1. Get current worker from token
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    worker = db.query(User).filter(User.email == email).first()

    # 2. Find the task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 3. Update Task with Worker's ID and change status
    task.worker_id = worker.id
    task.status = "ACCEPTED"
    
    db.commit()
    return {"message": "You have successfully accepted this task"}


@app.get("/auth/me")
async def get_current_user(
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
):
    try:
        # 1. Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        # 2. Fetch the user from MSSQL
        user = db.query(User).filter(User.email == email).first()
        
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
            
        return {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_verified": user.is_verified
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    

    # 1. Get all workers who are NOT verified yet
@app.get("/admin/pending-workers")
async def get_pending_workers(db: Session = Depends(get_db)):
    # We only want users with role 'WORKER' who are not verified
    workers = db.query(User).filter(User.role == 'WORKER', User.is_verified == False).all()
    print(workers,'checke')
    return workers

# 2. Approve a worker
@app.patch("/admin/verify-worker/{user_id}")
async def verify_worker(user_id: int, db: Session = Depends(get_db)):
    worker = db.query(User).filter(User.id == user_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    worker.is_verified = True
    db.commit()
    return {"message": f"Worker {worker.full_name} verified successfully"}

@app.get("/admin/stats")
async def get_admin_stats(db: Session = Depends(get_db)):
    # Count from MSSQL
    total_users = db.query(User).count()
    pending_workers = db.query(User).filter(User.role == 'WORKER', User.is_verified == False).count()
    
    # Placeholder for tasks (we will build tasks next)
    active_tasks = 0 
    
    return {
        "total_users": total_users,
        "pending_workers": pending_workers,
        "active_tasks": active_tasks
    }


# app/main.py

@app.put("/worker/profile")
async def update_profile(
    location: str = Form(...),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    # Get current user from token
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    
    worker = db.query(User).filter(User.email == email).first()
    if not worker:
        raise HTTPException(status_code=404, detail="User not found")
        
    worker.location = location
    db.commit()
    
    return {"message": "Profile updated", "location": worker.location}

# app/main.py

@app.delete("/admin/reject-worker/{user_id}")
async def reject_worker(user_id: int, db: Session = Depends(get_db)):
    # 1. Find the worker in the database
    worker = db.query(User).filter(User.id == user_id).first()
    
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # 2. Get the file path from the database record
    # Assuming 'id_proof_path' is stored as 'uploads/filename.jpg'
    file_path = worker.id_proof_path 

    # 3. Delete the file from the physical folder if it exists
    if file_path:
        try:
            # Check if the file exists on the disk before trying to remove it
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"DEBUG: Successfully deleted file {file_path}")
            else:
                print(f"DEBUG: File {file_path} not found on disk, skipping file deletion.")
        except Exception as e:
            # We log the error but continue deleting the DB record 
            # so the system doesn't get stuck due to a missing file
            print(f"ERROR deleting file: {e}")

    if worker.profile_pic_path:
        try:
            if os.path.exists(worker.profile_pic_path):
                os.remove(worker.profile_pic_path)
                print(f"DEBUG: Deleted profile picture {worker.profile_pic_path}")
            else:
                print(f"DEBUG: Profile picture {worker.profile_pic_path} not found on disk")
        except Exception as e:
            print(f"ERROR deleting profile picture: {e}")

    # 4. Delete the worker from the database
    try:
        db.delete(worker)
        db.commit()
        return {"message": f"Worker {worker.full_name} and their documents removed successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database deletion failed")