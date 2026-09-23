from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check used by the Docker healthcheck and load balancers."""
    return {"status": "ok"}
