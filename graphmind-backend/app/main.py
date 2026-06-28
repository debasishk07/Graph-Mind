from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import auth, repositories

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title="GraphMind API",
    description="AI-Powered Code Dependency & Architecture Visualizer",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(repositories.router, prefix="/api/v1/repositories", tags=["Repositories"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "graphmind-api"}


@app.get("/")
async def root():
    return {
        "name": "GraphMind API",
        "version": "0.1.0",
        "description": "AI-Powered Code Dependency & Architecture Visualizer",
        "docs": "/docs",
    }