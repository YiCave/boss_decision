export interface DataItem {
  source: string;
  label: string;
  value: string;
  trend: "up" | "down" | "flat";
}

export interface AgentInsight {
  name: string;
  emoji: string;
  insight: string;
}

export interface SubagentView {
  stance: "conservative" | "aggressive";
  recommendation: string;
  reasoning: string;
}

export interface Decision {
  verdict: string;
  reasoning: string;
  risk: "Low" | "Medium" | "High";
  confidence: number;
}

export interface AnalysisResult {
  data: DataItem[];
  agents: AgentInsight[];
  subagents: SubagentView[];
  decision: Decision;
  chat: ChatMessage[];
  routing: {
    selectedAgents: string[];
    routeSource: string;
    modelUsed?: string;
    reasoning?: string;
    routeError?: string;
  };
  usedMockFallback: boolean;
}

export interface ChatMessage {
  id: string;
  actor: "user" | "manager_router" | "agent" | "manager_tldr" | "system";
  label: string;
  text: string;
}

export interface AnalyzeOptions {
  context?: string;
  targetType?: string;
  targetId?: number;
  allowMockFallback: boolean;
  document?: File;
  mode?: string;
  forcedAgents?: string[];
}

interface BackendAnalyzeResponse {
  status: string;
  case_id: string;
  query: string;
  routing?: {
    selected_agents?: string[];
    route_source?: string;
    model_used?: string;
    reasoning?: string;
    route_error?: string;
  };
  final_decision?: {
    recommendation?: string;
    rationale?: string;
    risk_level?: "Low" | "Medium" | "High";
    confidence_score?: number;
  };
  agent_insights?: Array<{
    agent_name?: string;
    findings?: string[];
    recommendation?: string;
  }>;
  conservative_view?: string;
  aggressive_view?: string;
  document_analysis?: {
    department?: string;
    summary?: string;
    confidence?: number;
    model_used?: string;
    metadata?: {
      name?: string;
      extension?: string;
      size_bytes?: number;
      mime_type?: string;
    };
  };
}

const fireEmployeeResult: AnalysisResult = {
  data: [
    { source: "HR", label: "Performance trending down 6 mo.", value: "Score 2.1 / 5", trend: "down" },
    { source: "Sales", label: "Revenue contribution this Q", value: "RM 12,400", trend: "down" },
    { source: "Legal", label: "Severance & compliance cost", value: "RM 20,000", trend: "flat" },
  ],
  agents: [
    { name: "HR Agent", emoji: "👤", insight: "Employee underperforming for two consecutive review cycles. PIP not completed." },
    { name: "Sales Agent", emoji: "📉", insight: "Revenue contribution is in the bottom 8% of the team. Pipeline thin." },
    { name: "Legal Agent", emoji: "⚖️", insight: "Termination permitted with documented cause. Severance ~RM 20k required." },
  ],
  subagents: [
    {
      stance: "conservative",
      recommendation: "Do not fire — coach first",
      reasoning: "Short-term replacement cost (RM 45k+) and onboarding risk outweigh the savings. Try a 60-day PIP.",
    },
    {
      stance: "aggressive",
      recommendation: "Fire — performance issue",
      reasoning: "Sustained underperformance hurts team morale and revenue. Cut losses now and backfill from active pipeline.",
    },
  ],
  decision: {
    verdict: "DO NOT FIRE — Initiate 60-day PIP",
    reasoning:
      "Short-term termination cost (RM 65k including replacement & ramp) outweighs near-term benefit. A structured Performance Improvement Plan preserves optionality with measurable exit criteria.",
    risk: "Medium",
    confidence: 78,
  },
};

const acquireResult: AnalysisResult = {
  data: [
    { source: "Finance", label: "Acquisition price", value: "RM 4.2M", trend: "flat" },
    { source: "Market", label: "BetaCorp YoY growth", value: "+34%", trend: "up" },
    { source: "Legal", label: "Antitrust risk", value: "Low", trend: "flat" },
  ],
  agents: [
    { name: "Finance Agent", emoji: "💰", insight: "Cash reserves cover the deal at 1.8x EBITDA — within healthy range." },
    { name: "Strategy Agent", emoji: "♟️", insight: "Eliminates a fast-growing competitor and adds 22% market share." },
    { name: "Legal Agent", emoji: "⚖️", insight: "No regulatory blockers. Standard reps & warranties expected." },
  ],
  subagents: [
    {
      stance: "conservative",
      recommendation: "Negotiate down to RM 3.5M",
      reasoning: "Pay a fair multiple. Walk away if seller refuses — organic growth is a viable alternative.",
    },
    {
      stance: "aggressive",
      recommendation: "Acquire immediately at full price",
      reasoning: "Speed wins. Closing fast prevents a competing bid and locks in market consolidation.",
    },
  ],
  decision: {
    verdict: "ACQUIRE — Counter at RM 3.8M",
    reasoning:
      "Strategic upside is significant and financing is available, but a 10% price reduction protects margin. Strong walk-away position keeps leverage.",
    risk: "Medium",
    confidence: 84,
  },
};

const expansionResult: AnalysisResult = {
  data: [
    { source: "Market", label: "TAM in Singapore", value: "USD 180M", trend: "up" },
    { source: "Ops", label: "Setup cost (yr 1)", value: "RM 1.8M", trend: "flat" },
    { source: "Legal", label: "Regulatory complexity", value: "Moderate", trend: "flat" },
  ],
  agents: [
    { name: "Market Agent", emoji: "🌏", insight: "Demand signals strong; 3 enterprise leads already inbound from SG." },
    { name: "Ops Agent", emoji: "⚙️", insight: "Hiring market is competitive but feasible. Need a country lead first." },
    { name: "Legal Agent", emoji: "⚖️", insight: "Pte Ltd entity required. Data residency rules manageable." },
  ],
  subagents: [
    {
      stance: "conservative",
      recommendation: "Start with a remote sales pod",
      reasoning: "Validate demand for 6 months before opening an office. Limits downside to ~RM 400k.",
    },
    {
      stance: "aggressive",
      recommendation: "Launch full office in Q1",
      reasoning: "First-mover advantage in a hot market. Inbound leads suggest product-market fit already exists.",
    },
  ],
  decision: {
    verdict: "EXPAND — Phased entry, sales pod first",
    reasoning:
      "Inbound demand is real but unproven at scale. A 6-month remote pod de-risks the move while preserving a fast path to a full office if KPIs hit.",
    risk: "Low",
    confidence: 82,
  },
};

function analyzeMock(query: string): AnalysisResult {
  const q = query.toLowerCase();
  const base = q.includes("acqui") || q.includes("buy") || q.includes("merger")
    ? acquireResult
    : q.includes("expand") || q.includes("market") || q.includes("launch")
      ? expansionResult
      : fireEmployeeResult;

  return {
    ...base,
    chat: [
      { id: "u1", actor: "user", label: "User", text: query },
      {
        id: "m1",
        actor: "manager_router",
        label: "Manager Router",
        text: "Mock mode enabled. Routing and responses are generated from local mock data.",
      },
      ...base.agents.map((a, idx) => ({
        id: `a${idx + 1}`,
        actor: "agent" as const,
        label: a.name,
        text: a.insight,
      })),
      {
        id: "t1",
        actor: "manager_tldr",
        label: "Manager Agent",
        text: `${base.decision.verdict}. ${base.decision.reasoning}`,
      },
    ],
    routing: {
      selectedAgents: base.agents.map((a) => a.name.toLowerCase().replace(" agent", "")),
      routeSource: "mock",
      reasoning: "Mock fallback path",
    },
    usedMockFallback: true,
  };
}

export async function analyzeDecision(query: string, options: AnalyzeOptions): Promise<AnalysisResult> {
  const backendUrl = (import.meta.env.VITE_BACKEND_URL as string | undefined) || "http://localhost:8000";

  try {
    const hasDocument = Boolean(options.document);
    let response: Response;

    if (hasDocument && options.document) {
      const form = new FormData();
      form.append("query", query);
      if (options.context) form.append("context", options.context);
      if (options.targetType) form.append("target_type", options.targetType);
      if (typeof options.targetId === "number") form.append("target_id", String(options.targetId));
      form.append("submitted_by", "frontend");
      if (options.mode) form.append("mode", options.mode);
      if (options.forcedAgents) form.append("forced_agents", JSON.stringify(options.forcedAgents));
      form.append("document", options.document);

      response = await fetch(`${backendUrl}/api/analyze/upload`, {
        method: "POST",
        body: form,
      });
    } else {
      response = await fetch(`${backendUrl}/api/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query,
          context: options.context,
          target_type: options.targetType,
          target_id: options.targetId,
          submitted_by: "frontend",
          mode: options.mode || "hybrid",
          forced_agents: options.forcedAgents,
        }),
      });
    }

    if (!response.ok) {
      throw new Error(`Backend request failed with status ${response.status}`);
    }

    const payload = (await response.json()) as BackendAnalyzeResponse;

    const agentInsights = payload.agent_insights || [];
    const selectedAgents = payload.routing?.selected_agents || [];
    const routeSource = payload.routing?.route_source || "unknown";

    const data: DataItem[] = agentInsights.map((insight) => ({
      source: (insight.agent_name || "Unknown").toUpperCase(),
      label: "Primary finding",
      value: insight.findings?.[0] || "No findings",
      trend: "flat",
    }));

    const agents: AgentInsight[] = agentInsights.map((insight) => ({
      name: `${insight.agent_name || "Unknown"} Agent`,
      emoji: "\u{1F9E0}",
      insight: insight.recommendation || insight.findings?.[0] || "No recommendation",
    }));

    const subagents: SubagentView[] = [
      {
        stance: "conservative",
        recommendation: "Conservative perspective",
        reasoning: payload.conservative_view || "Not provided",
      },
      {
        stance: "aggressive",
        recommendation: "Aggressive perspective",
        reasoning: payload.aggressive_view || "Not provided",
      },
    ];

    const decision: Decision = {
      verdict: payload.final_decision?.recommendation || "No recommendation",
      reasoning: payload.final_decision?.rationale || "No rationale",
      risk: payload.final_decision?.risk_level || "Medium",
      confidence: Math.round(payload.final_decision?.confidence_score || 0),
    };

    const chat: ChatMessage[] = [
      { id: "u1", actor: "user", label: "User", text: query },
      ...(payload.document_analysis
        ? [
            {
              id: "d1",
              actor: "system" as const,
              label: "Document Analyzer",
              text: `Uploaded ${payload.document_analysis.metadata?.name || "file"} • Department: ${payload.document_analysis.department || "unknown"} • Summary: ${payload.document_analysis.summary || "n/a"}`,
            },
          ]
        : []),
      {
        id: "r1",
        actor: "manager_router",
        label: "Manager Router",
        text: `Selected agents: ${selectedAgents.join(", ") || "none"}. ${payload.routing?.reasoning || ""}`.trim(),
      },
      ...agentInsights.map((insight, idx) => ({
        id: `a${idx + 1}`,
        actor: "agent" as const,
        label: `${insight.agent_name || "Unknown"} Agent`,
        text: insight.recommendation || insight.findings?.[0] || "No recommendation",
      })),
      {
        id: "m1",
        actor: "manager_tldr",
        label: "Manager Agent",
        text: `${decision.verdict}. ${decision.reasoning}`,
      },
    ];

    if (routeSource === "fallback") {
      chat.splice(2, 0, {
        id: "s1",
        actor: "system",
        label: "System",
        text: `Fallback routing used.${payload.routing?.route_error ? ` Reason: ${payload.routing.route_error}` : ""}`,
      });
    }

    return {
      data,
      agents,
      subagents,
      decision,
      chat,
      routing: {
        selectedAgents,
        routeSource,
        modelUsed: payload.routing?.model_used,
        reasoning: payload.routing?.reasoning,
        routeError: payload.routing?.route_error,
      },
      usedMockFallback: false,
    };
  } catch (error) {
    if (!options.allowMockFallback) {
      throw error;
    }
    return analyzeMock(query);
  }
}
