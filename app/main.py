from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid

# Import your own files
from .database import engine, get_db, Base
from .models import User

# Create the tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SafeStay API")

# VERY IMPORTANT: Allow your React app to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Your Vite port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        with open(id_path, "wb") as buffer:
            buffer.write(await id_file.read())

    # 3. Save User to MSSQL
    # (Note: In a real app, use passlib to hash 'password' before saving!)
    new_user = User(
        full_name=fullName,
        email=email,
        password_hash=password, 
        role=role,
        location=location,
        aadhaar_number=aadhaar,
        id_proof_path=id_path
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Signup successful", "user_id": new_user.id}