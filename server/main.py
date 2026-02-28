import sys
import time
import logging

_t0 = time.time()
print(f"[main.py] Module load start", file=sys.stderr, flush=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

print(f"[main.py] Importing FastAPI... (+{time.time()-_t0:.1f}s)", file=sys.stderr, flush=True)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
print(f"[main.py] FastAPI imported (+{time.time()-_t0:.1f}s)", file=sys.stderr, flush=True)

print(f"[main.py] Importing config... (+{time.time()-_t0:.1f}s)", file=sys.stderr, flush=True)
from server.core.config import settings
print(f"[main.py] Importing db... (+{time.time()-_t0:.1f}s)", file=sys.stderr, flush=True)
from server.core.db import engine, Base, SessionLocal
print(f"[main.py] Core imports done (+{time.time()-_t0:.1f}s)", file=sys.stderr, flush=True)

_startup_state = {"ready": False, "error": None, "routers_loaded": False}


def _register_critical_routers(app: FastAPI):
    t0 = time.time()
    logger.info("Loading critical API modules (auth, companies, health)...")

    from server.api import auth, companies, admin as admin_api
    from server.api import qa as qa_api
    from server.api import billing as billing_api
    from server.api import onboarding as onboarding_api
    from server.api import oauth as oauth_api

    app.include_router(auth.router)
    app.include_router(oauth_api.router)
    app.include_router(companies.router)
    app.include_router(admin_api.router)
    app.include_router(qa_api.router)
    app.include_router(billing_api.router)
    app.include_router(onboarding_api.router)

    logger.info(f"Critical routes registered in {time.time() - t0:.1f}s")


def _register_remaining_routers(app: FastAPI):
    t0 = time.time()
    logger.info("Loading remaining API modules in background...")

    from server.api import datasets, truth_scan, simulations, decisions, copilot, investor, ingest, calibration, scenarios
    from server.api import forecasting as forecasting_api, alerts as alerts_api, integrations as integrations_api, templates as templates_api
    from server.api import imports as imports_api
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
    from server.api import assumptions as assumptions_api
    from server.api import advanced_simulation as advanced_simulation_api
    from server.api import conversations as conversations_api
    from server.api import llm as llm_api
    from server.api import simulation_copilot as simulation_copilot_api
    from server.api import canonical_state as canonical_state_api
    from server.api import realtime as realtime_api
    from server.api import export as export_api
    from server.api import company_lookup as company_lookup_api
    from server.api import benchmark_search as benchmark_search_api
    from server.api import connector_catalog as connector_catalog_api
    from server.api import dashboards as dashboards_api
    from server.api import metrics as metrics_api
    from server.api import suggestions as suggestions_api
    from server.api import email_tracking as email_tracking_api
    from server.api import shared_scenarios as shared_scenarios_api
    from server.api import metric_trends as metric_trends_api
    from server.api import digest as digest_api
    from server.api import csv_import as csv_import_api
    from server.api import currency as currency_api
    from server.api import leads as leads_api
    from server.api import events as events_api
    from server.api import cap_table as cap_table_api

    logger.info(f"Remaining API modules imported in {time.time() - t0:.1f}s")

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
    app.include_router(assumptions_api.router)
    app.include_router(advanced_simulation_api.router)
    app.include_router(conversations_api.router)
    app.include_router(llm_api.router)
    app.include_router(simulation_copilot_api.router)
    app.include_router(canonical_state_api.router)
    app.include_router(realtime_api.router)
    app.include_router(export_api.router)
    app.include_router(company_lookup_api.router)
    app.include_router(benchmark_search_api.router)
    app.include_router(connector_catalog_api.router)
    app.include_router(dashboards_api.router)
    app.include_router(metrics_api.router)
    app.include_router(suggestions_api.router)
    app.include_router(email_tracking_api.router)
    app.include_router(shared_scenarios_api.router)
    app.include_router(metric_trends_api.router)
    app.include_router(digest_api.router)
    app.include_router(csv_import_api.router)
    app.include_router(currency_api.router)
    app.include_router(leads_api.router)
    app.include_router(events_api.router)
    app.include_router(cap_table_api.router)

    _startup_state["routers_loaded"] = True
    logger.info(f"All {len(app.routes)} routes registered in {time.time() - t0:.1f}s")


async def _run_deferred_startup():
    import asyncio
    await asyncio.sleep(0.1)

    try:
        if settings.should_create_schema:
            logger.info("Creating database tables...")
            import server.models.cap_table  # noqa: F401 - ensure cap table models registered
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
        else:
            logger.info("Skipping schema creation (CREATE_SCHEMA=false)")

        if settings.should_run_migrations:
            logger.info("Running migrations...")
            from server.core.migrations import run_migrations
            run_migrations(engine)
            logger.info("Migrations completed")
        else:
            logger.info("Skipping migrations (RUN_MIGRATIONS=false)")

        db = SessionLocal()
        try:
            if settings.should_seed_benchmarks:
                logger.info("Seeding benchmark data...")
                from server.seed.seed_benchmarks import seed_benchmarks
                seed_benchmarks(db)
                logger.info("Benchmark data seeded")
            else:
                logger.info("Skipping benchmark seeding (SEED_BENCHMARKS=false)")

            if settings.should_seed_demo_data:
                logger.info("Seeding demo data...")
                from server.seed.seed_demo import seed_demo_data
                seed_demo_data(db)
                logger.info("Demo data seeded")
            else:
                logger.info("Skipping demo data seeding (SEED_DEMO_DATA=false)")
        except Exception as e:
            logger.error(f"Error during seeding: {e}")
        finally:
            db.close()

        _startup_state["ready"] = True
        logger.info("Deferred startup tasks completed successfully")

        if settings.ENVIRONMENT == "production":
            try:
                from server.services.notifications import check_and_send_publish_notification
                logger.info("Checking for publish notification...")
                await check_and_send_publish_notification()
            except Exception as e:
                logger.warning(f"Could not send publish notification: {e}")

    except Exception as e:
        _startup_state["error"] = str(e)
        logger.error(f"Error during deferred startup: {e}")
        if settings.is_production:
            logger.critical("FATAL: Deferred startup failed in production - schema/migrations may be incomplete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    import threading
    logger.info(f"Starting FounderConsole v1.0.0")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    if settings.cors_origins_list:
        logger.info(f"CORS origins: {settings.cors_origins_list}")
    else:
        logger.warning("CORS origins list is empty! No cross-origin requests will be allowed.")
    logger.info(f"Config flags - CREATE_SCHEMA: {settings.should_create_schema}, RUN_MIGRATIONS: {settings.should_run_migrations}, SEED_BENCHMARKS: {settings.should_seed_benchmarks}, SEED_DEMO_DATA: {settings.should_seed_demo_data}")

    _register_critical_routers(app)

    def _load_remaining():
        try:
            _register_remaining_routers(app)
            logger.info("Background module loading complete — all routes available")
        except Exception as e:
            logger.error(f"Error loading remaining routers: {e}")
            _startup_state["error"] = str(e)

    bg_thread = threading.Thread(target=_load_remaining, daemon=True, name="router-loader")
    bg_thread.start()

    logger.info("Startup complete - auth routes ready, remaining modules loading in background")
    asyncio.create_task(_run_deferred_startup())
    yield
    logger.info("Shutting down FastAPI server...")


print(f"[main.py] Creating FastAPI app (+{time.time()-_t0:.1f}s)", file=sys.stderr, flush=True)

app = FastAPI(
    title="FounderConsole",
    description="AI-powered financial simulation and decision engine for startups",
    version="1.0.0",
    lifespan=lifespan
)

print(f"[main.py] Adding middleware... (+{time.time()-_t0:.1f}s)", file=sys.stderr, flush=True)
from server.middleware.rate_limiter import RateLimiterMiddleware
from server.middleware.csrf_protection import CSRFProtectionMiddleware

app.add_middleware(CSRFProtectionMiddleware, exempt_paths=[
    "/health",
    "/auth/register",
    "/auth/login",
    "/auth/admin/login",
    "/companies/*/seed-sample",
])

app.add_middleware(
    RateLimiterMiddleware,
    rate_limit_auth=settings.RATE_LIMIT_AUTH,
    rate_limit_admin_login=settings.RATE_LIMIT_ADMIN_LOGIN,
    rate_limit_api=settings.RATE_LIMIT_API,
    rate_limit_upload=settings.RATE_LIMIT_UPLOAD,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With", "X-CSRF-Token"],
)

@app.get("/")
def root():
    return {"message": "FounderConsole API", "version": "1.0.0"}

@app.get("/demo/metrics")
def demo_metrics():
    return {
        "company": "SampleCo (Demo)",
        "metrics": {
            "mrr": 15000, "mrr_growth": 0.08,
            "arr": 180000,
            "burn_rate": 45000,
            "runway_months": 14,
            "cac": 850, "ltv": 12000,
            "ltv_cac_ratio": 14.1,
            "gross_margin": 0.82,
            "net_revenue_retention": 1.15,
            "customers": 45, "churn_rate": 0.03
        },
        "is_demo": True,
        "message": "Sign up to see your real metrics"
    }

@app.get("/health")
def health():
    db_healthy = False
    try:
        db = SessionLocal()
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        db_healthy = True
        db.close()
    except Exception as e:
        logger.warning(f"Health check DB probe failed: {e}")

    overall_status = "healthy" if db_healthy and _startup_state["ready"] else "degraded"
    return {
        "status": overall_status,
        "ready": _startup_state["ready"],
        "routers_loaded": _startup_state["routers_loaded"],
        "database": "connected" if db_healthy else "unavailable",
        "startup_error": _startup_state["error"],
    }

print(f"[main.py] Module load complete (+{time.time()-_t0:.1f}s)", file=sys.stderr, flush=True)
