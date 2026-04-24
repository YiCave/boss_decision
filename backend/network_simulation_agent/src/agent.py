from __future__ import annotations

import asyncio
from typing import Any
from typing import AsyncIterator

from .engine import NetworkSimulationEngine
from .schema import NetworkSimulatorRequest


def invoke(initial_state: dict[str, Any], session_id: str | None = None) -> dict[str, Any]:
    """Run a simulation synchronously and return the final aggregated result payload.

    Args:
        initial_state: Raw request payload that must match `NetworkSimulatorRequest`.
        session_id: Optional externally supplied session id for deterministic run grouping.

    Returns:
        Final simulation result dictionary containing at least `session_id`.
    """
    request = NetworkSimulatorRequest.model_validate(initial_state)
    engine = NetworkSimulationEngine(request=request, session_id=session_id)
    return asyncio.run(engine.run_to_completion())


async def astream(initial_state: dict[str, Any], session_id: str | None = None) -> AsyncIterator[dict[str, Any]]:
    """Stream simulation events asynchronously from start to completion.

    Args:
        initial_state: Raw request payload validated as `NetworkSimulatorRequest`.
        session_id: Optional externally supplied session id for the stream run.

    Yields:
        Event dictionaries in chronological order for UI/API consumption.
    """
    request = NetworkSimulatorRequest.model_validate(initial_state)
    engine = NetworkSimulationEngine(request=request, session_id=session_id)
    async for event in engine.run_stream():
        yield event
