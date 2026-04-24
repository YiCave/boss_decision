from __future__ import annotations

import asyncio
from typing import Any
from typing import AsyncIterator

from .engine import DeepSimulationEngine
from .schema import DeepSimulationRequest


def invoke(initial_state: dict[str, Any]) -> dict[str, Any]:
    request = DeepSimulationRequest.model_validate(initial_state)
    engine = DeepSimulationEngine(request)
    return asyncio.run(engine.run_to_completion())


async def astream(initial_state: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    request = DeepSimulationRequest.model_validate(initial_state)
    engine = DeepSimulationEngine(request)
    async for event in engine.run_stream():
        yield event
