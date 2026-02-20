from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import models BEFORE creating tables to ensure they are registered with Base
from app.models.user import User
from app.models.task import Task
from app.api import auth, tasks
from app.db.base import Base
from app.db.session import engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="WMS API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])


@app.get("/")
def root():
    return {"message": "WMS API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
