from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_tables
from app.routers import auth, memories, conversations

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if they don't exist
    await create_tables()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(memories.router, prefix="/memories", tags=["Memories"])
app.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])


@app.get("/")
async def root():
    return {"message": "Friday AI Assistant API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
