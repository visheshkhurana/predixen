from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from server.core.db import engine, Base, SessionLocal
from server.seed.seed_benchmarks import seed_benchmarks
from server.seed.seed_demo import seed_demo_data
from server.api import auth, companies, datasets, truth_scan, simulations, decisions, copilot, investor, ingest, calibration
from server.api import forecasting as forecasting_api, alerts as alerts_api, integrations as integrations_api, templates as templates_api
from server.api import imports as imports_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        db = SessionLocal()
        try:
            logger.info("Running seed scripts...")
            seed_benchmarks(db)
            seed_demo_data(db)
            logger.info("Seed scripts completed successfully")
        except Exception as e:
            logger.error(f"Error during seeding: {e}")
            raise
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
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
app.include_router(ingest.router)
app.include_router(calibration.router)
app.include_router(forecasting_api.router)
app.include_router(alerts_api.router)
app.include_router(integrations_api.router)
app.include_router(templates_api.router)
app.include_router(imports_api.router)

@app.get("/")
def root():
    return {"message": "Predixen Intelligence OS API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}
