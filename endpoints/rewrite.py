import logging
from fastapi import Request, Header, HTTPException

from common.fastapi_server import api
from common.config import REWRITE_SECRET
from services.gemini import gemini_manager as g

logger = logging.getLogger("rewrite")

@api.post("/webhook/rewrite")
@api.post("/webhook/rewrite/")
async def rewrite_webhook(
    request: Request,
    authorization: str = Header(None)
):
    if authorization != f"Bearer {REWRITE_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    text = body.get("text")
    if not text or not isinstance(text, str):
        raise HTTPException(status_code=400, detail="Missing text")

    rewrite = await g.correct_text(text)
    if not rewrite:
        raise HTTPException(status_code=502, detail="Rewrite failed")

    return {"rewrite": rewrite}