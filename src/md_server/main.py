from fastapi import FastAPI
from .api.routes.health import router as health_router
from .api.routes.convert import router as convert_router

app = FastAPI(title="md-server", version="0.0.1")

app.include_router(health_router)
app.include_router(convert_router)
