import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.api import runners as runners_api
from app.api.alerts import router as alerts_router
from app.api.auth import router as auth_router
from app.api.cameras import router as cameras_router
from app.api.dashboard import router as dashboard_router
from app.api.incidents import router as incidents_router
from app.api.people import embeddings_router
from app.api.people import router as people_router
from app.api.ws import router as ws_router
from app.db.session import SessionLocal
from app.services import retention
from app.services.camera_runner import camera_runner

load_dotenv()
logger = logging.getLogger("universe")

RETENTION_INTERVAL_SECONDS = 6 * 60 * 60


def _run_retention() -> None:
    with SessionLocal() as db:
        retention.purge(db)


async def _retention_loop() -> None:
    """Evidence retention runs at startup and then every few hours."""
    while True:
        try:
            await run_in_threadpool(_run_retention)
        except Exception:
            logger.exception("evidence retention purge failed")
        await asyncio.sleep(RETENTION_INTERVAL_SECONDS)


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    runners_api.event_loop = asyncio.get_running_loop()
    task = asyncio.create_task(_retention_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    # AI scripts started from the dashboard don't outlive the API.
    await run_in_threadpool(camera_runner.stop_all)


app = FastAPI(title="UniVerse Surveillance API", lifespan=lifespan)

# The dashboard is served from a different origin (Vite dev server in development).
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(cameras_router)
app.include_router(runners_api.router)
app.include_router(runners_api.list_router)
app.include_router(people_router)
app.include_router(embeddings_router)
app.include_router(alerts_router)
app.include_router(incidents_router)
app.include_router(dashboard_router)
app.include_router(ws_router)


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "universe-backend"}
