export interface SalesSupplyDebateRequest {
  item_name?: string;
  max_rounds?: number;
}

export interface DebateRound {
  round: number;
  sales_agent: {
    agent_id: string;
    role: string;
    suggestion: string;
    market_signal?: string;
  };
  supply_chain_agent: {
    agent_id: string;
    role: string;
    validity: "valid" | "invalid";
    strict_checks: string[];
    response: string;
  };
}

export interface DebateSimulationResult {
  supply_id: number;
  item_name: string;
  inventory_context: {
    inventory_level: number | null;
    demand_forecast: number | null;
    reorder_point: number | null;
    shortage_flag: number | null;
    supplier_name: string | null;
    unit_cost: number | null;
  };
  rounds: DebateRound[];
  final_result: {
    status: "approved" | "rejected";
    winner?: "sales_agent" | "supply_chain_agent";
    conclusion: string;
  };
  judge_result?: {
    winner: "sales" | "supply";
    verdict: "execute" | "hold";
    rationale: string;
    confidence: number;
  };
}

export interface SalesSupplyDebateResponse {
  status: "ok" | "no_data";
  message?: string;
  max_rounds?: number;
  retrieved_item_names: string[];
  simulations: DebateSimulationResult[];
  summary?: {
    total_items: number;
    approved: number;
    rejected: number;
  };
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function runSalesSupplyDebateSimulation(
  request: SalesSupplyDebateRequest,
): Promise<SalesSupplyDebateResponse> {
  const response = await fetch(`${API_BASE}/api/simulator/sales-supply-debate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let message = `Debate simulator request failed (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      // Keep generic message.
    }
    throw new Error(message);
  }

  return (await response.json()) as SalesSupplyDebateResponse;
}
