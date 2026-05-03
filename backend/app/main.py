from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, chat, export, requirements, rtm, upload
from app.core.database import enable_pgvector

app = FastAPI(
    title="SpecAgent API",
    description="AI Agent-Based SRS Generation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await enable_pgvector()
    yield

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "NIJE NADZENOU NE POSTOJI"}


app.include_router(auth.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(requirements.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(rtm.router, prefix="/api")
app.include_router(export.router, prefix="/api")