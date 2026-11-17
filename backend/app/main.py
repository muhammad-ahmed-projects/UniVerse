import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router

logger = logging.getLogger("universe")

app = FastAPI(title="UniVerse Surveillance API")
app.include_router(auth_router)


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "universe-backend"}
