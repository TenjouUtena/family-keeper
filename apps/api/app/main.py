import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Route app loggers through uvicorn's handler so they appear in stdout
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")

from app.config import settings
from app.core.redis import close_redis, get_redis
from app.routers import ai, auth, calendar, families, health, lists, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_redis()
    yield
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(families.router)
app.include_router(lists.router)
app.include_router(ai.router)
app.include_router(calendar.router)
