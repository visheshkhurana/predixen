from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from server.core.db import engine, Base, SessionLocal
from server.core.migrations import run_migrations
from server.seed.seed_benchmarks import seed_benchmarks
from server.seed.seed_demo import seed_demo_data
from server.api import auth, companies, datasets, truth_scan, simulations, decisions, copilot, investor, ingest, calibration, scenarios
from server.api import forecasting as forecasting_api, alerts as alerts_api, integrations as integrations_api, templates as templates_api
from server.api import imports as imports_api
from server.api import admin as admin_api
from server.api import workspace as workspace_api, comments as comments_api
from server.api import simulation_jobs as simulation_jobs_api
from server.api import email_templates as email_templates_api
from server.api import data_health as data_health_api
from server.api import workstreams as workstreams_api
from server.api import driver_models as driver_models_api
from server.api import fundraising as fundraising_api
from server.api import dashboard_kpis as dashboard_kpis_api
from server.api import connectors as connectors_api
from server.api import notifications as notifications_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Run migrations to add any new columns to existing tables
        run_migrations(engine)
        
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
app.include_router(admin_api.router)
app.include_router(workspace_api.router)
app.include_router(comments_api.router)
app.include_router(simulation_jobs_api.router)
app.include_router(email_templates_api.router)
app.include_router(scenarios.router)
app.include_router(data_health_api.router)
app.include_router(workstreams_api.router)
app.include_router(driver_models_api.router)
app.include_router(fundraising_api.router)
app.include_router(dashboard_kpis_api.router)
app.include_router(connectors_api.router)
app.include_router(notifications_api.router)

@app.get("/")
def root():
    return {"message": "Predixen Intelligence OS API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}
