from fastapi import APIRouter, Depends

from app.core.logging import get_logger
from app.services.session_manager import SessionManager


router = APIRouter()
logger = get_logger("api.session")


def get_session_manager() -> SessionManager:
    from app.main import app_state
    if app_state is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Application not ready")
    return app_state.session_manager


@router.post("/session/{session_id}/teardown")
async def teardown_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
):
    await session_manager.drop_session_schema(session_id)
    logger.info("Session torn down", extra={"session_id": session_id})
    return {"status": "ok", "session_id": session_id}
