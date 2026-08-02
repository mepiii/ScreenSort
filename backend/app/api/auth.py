"""Purpose: optional API key authorization. Callers: API route dependencies. Deps: hmac, FastAPI Request/Header/HTTPException. API: require_api_key. Side effects: rejects unauthorized requests when configured."""
import hmac

from fastapi import Header, HTTPException, Query, Request


async def require_api_key(request: Request, x_api_key: str | None = Header(default=None), api_key: str | None = Query(default=None)) -> None:
    expected = request.app.state.settings.api_key
    if expected is None:
        return
    provided = x_api_key or api_key
    if provided is not None and hmac.compare_digest(provided, expected):
        return
    raise HTTPException(status_code=401, detail="Invalid API key")
