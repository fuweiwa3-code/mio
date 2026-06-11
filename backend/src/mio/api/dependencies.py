from typing import cast

from fastapi import Request

from mio.services.conversations import ConversationService


def get_conversation_service(request: Request) -> ConversationService:
    return cast(ConversationService, request.app.state.conversation_service)
