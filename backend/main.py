import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router
from routes.documents import router as documents_router
from routes.live import router as live_router
from routes.channels import router as channels_router

import uvicorn

from settings import get_settings
from observability import configure_logging, install_request_logging
# import database
settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "application_started",
        extra={
            "google_api_key_configured": bool(settings.google_api_key),
            "gemini_live_model": settings.gemini_live_model,
            "log_level": settings.log_level.upper(),
        },
    )
    yield


app = FastAPI(lifespan=lifespan)
install_request_logging(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(live_router)
app.include_router(channels_router)

@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
