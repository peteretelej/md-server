from fastapi import FastAPI

app = FastAPI(title="md-server", version="0.0.1")


@app.get("/healthz")
async def health_check():
    return {"status": "ok"}