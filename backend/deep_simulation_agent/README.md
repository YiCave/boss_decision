# Deep Simulation Agent Backend

Deep simulation backend for deterministic, tick-based 2D market runs.

## Architecture Modules

- `src/schema.py`: world, persona, intent, timeline, observer contracts.
- `src/engine.py`: deterministic tick engine (`1 tick = 1 day`), world updates, KPI updates.
- `src/orchestrator.py`: dynamic persona generation, Deep Agents persona execution, tool streaming.
- `src/rules.py`: action parsing, validation, weighted-hybrid conflict resolution.
- `src/observer.py`: periodic summaries + final observer report with HTML slides.
- `src/stream_adapter.py`: converts backend internals to frontend stream events.
- `src/scenarios/pricing_war_v1.yaml`: baseline scenario config.

## API Endpoints

- `POST /api/deep-simulator/run`
- `POST /api/deep-simulator/stream` (NDJSON)

## Request Body

```json
{
  "query": "Should we increase student pricing by 10%?",
  "max_ticks": 60,
  "seed": 7,
  "scenario_id": "pricing_war_v1",
  "min_personas": 3,
  "max_personas": 6,
  "summary_cadence_ticks": 7
}
```

## Stream Event Types

- `status`
- `progress`
- `world`
- `agent_tool_call`
- `agent_chunk`
- `timeline`
- `tick_event`
- `observer_summary`
- `final`
- `done`
