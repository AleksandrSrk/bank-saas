from fastapi import Header, HTTPException, status

from app.config.settings import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """
    Minimal protection for public deployments.
    If INTERNAL_API_KEY is set in env, all protected routes require X-API-Key header.
    """
    configured = getattr(settings, "INTERNAL_API_KEY", None)
    if not configured:
        return

    if not x_api_key or x_api_key != configured:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

