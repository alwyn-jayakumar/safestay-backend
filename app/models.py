from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .database import engine, Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, Float



class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100))
    email = Column(String(100), unique=True)
    password_hash = Column(String(255))
    role = Column(String(20))
    location = Column(String(100), nullable=True)
    aadhaar_number = Column(String(12), nullable=True)
    id_proof_path = Column(String(255), nullable=True)
    profile_pic_path = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=False)
    status = Column(String(50), default="PENDING")  # PENDING, ACCEPTED, COMPLETED
    qr_token = Column(String(255), nullable=True)
    
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    status = Column(String(20), default="ACTIVE")  # ACTIVE, COMPLETED
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    start_coords_lat = Column(Float, nullable=True)
    start_coords_lng = Column(Float, nullable=True)
    end_coords_lat = Column(Float, nullable=True)
    end_coords_lng = Column(Float, nullable=True)
    
    qr_verified = Column(Boolean, default=False)
    location_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    type = Column(String(50))  # MEDICINE, FOOD, ACTIVITY
    description = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class StatusUpdate(Base):
    __tablename__ = "status_updates"

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    image_path = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


Base.metadata.create_all(bind=engine)

