from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid

from app.database import get_db
from app.models import User
from app.auth import hash_password, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from app.schemas import LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.post("/signup")
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
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

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
        profile_path = os.path.join("uploads", f"profile_{email}_{profile_file.filename}")
        profile_path = profile_path.replace("\\", "/")
        with open(profile_path, "wb") as buffer:
            buffer.write(await profile_file.read())

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

@router.post("/login")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid Email or Password")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid Email or Password")

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

@router.get("/me")
async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.email == email).first()
        if not user:
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
