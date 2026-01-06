from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from server.core.db import engine, Base, SessionLocal
from server.seed.seed_benchmarks import seed_benchmarks
from server.api import auth, companies, datasets, truth_scan, simulations, decisions, copilot, investor

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        seed_benchmarks(db)
    finally:
        db.close()
    
    yield

app = FastAPI(
    title="Predixen Intelligence OS",
    description="AI-powered financial simulation and decision engine for startups",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(datasets.router)
app.include_router(truth_scan.router)
app.include_router(simulations.router)
app.include_router(decisions.router)
app.include_router(copilot.router)
app.include_router(investor.router)

@app.get("/")
def root():
    return {"message": "Predixen Intelligence OS API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}
