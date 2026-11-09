from fastapi import FastAPI

app = FastAPI(title="UniVerse Surveillance API")


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "universe-backend"}
