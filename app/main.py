from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.auth import router as auth_router
from app.api.tasks import router as tasks_router
from app.api.client import router as client_router
from app.api.worker import router as worker_router
from app.api.admin import router as admin_router
from app.api.shifts import router as shifts_router

app = FastAPI(title="SafeStay API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_DIR),
    name="uploads"
)

app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(client_router)
app.include_router(worker_router)
app.include_router(admin_router)
app.include_router(shifts_router)

@app.get("/")
def read_root():
    return {"message": "SafeStay Backend is Running"}
