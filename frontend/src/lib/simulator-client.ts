export interface SimulatorRequest {
  query: string;
  structured_data?: Record<string, unknown>;
  documents?: string[];
  business_context?: Record<string, unknown>;
}

export interface SimulatorStreamEvent {
  type: "status" | "update" | "custom" | "final" | "error" | "done";
  message?: string;
  nodes?: string[];
  updates?: Record<string, unknown>;
  event?: string;
  data?: Record<string, unknown>;
  response?: unknown;
  state?: Record<string, unknown>;
  error?: string;
}

export interface DeepSimulatorRequest {
  query: string;
  max_ticks?: number;
  seed?: number;
  scenario_id?: string;
}

export interface NetworkSimulatorRequest {
  query: string;
  max_ticks?: number;
  seed?: number;
  min_nodes?: number;
  max_nodes?: number;
  scenario_id?: string;
  allow_internet?: boolean;
  data_context_path?: string;
}

export interface DeepSimulatorStreamEvent {
  type:
    | "status"
    | "progress"
    | "world"
    | "tick_event"
    | "agent_tool_call"
    | "agent_chunk"
    | "timeline"
    | "final"
    | "error"
    | "done";
  message?: string;
  max_ticks?: number;
  tick?: number;
  summary?: string;
  state?: Record<string, unknown>;
  persona_id?: string;
  tool_call?: string;
  chunk?: string;
  response?: Record<string, unknown>;
  event_type?: string;
  source?: string;
  payload?: Record<string, unknown>;
  ts?: string;
  error?: string;
}

export interface NetworkSimulatorStreamEvent {
  type:
    | "status"
    | "progress"
    | "network_state"
    | "node_action"
    | "node_message"
    | "edge_update"
    | "shock_event"
    | "observer_summary"
    | "final"
    | "error"
    | "done";
  session_id?: string;
  message?: unknown;
  tick?: number;
  max_ticks?: number;
  summary?: string;
  state?: Record<string, unknown>;
  action?: Record<string, unknown>;
  edge?: Record<string, unknown>;
  shock?: Record<string, unknown>;
  result?: Record<string, unknown>;
  confidence?: number;
  error?: string;
}

interface StreamHandlers {
  onEvent: (event: SimulatorStreamEvent) => void;
}

interface DeepStreamHandlers {
  onEvent: (event: DeepSimulatorStreamEvent) => void;
  signal?: AbortSignal;
}

interface NetworkStreamHandlers {
  onEvent: (event: NetworkSimulatorStreamEvent) => void;
  signal?: AbortSignal;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function streamSimulator(
  request: SimulatorRequest,
  handlers: StreamHandlers,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/simulator/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Simulator stream request failed (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const parsed = JSON.parse(trimmed) as SimulatorStreamEvent;
      handlers.onEvent(parsed);
      if (parsed.type === "done") return;
    }
  }
}

export async function streamDeepSimulator(
  request: DeepSimulatorRequest,
  handlers: DeepStreamHandlers,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/deep-simulator/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal: handlers.signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Deep simulator stream request failed (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const parsed = JSON.parse(trimmed) as DeepSimulatorStreamEvent;
      handlers.onEvent(parsed);
      if (parsed.type === "done") return;
    }
  }
}

export async function streamNetworkSimulator(
  request: NetworkSimulatorRequest,
  handlers: NetworkStreamHandlers,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/network-simulator/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal: handlers.signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Network simulator stream request failed (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const parsed = JSON.parse(trimmed) as NetworkSimulatorStreamEvent;
      handlers.onEvent(parsed);
      if (parsed.type === "done") return;
    }
  }
}

export async function injectNetworkShock(
  sessionId: string,
  request: {
    shock_type: string;
    summary: string;
    severity: number;
    targets?: string[];
  },
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/network-simulator/${sessionId}/shock`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Shock request failed (${response.status})`);
  }
}

export async function chatNetworkObserver(
  sessionId: string,
  question: string,
): Promise<{ answer: string }> {
  const response = await fetch(`${API_BASE}/api/network-simulator/${sessionId}/observer-chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new Error(`Observer chat failed (${response.status})`);
  }
  const payload = (await response.json()) as { answer?: string };
  return { answer: payload.answer ?? "No observer answer returned." };
}

export async function downloadNetworkStoryline(sessionId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/network-simulator/${sessionId}/storyline`, {
    method: "GET",
  });
  if (!response.ok) {
    throw new Error(`Storyline download failed (${response.status})`);
  }
  return response.blob();
}
