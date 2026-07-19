from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_chat_history_service
from app.core.logging import get_logger
from app.schemas.ask import AnswerResponse
from app.schemas.chat_history import (
    ChatSessionHistoryResponse,
    ChatSessionResponse,
    ChatSessionSummaryResponse,
    CreateChatSessionRequest,
    StoredTurnResponse,
)
from app.services.chat_history_service import ChatHistoryService
from app.services.session_manager import SessionManager

router = APIRouter()
logger = get_logger("api.session")


def get_session_manager() -> SessionManager:
    from app.main import app_state
    if app_state is None:
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


@router.post("/session/chat", status_code=201)
async def create_chat_session(
    body: CreateChatSessionRequest,
    service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatSessionResponse:
    session = await service.start_session(
        account_username=body.account_username,
        upload_session_id=body.upload_session_id,
    )
    return ChatSessionResponse(
        chat_session_id=session.id,
        account_username=session.account_username,
        upload_session_id=session.upload_session_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/session/chat/{chat_session_id}")
async def get_chat_session_history(
    chat_session_id: str,
    service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatSessionHistoryResponse:
    result = await service.get_history(chat_session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    session, turns = result
    return ChatSessionHistoryResponse(
        session=ChatSessionResponse(
            chat_session_id=session.id,
            account_username=session.account_username,
            upload_session_id=session.upload_session_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
        ),
        turns=[
            StoredTurnResponse(
                turn_index=t.turn_index,
                question=t.question_text,
                answer=AnswerResponse.model_validate(t.answer_json),
                created_at=t.created_at,
            )
            for t in turns
        ],
    )


@router.get("/session/chat")
async def list_chat_sessions(
    account_username: str | None = None,
    service: ChatHistoryService = Depends(get_chat_history_service),
) -> list[ChatSessionSummaryResponse]:
    items = await service.list_session_summaries(account_username)
    return [
        ChatSessionSummaryResponse(
            chat_session_id=session.id,
            account_username=session.account_username,
            created_at=session.created_at,
            updated_at=session.updated_at,
            turn_count=turn_count,
            preview_question=preview_question,
        )
        for session, turn_count, preview_question in items
    ]
