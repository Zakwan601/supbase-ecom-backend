import os

from fastapi import Header, HTTPException, status


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    api_key = os.getenv("API_KEY", "").strip()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "error": "API_KEY is not configured"},
        )

    expected = f"Bearer {api_key}"
    if not authorization or authorization.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error": "Invalid API key"},
        )
