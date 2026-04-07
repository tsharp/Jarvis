from unittest.mock import AsyncMock

import pytest

from core.bridge import CoreBridge
from core.models import CoreChatRequest, CoreChatResponse, Message, MessageRole


@pytest.mark.asyncio
async def test_bridge_process_delegates_to_full_orchestrator_pipeline():
    bridge = CoreBridge()
    expected = CoreChatResponse(
        model="test-model",
        content="ok",
        conversation_id="conv-bridge-sync",
        validation_passed=True,
    )
    bridge.orchestrator.process = AsyncMock(return_value=expected)

    request = CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content="starte den gaming container")],
        conversation_id="conv-bridge-sync",
    )

    result = await bridge.process(request)

    assert result is expected
    bridge.orchestrator.process.assert_awaited_once_with(request)
