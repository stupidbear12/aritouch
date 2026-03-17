from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import CORS_ORIGINS, DB_PATH
from server.db.database import close_db, init_db
from server.routers import anomaly_router, config_router, dashboard_router, ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(DB_PATH)
    yield
    await close_db()


app = FastAPI(title="AirTouch Server", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router.router)
app.include_router(anomaly_router.router)
app.include_router(dashboard_router.router)
app.include_router(ws_router.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
