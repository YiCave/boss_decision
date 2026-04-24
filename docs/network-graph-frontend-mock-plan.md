# Network Graph Frontend Mock Plan (Parallel Feature)

## Goal

Add a new **network simulation mock UI** as a separate feature tab without removing or changing the existing deep 2D board behavior.

## Scope

- Build a new route and page for a network-based simulation view.
- Implement a three-pane layout:
  - Left: scenario input and runtime controls.
  - Center: interactive network graph canvas.
  - Right: node inspector, observer report, and post-run chat panel.
- Keep implementation mock-only for now (local simulated events/state).
- Preserve existing routes:
  - `/simulation-live`
  - `/simulation-deep`

## Interaction Model (Mock v1)

- User enters scenario and day count, then starts run.
- Simulation advances by day ticks with synthetic node actions and edge updates.
- User can pause/resume and inject a shock event.
- Clicking a node updates inspector details on the right.
- Observer report appears when run completes.
- Observer chat is disabled until completion, then answers using the run’s mock state/report.

## Technical Plan

- Add `NetworkSimulationLive` page and route `/simulation-network`.
- Add `NetworkSimulationSection` component with:
  - Node/edge model and typed edge categories.
  - Local tick engine and event timeline.
  - Interactive SVG graph (zoom, pan, node drag/select).
  - Node inspector and mock observer output.
- Add navigation links/buttons from existing simulation launch points.

## Acceptance for This Phase

- Network view opens in a separate tab/page and does not break existing pages.
- Graph is interactive and visibly updates during ticks.
- Left and right sections are functional and populated by mock data.
- Shock injection is visible in timeline and impacts node/edge statuses.
