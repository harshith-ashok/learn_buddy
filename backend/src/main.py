from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.chat import router as chat_router
from src.api.documents import router as documents_router
from src.api.feynman import router as feynman_router
from src.api.graph import router as graph_router
from src.api.health import router as health_router
from src.api.progress import router as progress_router
from src.api.quiz import router as quiz_router
from src.api.recommendation import router as recommendation_router
from src.api.study_kit import router as study_kit_router
from src.api.worked_answer import router as worked_answer_router
from src.core.config import get_settings
from src.core.errors import register_error_handlers
from src.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Learn Buddy API")

    settings = get_settings()
    if settings.jwt_secret == "change-me":
        # Every token this process ever issues is only as safe as this
        # secret — a deployment that never overrode the placeholder
        # default (core/config.py) is signing tokens anyone could forge
        # given the (public, in this repo) default value.
        logger.warning(
            "JWT_SECRET is still the placeholder default — every issued token is forgeable. "
            "Set a real secret via the JWT_SECRET env var before this is reachable outside dev."
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(graph_router)
    app.include_router(progress_router)
    app.include_router(recommendation_router)
    app.include_router(study_kit_router)
    app.include_router(quiz_router)
    app.include_router(chat_router)
    app.include_router(feynman_router)
    app.include_router(worked_answer_router)

    return app


app = create_app()
