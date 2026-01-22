from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import datasets, jobs, results, scheduler 
from app.db.indexes import create_indexes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    # Pastikan index dibuat saat aplikasi nyala
    await create_indexes()
    yield
    # SHUTDOWN
    # Motor handle close connection otomatis, tapi bisa ditambahkan jika perlu

app = FastAPI(
    title="Class Scheduling API",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(datasets.router)
app.include_router(scheduler.router)
app.include_router(jobs.router)
app.include_router(results.router)