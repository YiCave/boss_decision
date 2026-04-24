import { useEffect, useMemo, useRef, useState, type PointerEvent, type WheelEvent } from "react";
import {
  AlertTriangle,
  BadgeDollarSign,
  Banknote,
  Building2,
  CheckCircle2,
  Factory,
  GraduationCap,
  Landmark,
  Megaphone,
  Pause,
  Play,
  RotateCcw,
  Info,
  FileText,
  X,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Store,
  TrendingUp,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DeepSimulatorStreamEvent, streamDeepSimulator } from "@/lib/simulator-client";

type AgentStatus = "idle" | "thinking" | "acting" | "done";
type GamePhase = "setup" | "world" | "observe" | "action" | "resolution" | "scoring" | "summary" | "complete";

interface AgentCard {
  id: string;
  name: string;
  role: string;
  objective: string;
  allowedPaths: string[];
  color: string;
  x: number;
  y: number;
  status: AgentStatus;
  toolCalls: string[];
  transcript: string;
  confidence: number;
  score: number;
}

interface TimelineEvent {
  id: string;
  tick: number;
  message: string;
}

interface ScorePoint {
  tick: number;
  [key: string]: number;
}

interface ActionRecord {
  tick: number;
  phase: GamePhase;
  persona_id: string;
  persona_name: string;
  action_type: string;
  status: "pending" | "resolved" | "rejected";
  summary: string;
  target_zone_id?: string | null;
  confidence: number;
  args?: Record<string, unknown>;
  rationale_md?: string;
  outcome?: string;
  requested_via_tool?: boolean;
  requested_tool?: string;
}

interface ActiveEventCard {
  id: string;
  title: string;
  summary: string;
  effects: Record<string, number>;
  counter_actions: string[];
  matched_actions: string[];
}

interface SocialLink {
  source_persona_id: string;
  target_persona_id: string;
  trust: number;
  talk_count: number;
  support_count: number;
  oppose_count: number;
  last_interaction: string;
  updated_tick: number;
}

interface PersonaScoreBreakdown {
  persona_id: string;
  persona_name: string;
  base_points: number;
  movement_points: number;
  intent_quality_points: number;
  kpi_contribution_points: number;
  crisis_response_points: number;
  timing_points: number;
  resource_efficiency_points: number;
  social_influence_points: number;
  total_delta: number;
  total_score: number;
}

interface TickScoreBreakdown {
  tick: number;
  kpi_shift: number;
  personas: PersonaScoreBreakdown[];
}

interface TickSnapshot {
  tick: number;
  phase: GamePhase;
  summary: string;
  kpi: {
    revenue: number;
    margin: number;
    sentiment: number;
    churn_risk: number;
  };
  actions: ActionRecord[];
  scoreBreakdown: TickScoreBreakdown | null;
}

interface FinalReport {
  summary: string;
  recommendation: string;
  confidence: number;
  key_turning_points: string[];
  persona_observations?: Array<{
    persona_id: string;
    name: string;
    role: string;
    objective: string;
    stance: string;
    evidence: string[];
    suggested_next_action: string;
  }>;
  html_slides: string;
}

interface BoardTile {
  id: string;
  name: string;
  x: number;
  y: number;
}

interface TileVisual {
  icon: LucideIcon;
  accentClass: string;
  iconClass: string;
  blocks: number;
  effectLabel: string;
  effectToneClass: string;
  glowColor: string;
}

interface BoardEdge {
  from: string;
  to: string;
}

interface WorldAgent {
  id?: unknown;
  name?: unknown;
  role?: unknown;
  x?: unknown;
  y?: unknown;
  status?: unknown;
  tool_calls?: unknown;
  transcript?: unknown;
  confidence?: unknown;
}

interface WorldPersona {
  id?: unknown;
  name?: unknown;
  role?: unknown;
  objective?: unknown;
  allowed_paths?: unknown;
}

interface WorldActionRecord {
  tick?: unknown;
  phase?: unknown;
  persona_id?: unknown;
  persona_name?: unknown;
  action_type?: unknown;
  status?: unknown;
  summary?: unknown;
  target_zone_id?: unknown;
  confidence?: unknown;
  args?: unknown;
  rationale_md?: unknown;
  outcome?: unknown;
  requested_via_tool?: unknown;
  requested_tool?: unknown;
}

interface WorldActiveEvent {
  id?: unknown;
  title?: unknown;
  summary?: unknown;
  effects?: unknown;
  counter_actions?: unknown;
  matched_actions?: unknown;
}

interface WorldSocialLink {
  source_persona_id?: unknown;
  target_persona_id?: unknown;
  trust?: unknown;
  talk_count?: unknown;
  support_count?: unknown;
  oppose_count?: unknown;
  last_interaction?: unknown;
  updated_tick?: unknown;
}

interface WorldPersonaScoreBreakdown {
  persona_id?: unknown;
  persona_name?: unknown;
  base_points?: unknown;
  movement_points?: unknown;
  intent_quality_points?: unknown;
  kpi_contribution_points?: unknown;
  crisis_response_points?: unknown;
  timing_points?: unknown;
  resource_efficiency_points?: unknown;
  social_influence_points?: unknown;
  total_delta?: unknown;
  total_score?: unknown;
}

interface WorldTickScoreBreakdown {
  tick?: unknown;
  kpi_shift?: unknown;
  personas?: unknown;
}

const DEFAULT_QUERY = "Should we increase price by 10% for student segment next quarter?";
const DEFAULT_MAX_TICKS = 5;
const RUN_TICK_MIN = 1;
const RUN_TICK_MAX = 240;
const SHARED_START_X = 50;
const SHARED_START_Y = 50;
const DEFAULT_PHASE: GamePhase = "setup";
const PHASE_ORDER: GamePhase[] = ["world", "observe", "action", "resolution", "scoring", "summary"];

const AGENT_COLOR_OVERRIDES: Record<string, string> = {
  consumer_psychologist_001: "hsl(18 88% 51%)",
  pricing_strategist_001: "hsl(171 66% 36%)",
  market_risk_001: "hsl(38 86% 44%)",
  ops_constraints_001: "hsl(148 62% 34%)",
  brand_positioning_001: "hsl(204 32% 26%)",
};

const PERSONA_COLOR_PALETTE = [
  "hsl(18 88% 51%)",
  "hsl(171 66% 36%)",
  "hsl(38 86% 44%)",
  "hsl(148 62% 34%)",
  "hsl(204 32% 26%)",
  "hsl(12 73% 52%)",
  "hsl(26 79% 46%)",
  "hsl(196 48% 38%)",
  "hsl(163 54% 34%)",
  "hsl(29 69% 40%)",
  "hsl(205 21% 34%)",
  "hsl(8 63% 44%)",
];

const PERSONA_SPRITES = Array.from(
  { length: 49 },
  (_, idx) => `/assets/personas/persona_${String(idx + 1).padStart(2, "0")}.png`,
);

const personaVisualCache = new Map<string, { color: string; avatarUrl: string }>();

function hashString(input: string): number {
  let hash = 0;
  for (let idx = 0; idx < input.length; idx += 1) {
    hash = (hash * 31 + input.charCodeAt(idx)) >>> 0;
  }
  return hash;
}

function getPersonaVisual(personaId: string): { color: string; avatarUrl: string } {
  const cached = personaVisualCache.get(personaId);
  if (cached) return cached;
  const hash = hashString(personaId || "persona");
  const color = AGENT_COLOR_OVERRIDES[personaId] ?? PERSONA_COLOR_PALETTE[hash % PERSONA_COLOR_PALETTE.length];
  const avatarUrl = PERSONA_SPRITES[hash % PERSONA_SPRITES.length];
  const visual = { color, avatarUrl };
  personaVisualCache.set(personaId, visual);
  return visual;
}

const BASE_AGENTS: AgentCard[] = [
  {
    id: "consumer_psychologist_001",
    name: "Consumer Psychologist",
    role: "Demand behavior lead",
    objective: "Understand student demand reaction and churn behavior.",
    allowedPaths: [],
    color: AGENT_COLOR_OVERRIDES.consumer_psychologist_001,
    x: SHARED_START_X,
    y: SHARED_START_Y,
    status: "idle",
    toolCalls: [],
    transcript: "",
    confidence: 0.5,
    score: 0,
  },
  {
    id: "pricing_strategist_001",
    name: "Pricing Strategist",
    role: "Price and promo architect",
    objective: "Model price elasticity and promotion tradeoffs.",
    allowedPaths: [],
    color: AGENT_COLOR_OVERRIDES.pricing_strategist_001,
    x: SHARED_START_X,
    y: SHARED_START_Y,
    status: "idle",
    toolCalls: [],
    transcript: "",
    confidence: 0.5,
    score: 0,
  },
  {
    id: "market_risk_001",
    name: "Market Risk",
    role: "Competitor response radar",
    objective: "Estimate competitor retaliation and market downside.",
    allowedPaths: [],
    color: AGENT_COLOR_OVERRIDES.market_risk_001,
    x: SHARED_START_X,
    y: SHARED_START_Y,
    status: "idle",
    toolCalls: [],
    transcript: "",
    confidence: 0.5,
    score: 0,
  },
  {
    id: "ops_constraints_001",
    name: "Ops Constraints",
    role: "Execution feasibility owner",
    objective: "Validate operational feasibility and rollout limits.",
    allowedPaths: [],
    color: AGENT_COLOR_OVERRIDES.ops_constraints_001,
    x: SHARED_START_X,
    y: SHARED_START_Y,
    status: "idle",
    toolCalls: [],
    transcript: "",
    confidence: 0.5,
    score: 0,
  },
  {
    id: "brand_positioning_001",
    name: "Brand Positioning",
    role: "Narrative and trust steward",
    objective: "Protect brand trust and long-term positioning.",
    allowedPaths: [],
    color: AGENT_COLOR_OVERRIDES.brand_positioning_001,
    x: SHARED_START_X,
    y: SHARED_START_Y,
    status: "idle",
    toolCalls: [],
    transcript: "",
    confidence: 0.5,
    score: 0,
  },
];

const DEFAULT_TILES: BoardTile[] = [
  { id: "demand_hub", name: "Demand Hub", x: 10, y: 10 },
  { id: "campus_square", name: "Campus Square", x: 30, y: 10 },
  { id: "digital_blast", name: "Digital Blast", x: 50, y: 10 },
  { id: "retail_lane", name: "Retail Lane", x: 70, y: 10 },
  { id: "promo_stage", name: "Promo Stage", x: 90, y: 30 },
  { id: "supply_yard", name: "Supply Yard", x: 90, y: 50 },
  { id: "finance_tower", name: "Finance Tower", x: 90, y: 70 },
  { id: "brand_garden", name: "Brand Garden", x: 70, y: 90 },
  { id: "competitor_radar", name: "Competitor Radar", x: 50, y: 90 },
  { id: "compliance_gate", name: "Compliance Gate", x: 30, y: 90 },
  { id: "loyalty_park", name: "Loyalty Park", x: 10, y: 90 },
  { id: "volatility_crossing", name: "Volatility Crossing", x: 10, y: 50 },
];

const TILE_VISUALS: Record<string, TileVisual> = {
  demand_hub: {
    icon: Building2,
    accentClass: "bg-slate-600",
    iconClass: "text-slate-600",
    blocks: 4,
    effectLabel: "Demand",
    effectToneClass: "border-slate-300 bg-slate-100/90 text-slate-700",
    glowColor: "hsl(215 18% 50% / 0.26)",
  },
  campus_square: {
    icon: GraduationCap,
    accentClass: "bg-indigo-600",
    iconClass: "text-indigo-600",
    blocks: 3,
    effectLabel: "Audience",
    effectToneClass: "border-indigo-300 bg-indigo-100/85 text-indigo-700",
    glowColor: "hsl(245 70% 58% / 0.26)",
  },
  digital_blast: {
    icon: ShoppingCart,
    accentClass: "bg-cyan-600",
    iconClass: "text-cyan-600",
    blocks: 3,
    effectLabel: "Reach",
    effectToneClass: "border-cyan-300 bg-cyan-100/85 text-cyan-700",
    glowColor: "hsl(191 83% 45% / 0.25)",
  },
  retail_lane: {
    icon: Store,
    accentClass: "bg-emerald-600",
    iconClass: "text-emerald-600",
    blocks: 2,
    effectLabel: "Sellout",
    effectToneClass: "border-emerald-300 bg-emerald-100/85 text-emerald-700",
    glowColor: "hsl(156 72% 41% / 0.24)",
  },
  promo_stage: {
    icon: Megaphone,
    accentClass: "bg-rose-600",
    iconClass: "text-rose-600",
    blocks: 3,
    effectLabel: "Burst",
    effectToneClass: "border-rose-300 bg-rose-100/85 text-rose-700",
    glowColor: "hsl(347 89% 57% / 0.23)",
  },
  supply_yard: {
    icon: Factory,
    accentClass: "bg-amber-700",
    iconClass: "text-amber-700",
    blocks: 4,
    effectLabel: "Ops",
    effectToneClass: "border-amber-300 bg-amber-100/85 text-amber-800",
    glowColor: "hsl(38 90% 45% / 0.24)",
  },
  finance_tower: {
    icon: Banknote,
    accentClass: "bg-green-700",
    iconClass: "text-green-700",
    blocks: 4,
    effectLabel: "Margin",
    effectToneClass: "border-green-300 bg-green-100/85 text-green-800",
    glowColor: "hsl(132 65% 34% / 0.26)",
  },
  brand_garden: {
    icon: Sparkles,
    accentClass: "bg-fuchsia-600",
    iconClass: "text-fuchsia-600",
    blocks: 3,
    effectLabel: "Trust",
    effectToneClass: "border-fuchsia-300 bg-fuchsia-100/85 text-fuchsia-700",
    glowColor: "hsl(292 82% 58% / 0.24)",
  },
  competitor_radar: {
    icon: Users,
    accentClass: "bg-orange-700",
    iconClass: "text-orange-700",
    blocks: 2,
    effectLabel: "Threat",
    effectToneClass: "border-orange-300 bg-orange-100/85 text-orange-700",
    glowColor: "hsl(24 91% 53% / 0.24)",
  },
  compliance_gate: {
    icon: ShieldCheck,
    accentClass: "bg-blue-700",
    iconClass: "text-blue-700",
    blocks: 3,
    effectLabel: "Guard",
    effectToneClass: "border-blue-300 bg-blue-100/85 text-blue-700",
    glowColor: "hsl(216 91% 53% / 0.25)",
  },
  loyalty_park: {
    icon: Landmark,
    accentClass: "bg-teal-700",
    iconClass: "text-teal-700",
    blocks: 2,
    effectLabel: "Retention",
    effectToneClass: "border-teal-300 bg-teal-100/85 text-teal-700",
    glowColor: "hsl(173 81% 34% / 0.24)",
  },
  volatility_crossing: {
    icon: AlertTriangle,
    accentClass: "bg-red-700",
    iconClass: "text-red-700",
    blocks: 2,
    effectLabel: "Shock",
    effectToneClass: "border-red-300 bg-red-100/85 text-red-700",
    glowColor: "hsl(0 82% 55% / 0.25)",
  },
};

const BOARD_EDGES: BoardEdge[] = [
  { from: "demand_hub", to: "campus_square" },
  { from: "campus_square", to: "digital_blast" },
  { from: "digital_blast", to: "retail_lane" },
  { from: "retail_lane", to: "promo_stage" },
  { from: "promo_stage", to: "supply_yard" },
  { from: "supply_yard", to: "finance_tower" },
  { from: "finance_tower", to: "brand_garden" },
  { from: "brand_garden", to: "competitor_radar" },
  { from: "competitor_radar", to: "compliance_gate" },
  { from: "compliance_gate", to: "loyalty_park" },
  { from: "loyalty_park", to: "volatility_crossing" },
  { from: "volatility_crossing", to: "demand_hub" },
  { from: "digital_blast", to: "competitor_radar" },
  { from: "campus_square", to: "compliance_gate" },
  { from: "supply_yard", to: "volatility_crossing" },
];

function tileVisual(id: string): TileVisual {
  return TILE_VISUALS[id] ?? {
    icon: BadgeDollarSign,
    accentClass: "bg-slate-500",
    iconClass: "text-slate-600",
    blocks: 2,
    effectLabel: "General",
    effectToneClass: "border-slate-300 bg-slate-100/90 text-slate-700",
    glowColor: "hsl(216 18% 50% / 0.22)",
  };
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function formatSigned(value: number): string {
  if (value > 0) return `+${value.toFixed(2)}`;
  return value.toFixed(2);
}

function humanStatus(status: AgentStatus): string {
  if (status === "done") return "Done";
  if (status === "acting") return "Acting";
  if (status === "thinking") return "Thinking";
  return "Idle";
}

function statusBadgeTone(status: AgentStatus): string {
  if (status === "done") return "border-success/40 bg-success/10 text-foreground";
  if (status === "acting") return "border-primary/50 bg-primary/10 text-foreground";
  if (status === "thinking") return "border-warning/40 bg-warning/10 text-foreground";
  return "border-border bg-secondary text-secondary-foreground";
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function nearestTileId(x: number, y: number, tiles: BoardTile[]): string | null {
  if (tiles.length === 0) return null;
  let best: BoardTile | null = null;
  let bestDist = Number.POSITIVE_INFINITY;
  for (const tile of tiles) {
    const dx = tile.x - x;
    const dy = tile.y - y;
    const dist = dx * dx + dy * dy;
    if (dist < bestDist) {
      bestDist = dist;
      best = tile;
    }
  }
  // Ignore far-away matches so pings stay meaningful.
  return best && bestDist <= 220 ? best.id : null;
}

function inferTilesFromMessage(message: string, tiles: BoardTile[]): string[] {
  const lower = message.toLowerCase();
  const hits = tiles
    .filter((tile) => lower.includes(tile.name.toLowerCase()) || lower.includes(tile.id.replaceAll("_", " ")))
    .map((tile) => tile.id);
  return Array.from(new Set(hits));
}

function isShockMessage(message: string): boolean {
  const text = message.toLowerCase();
  return ["crisis", "shock", "volatility", "retaliation", "downside", "incident"].some((token) => text.includes(token));
}

function boardTokenTone(status: AgentStatus): string {
  if (status === "thinking") return "board-token-thinking";
  if (status === "acting") return "board-token-acting";
  return "";
}

function boardStatusBubble(agent: AgentCard): string {
  if (agent.status === "thinking") return "Thinking...";
  if (agent.status === "acting") return "Acting...";
  if (agent.status === "done") return "Done";
  return "Idle";
}

function mapWorldAgents(input: unknown, previous: AgentCard[]): AgentCard[] {
  if (!Array.isArray(input)) return previous;
  const prevById = Object.fromEntries(previous.map((agent) => [agent.id, agent]));
  return input
    .map((row) => {
      if (!row || typeof row !== "object") return null;
      const agent = row as WorldAgent;
      const id = typeof agent.id === "string" ? agent.id : "";
      if (!id) return null;
      const prev = prevById[id];
      const status = agent.status;
      const normalizedStatus: AgentStatus =
        status === "idle" || status === "thinking" || status === "acting" || status === "done"
          ? status
          : prev?.status ?? "idle";
      return {
        id,
        name: typeof agent.name === "string" ? agent.name : prev?.name ?? id,
        role: typeof agent.role === "string" ? agent.role : prev?.role ?? "persona",
        objective: prev?.objective ?? "",
        allowedPaths: prev?.allowedPaths ?? [],
        color: prev?.color ?? getPersonaVisual(id).color,
        x: asNumber(agent.x, prev?.x ?? 50),
        y: asNumber(agent.y, prev?.y ?? 50),
        status: normalizedStatus,
        toolCalls: Array.isArray(agent.tool_calls)
          ? agent.tool_calls.filter((item): item is string => typeof item === "string").slice(-10)
          : prev?.toolCalls ?? [],
        transcript: typeof agent.transcript === "string" ? agent.transcript : prev?.transcript ?? "",
        confidence: asNumber(agent.confidence, prev?.confidence ?? 0.5),
        score: prev?.score ?? 0,
      };
    })
    .filter((item): item is AgentCard => item !== null);
}

function applyPersonaProfiles(input: unknown, previous: AgentCard[]): AgentCard[] {
  if (!Array.isArray(input)) return previous;
  const byId = new Map<string, WorldPersona>();
  for (const row of input) {
    if (!row || typeof row !== "object") continue;
    const persona = row as WorldPersona;
    const id = typeof persona.id === "string" ? persona.id : "";
    if (!id) continue;
    byId.set(id, persona);
  }
  if (byId.size === 0) return previous;
  return previous.map((agent) => {
    const persona = byId.get(agent.id);
    if (!persona) return agent;
    const allowedPaths = Array.isArray(persona.allowed_paths)
      ? persona.allowed_paths.filter((item): item is string => typeof item === "string")
      : agent.allowedPaths;
    return {
      ...agent,
      name: typeof persona.name === "string" ? persona.name : agent.name,
      role: typeof persona.role === "string" ? persona.role : agent.role,
      objective: typeof persona.objective === "string" ? persona.objective : agent.objective,
      allowedPaths,
    };
  });
}

function mapBoardTiles(input: unknown, fallback: BoardTile[]): BoardTile[] {
  if (!Array.isArray(input)) return fallback;
  const parsed = input
    .map((row) => {
      if (!row || typeof row !== "object") return null;
      const item = row as Record<string, unknown>;
      if (typeof item.id !== "string" || typeof item.name !== "string") return null;
      return {
        id: item.id,
        name: item.name,
        x: asNumber(item.x, 50),
        y: asNumber(item.y, 50),
      };
    })
    .filter((item): item is BoardTile => item !== null);
  return parsed.length > 0 ? parsed : fallback;
}

function asScoreMap(input: unknown): Record<string, number> {
  if (!input || typeof input !== "object") return {};
  const out: Record<string, number> = {};
  for (const [key, value] of Object.entries(input as Record<string, unknown>)) {
    out[key] = asNumber(value, 0);
  }
  return out;
}

function isGamePhase(value: unknown): value is GamePhase {
  return (
    value === "setup" ||
    value === "world" ||
    value === "observe" ||
    value === "action" ||
    value === "resolution" ||
    value === "scoring" ||
    value === "summary" ||
    value === "complete"
  );
}

function mapActionRecords(input: unknown): ActionRecord[] {
  if (!Array.isArray(input)) return [];
  return input
    .map((row) => {
      if (!row || typeof row !== "object") return null;
      const item = row as WorldActionRecord;
      const personaId = typeof item.persona_id === "string" ? item.persona_id : "";
      const actionType = typeof item.action_type === "string" ? item.action_type : "";
      if (!personaId || !actionType) return null;
      return {
        tick: asNumber(item.tick, 0),
        phase: isGamePhase(item.phase) ? item.phase : "action",
        persona_id: personaId,
        persona_name: typeof item.persona_name === "string" ? item.persona_name : personaId,
        action_type: actionType,
        status: item.status === "resolved" || item.status === "rejected" ? item.status : "pending",
        summary: typeof item.summary === "string" ? item.summary : actionType.replaceAll("_", " "),
        target_zone_id: typeof item.target_zone_id === "string" ? item.target_zone_id : null,
        confidence: asNumber(item.confidence, 0.5),
        args: item.args && typeof item.args === "object" ? (item.args as Record<string, unknown>) : {},
        rationale_md: typeof item.rationale_md === "string" ? item.rationale_md : "",
        outcome: typeof item.outcome === "string" ? item.outcome : "",
        requested_via_tool: Boolean(item.requested_via_tool),
        requested_tool: typeof item.requested_tool === "string" ? item.requested_tool : "",
      };
    })
    .filter((item): item is ActionRecord => item !== null);
}

function mapActiveEvent(input: unknown): ActiveEventCard | null {
  if (!input || typeof input !== "object") return null;
  const item = input as WorldActiveEvent;
  const id = typeof item.id === "string" ? item.id : "";
  const title = typeof item.title === "string" ? item.title : "";
  if (!id || !title) return null;
  return {
    id,
    title,
    summary: typeof item.summary === "string" ? item.summary : "",
    effects: asScoreMap(item.effects),
    counter_actions: Array.isArray(item.counter_actions)
      ? item.counter_actions.filter((entry): entry is string => typeof entry === "string")
      : [],
    matched_actions: Array.isArray(item.matched_actions)
      ? item.matched_actions.filter((entry): entry is string => typeof entry === "string")
      : [],
  };
}

function mapSocialLinks(input: unknown): SocialLink[] {
  if (!Array.isArray(input)) return [];
  return input
    .map((row) => {
      if (!row || typeof row !== "object") return null;
      const item = row as WorldSocialLink;
      const source = typeof item.source_persona_id === "string" ? item.source_persona_id : "";
      const target = typeof item.target_persona_id === "string" ? item.target_persona_id : "";
      if (!source || !target || source === target) return null;
      return {
        source_persona_id: source,
        target_persona_id: target,
        trust: clamp(asNumber(item.trust, 0), -1, 1),
        talk_count: Math.max(0, Math.round(asNumber(item.talk_count, 0))),
        support_count: Math.max(0, Math.round(asNumber(item.support_count, 0))),
        oppose_count: Math.max(0, Math.round(asNumber(item.oppose_count, 0))),
        last_interaction: typeof item.last_interaction === "string" ? item.last_interaction : "none",
        updated_tick: Math.max(0, Math.round(asNumber(item.updated_tick, 0))),
      };
    })
    .filter((item): item is SocialLink => item !== null);
}

function mapTickScoreBreakdown(input: unknown): TickScoreBreakdown | null {
  if (!input || typeof input !== "object") return null;
  const item = input as WorldTickScoreBreakdown;
  const personas = Array.isArray(item.personas)
    ? item.personas
        .map((row) => {
          if (!row || typeof row !== "object") return null;
          const persona = row as WorldPersonaScoreBreakdown;
          const personaId = typeof persona.persona_id === "string" ? persona.persona_id : "";
          if (!personaId) return null;
          return {
            persona_id: personaId,
            persona_name: typeof persona.persona_name === "string" ? persona.persona_name : personaId,
            base_points: asNumber(persona.base_points, 0),
            movement_points: asNumber(persona.movement_points, 0),
            intent_quality_points: asNumber(persona.intent_quality_points, 0),
            kpi_contribution_points: asNumber(persona.kpi_contribution_points, 0),
            crisis_response_points: asNumber(persona.crisis_response_points, 0),
            timing_points: asNumber(persona.timing_points, 0),
            resource_efficiency_points: asNumber(persona.resource_efficiency_points, 0),
            social_influence_points: asNumber(persona.social_influence_points, 0),
            total_delta: asNumber(persona.total_delta, 0),
            total_score: asNumber(persona.total_score, 0),
          };
        })
        .filter((row): row is PersonaScoreBreakdown => row !== null)
    : [];
  return {
    tick: Math.max(0, Math.round(asNumber(item.tick, 0))),
    kpi_shift: asNumber(item.kpi_shift, 0),
    personas,
  };
}

function phaseLabel(phase: GamePhase): string {
  if (phase === "world") return "World";
  if (phase === "observe") return "Observe";
  if (phase === "action") return "Actions";
  if (phase === "resolution") return "Resolve";
  if (phase === "scoring") return "Scoring";
  if (phase === "summary") return "Summary";
  if (phase === "complete") return "Complete";
  return "Setup";
}

function phaseDescription(phase: GamePhase): string {
  if (phase === "world") return "Market pressure and movement update.";
  if (phase === "observe") return "Personas read state before committing.";
  if (phase === "action") return "AI personas queue legal actions.";
  if (phase === "resolution") return "Engine validates and applies results.";
  if (phase === "scoring") return "KPI and persona scores update.";
  if (phase === "summary") return "Day summary is written to history.";
  if (phase === "complete") return "Simulation finished.";
  return "Preparing scenario state.";
}

function actionStatusTone(status: ActionRecord["status"]): string {
  if (status === "resolved") return "border-emerald-300/70 bg-emerald-50/80 text-emerald-800";
  if (status === "rejected") return "border-red-300/70 bg-red-50/80 text-red-800";
  return "border-amber-300/70 bg-amber-50/80 text-amber-800";
}

function zoneSummary(tileId: string): string {
  const visual = tileVisual(tileId);
  return visual.effectLabel;
}

function PersonaAvatar({
  personaId,
  name,
  size = 24,
  className = "",
}: {
  personaId: string;
  name: string;
  size?: number;
  className?: string;
}) {
  const visual = getPersonaVisual(personaId);
  return (
    <span
      className={`inline-flex items-center justify-center overflow-hidden rounded-lg border-2 bg-white ${className}`}
      style={{ width: size, height: size, borderColor: visual.color }}
    >
      <img
        src={visual.avatarUrl}
        alt={name}
        className="h-full w-full object-contain"
        style={{ imageRendering: "pixelated" }}
        draggable={false}
      />
    </span>
  );
}

export function DeepSimulationSection() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [requestedTicks, setRequestedTicks] = useState(DEFAULT_MAX_TICKS);
  const [tick, setTick] = useState(0);
  const [maxTicks, setMaxTicks] = useState(DEFAULT_MAX_TICKS);
  const [running, setRunning] = useState(false);
  const [progressSummary, setProgressSummary] = useState("Ready to run the tycoon crisis simulation.");
  const [error, setError] = useState<string | null>(null);
  const [agents, setAgents] = useState<AgentCard[]>(BASE_AGENTS);
  const [selectedAgentId, setSelectedAgentId] = useState(BASE_AGENTS[0].id);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [boardTiles, setBoardTiles] = useState<BoardTile[]>(DEFAULT_TILES);
  const [kpi, setKpi] = useState({ revenue: 0, margin: 0, sentiment: 0, churn_risk: 0 });
  const [currentPhase, setCurrentPhase] = useState<GamePhase>(DEFAULT_PHASE);
  const [pendingActions, setPendingActions] = useState<ActionRecord[]>([]);
  const [resolvedActions, setResolvedActions] = useState<ActionRecord[]>([]);
  const [activeEvent, setActiveEvent] = useState<ActiveEventCard | null>(null);
  const [socialLinks, setSocialLinks] = useState<SocialLink[]>([]);
  const [latestScoreBreakdown, setLatestScoreBreakdown] = useState<TickScoreBreakdown | null>(null);
  const [scoreSeries, setScoreSeries] = useState<ScorePoint[]>([]);
  const [tickSnapshots, setTickSnapshots] = useState<Record<number, TickSnapshot>>({});
  const [replayTick, setReplayTick] = useState(0);
  const [followLive, setFollowLive] = useState(true);
  const [isReplayPlaying, setIsReplayPlaying] = useState(false);
  const [finalReport, setFinalReport] = useState<FinalReport | null>(null);
  const [showResultCard, setShowResultCard] = useState(false);
  const [showInfoCard, setShowInfoCard] = useState(false);
  const [boardScale, setBoardScale] = useState(1);
  const [boardOffset, setBoardOffset] = useState({ x: 0, y: 0 });
  const [isBoardDragging, setIsBoardDragging] = useState(false);
  const [pulsedTileIds, setPulsedTileIds] = useState<string[]>([]);
  const [isBoardShaking, setIsBoardShaking] = useState(false);
  const [cameraFollowUntil, setCameraFollowUntil] = useState(0);

  const abortRef = useRef<AbortController | null>(null);
  const followLiveRef = useRef(true);
  const tickRef = useRef(0);
  const boardTilesRef = useRef<BoardTile[]>(DEFAULT_TILES);
  const progressSummaryRef = useRef("Ready to run the tycoon crisis simulation.");
  const pendingProgressRef = useRef<{ tick?: number; maxTicks?: number; summary?: string } | null>(null);
  const pendingTimelineRowsRef = useRef<TimelineEvent[]>([]);
  const pendingWorldStateRef = useRef<Record<string, unknown> | null>(null);
  const streamFlushFrameRef = useRef<number | null>(null);
  const pulseTimersRef = useRef<number[]>([]);
  const shakeTimerRef = useRef<number | null>(null);
  const boardDragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
  } | null>(null);

  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
      pulseTimersRef.current.forEach((timer) => window.clearTimeout(timer));
      pulseTimersRef.current = [];
      if (shakeTimerRef.current !== null) window.clearTimeout(shakeTimerRef.current);
      if (streamFlushFrameRef.current !== null) window.cancelAnimationFrame(streamFlushFrameRef.current);
    };
  }, []);

  useEffect(() => {
    followLiveRef.current = followLive;
  }, [followLive]);

  useEffect(() => {
    tickRef.current = tick;
  }, [tick]);

  useEffect(() => {
    boardTilesRef.current = boardTiles;
  }, [boardTiles]);

  useEffect(() => {
    progressSummaryRef.current = progressSummary;
  }, [progressSummary]);

  useEffect(() => {
    if (!isReplayPlaying) return;
    const replayTicks = Object.keys(tickSnapshots)
      .map((value) => Number(value))
      .filter((value) => Number.isFinite(value));
    if (replayTicks.length === 0) return;
    const maxReplayTick = Math.max(...replayTicks);
    if (maxReplayTick <= 0) return;

    const timer = window.setInterval(() => {
      setFollowLive(false);
      setReplayTick((previousTick) => {
        const nextTick = previousTick + 1;
        if (nextTick > maxReplayTick) {
          setIsReplayPlaying(false);
          return maxReplayTick;
        }
        return nextTick;
      });
    }, 900);

    return () => window.clearInterval(timer);
  }, [isReplayPlaying, tickSnapshots]);

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? null,
    [agents, selectedAgentId],
  );
  const boardTilesById = useMemo(() => new Map(boardTiles.map((tile) => [tile.id, tile])), [boardTiles]);
  const boardEdges = useMemo(
    () =>
      BOARD_EDGES.filter((edge) => {
        return boardTilesById.has(edge.from) && boardTilesById.has(edge.to);
      }),
    [boardTilesById],
  );
  const latestTimelineMessage = timeline[0]?.message ?? "No event yet.";
  const tileActivity = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const agent of agents) {
      const tileId = nearestTileId(agent.x, agent.y, boardTiles);
      if (!tileId) continue;
      counts[tileId] = (counts[tileId] ?? 0) + 1;
    }
    return counts;
  }, [agents, boardTiles]);

  const progressPct = maxTicks > 0 ? Math.min(100, Math.round((tick / maxTicks) * 100)) : 0;
  const replayTicks = useMemo(
    () =>
      Object.keys(tickSnapshots)
        .map((value) => Number(value))
        .filter((value) => Number.isFinite(value)),
    [tickSnapshots],
  );
  const maxReplayTick = replayTicks.length > 0 ? Math.max(...replayTicks) : tick;
  const activeTick = followLive ? tick : replayTick;
  const activeSnapshot = tickSnapshots[activeTick];
  const activePhase = activeSnapshot?.phase ?? currentPhase;
  const activeKpi = activeSnapshot?.kpi ?? kpi;
  const activeScoreBreakdown = activeSnapshot?.scoreBreakdown ?? (followLive ? latestScoreBreakdown : null);
  const activeActions = useMemo(
    () => activeSnapshot?.actions ?? [...pendingActions, ...resolvedActions],
    [activeSnapshot, pendingActions, resolvedActions],
  );
  const activeSummary = activeSnapshot?.summary || progressSummary;

  const pulseTiles = (tileIds: string[]) => {
    const unique = Array.from(new Set(tileIds.filter((id) => boardTilesById.has(id))));
    if (unique.length === 0) return;
    setPulsedTileIds((prev) => Array.from(new Set([...prev, ...unique])));
    for (const tileId of unique) {
      const timer = window.setTimeout(() => {
        setPulsedTileIds((prev) => prev.filter((id) => id !== tileId));
      }, 950);
      pulseTimersRef.current.push(timer);
    }
  };

  const triggerBoardShake = () => {
    setIsBoardShaking(true);
    if (shakeTimerRef.current !== null) window.clearTimeout(shakeTimerRef.current);
    shakeTimerRef.current = window.setTimeout(() => {
      setIsBoardShaking(false);
      shakeTimerRef.current = null;
    }, 340);
  };

  const stopStream = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setRunning(false);
  };

  const resetSimulation = () => {
    stopStream();
    setError(null);
    setTick(0);
    setMaxTicks(DEFAULT_MAX_TICKS);
    setRequestedTicks(DEFAULT_MAX_TICKS);
    setProgressSummary("Ready to run the tycoon crisis simulation.");
    setAgents(BASE_AGENTS);
    setSelectedAgentId(BASE_AGENTS[0].id);
    setTimeline([]);
    setBoardTiles(DEFAULT_TILES);
    setKpi({ revenue: 0, margin: 0, sentiment: 0, churn_risk: 0 });
    setCurrentPhase(DEFAULT_PHASE);
    setPendingActions([]);
    setResolvedActions([]);
    setActiveEvent(null);
    setSocialLinks([]);
    setLatestScoreBreakdown(null);
    setTickSnapshots({});
    setReplayTick(0);
    setFollowLive(true);
    setIsReplayPlaying(false);
    pendingProgressRef.current = null;
    pendingTimelineRowsRef.current = [];
    pendingWorldStateRef.current = null;
    if (streamFlushFrameRef.current !== null) {
      window.cancelAnimationFrame(streamFlushFrameRef.current);
      streamFlushFrameRef.current = null;
    }
    setScoreSeries([]);
    setFinalReport(null);
    setShowResultCard(false);
    setShowInfoCard(false);
    setBoardScale(1);
    setBoardOffset({ x: 0, y: 0 });
    setIsBoardDragging(false);
    boardDragRef.current = null;
    setPulsedTileIds([]);
    setIsBoardShaking(false);
    setCameraFollowUntil(0);
  };

  const applyWorldState = (state: Record<string, unknown>) => {
    const stateTick = typeof state.tick === "number" ? state.tick : tickRef.current;
    if (typeof state.tick === "number") setTick(state.tick);
    if (typeof state.max_ticks === "number") setMaxTicks(state.max_ticks);
    setCurrentPhase(
      isGamePhase(state.phase) ? (state.phase as GamePhase) : DEFAULT_PHASE,
    );
    const nextPendingActions = mapActionRecords(state.pending_actions);
    const nextResolvedActions = mapActionRecords(state.resolved_actions);
    setPendingActions(nextPendingActions);
    setResolvedActions(nextResolvedActions);
    setActiveEvent(mapActiveEvent(state.active_event));
    setSocialLinks(mapSocialLinks(state.social_links));
    const nextScoreBreakdown = mapTickScoreBreakdown(state.latest_score_breakdown);
    setLatestScoreBreakdown(nextScoreBreakdown);

    const currentKpi = {
      revenue: 0,
      margin: 0,
      sentiment: 0,
      churn_risk: 0,
    };
    if (state.kpi && typeof state.kpi === "object") {
      const k = state.kpi as Record<string, unknown>;
      currentKpi.revenue = asNumber(k.revenue, 0);
      currentKpi.margin = asNumber(k.margin, 0);
      currentKpi.sentiment = asNumber(k.sentiment, 0);
      currentKpi.churn_risk = asNumber(k.churn_risk, 0);
    }
    setKpi(currentKpi);
    if (followLiveRef.current) setReplayTick(stateTick);

    let effectiveTiles = boardTilesRef.current;
    if (state.map && typeof state.map === "object") {
      const mapState = state.map as Record<string, unknown>;
      effectiveTiles = mapBoardTiles(mapState.zones, boardTilesRef.current);
      setBoardTiles(effectiveTiles);
    }

    const scores = asScoreMap(state.scores);
    const positions = asScoreMap(state.positions);
    setAgents((prev) => {
      const next = mapWorldAgents(state.agents, prev);
      const withPersonaProfiles = applyPersonaProfiles(state.personas, next);
      const withScores = withPersonaProfiles.map((agent) => {
        const tileIndex = Math.max(0, Math.round(asNumber(positions[agent.id], 0)));
        const tile = effectiveTiles.length > 0 ? effectiveTiles[tileIndex % effectiveTiles.length] : null;
        return {
          ...agent,
          x: tile ? tile.x : agent.x,
          y: tile ? tile.y : agent.y,
          score: scores[agent.id] ?? agent.score,
        };
      });
      const activeTileIds = withScores
        .filter((agent) => agent.status === "acting" || agent.status === "thinking")
        .map((agent) => nearestTileId(agent.x, agent.y, effectiveTiles))
        .filter((tileId): tileId is string => Boolean(tileId));
      pulseTiles(activeTileIds);
      return withScores.length > 0 ? withScores : prev;
    });

    if (Object.keys(scores).length > 0 && stateTick > 0) {
      setScoreSeries((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.tick === stateTick) {
          const merged = { ...last, ...scores };
          return [...prev.slice(0, -1), merged];
        }
        return [...prev, { tick: stateTick, ...scores }].slice(-180);
      });
    }

    const phaseValue = isGamePhase(state.phase) ? (state.phase as GamePhase) : DEFAULT_PHASE;
    const combinedActions = [...nextPendingActions, ...nextResolvedActions];
    setTickSnapshots((prev) => ({
      ...prev,
      [stateTick]: {
        tick: stateTick,
        phase: phaseValue,
        summary: progressSummaryRef.current || `Day ${stateTick}`,
        kpi: currentKpi,
        actions: combinedActions,
        scoreBreakdown: nextScoreBreakdown,
      },
    }));
  };

  const flushPendingStream = () => {
    streamFlushFrameRef.current = null;

    const progress = pendingProgressRef.current;
    pendingProgressRef.current = null;
    if (progress) {
      if (typeof progress.tick === "number") {
        setTick(progress.tick);
        if (followLiveRef.current) setReplayTick(progress.tick);
      }
      if (typeof progress.maxTicks === "number") setMaxTicks(progress.maxTicks);
      if (typeof progress.summary === "string") setProgressSummary(progress.summary);
      if (typeof progress.tick === "number") {
        const progressTick = progress.tick;
        const progressSummaryText = typeof progress.summary === "string" ? progress.summary : "";
        setTickSnapshots((prev) => {
          const existing = prev[progressTick];
          return {
            ...prev,
            [progressTick]: {
              tick: progressTick,
              phase: existing?.phase ?? DEFAULT_PHASE,
              summary: progressSummaryText || existing?.summary || "",
              kpi: existing?.kpi ?? { revenue: 0, margin: 0, sentiment: 0, churn_risk: 0 },
              actions: existing?.actions ?? [],
              scoreBreakdown: existing?.scoreBreakdown ?? null,
            },
          };
        });
      }
    }

    const timelineRows = pendingTimelineRowsRef.current;
    pendingTimelineRowsRef.current = [];
    if (timelineRows.length > 0) {
      const ordered = [...timelineRows].reverse();
      setTimeline((prev) => [...ordered, ...prev].slice(0, 160));
      const pulseSet = new Set<string>();
      let shouldShake = false;
      for (const row of timelineRows) {
        inferTilesFromMessage(row.message, boardTilesRef.current).forEach((id) => pulseSet.add(id));
        if (isShockMessage(row.message)) shouldShake = true;
      }
      if (pulseSet.size > 0) pulseTiles([...pulseSet]);
      if (shouldShake) triggerBoardShake();
    }

    const worldState = pendingWorldStateRef.current;
    pendingWorldStateRef.current = null;
    if (worldState) applyWorldState(worldState);
  };

  const scheduleStreamFlush = () => {
    if (streamFlushFrameRef.current !== null) return;
    streamFlushFrameRef.current = window.requestAnimationFrame(flushPendingStream);
  };

  const handleEvent = (event: DeepSimulatorStreamEvent) => {
    if (event.type === "status") {
      if (typeof event.max_ticks === "number") setMaxTicks(event.max_ticks);
      if (typeof event.message === "string") setProgressSummary(event.message);
      return;
    }

    if (event.type === "progress") {
      pendingProgressRef.current = {
        tick: typeof event.tick === "number" ? event.tick : pendingProgressRef.current?.tick,
        maxTicks: typeof event.max_ticks === "number" ? event.max_ticks : pendingProgressRef.current?.maxTicks,
        summary: typeof event.summary === "string" ? event.summary : pendingProgressRef.current?.summary,
      };
      scheduleStreamFlush();
      return;
    }

    if (event.type === "timeline") {
      if (typeof event.tick !== "number" || typeof event.message !== "string") return;
      pendingTimelineRowsRef.current.push({
        id: `${event.tick}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        tick: event.tick,
        message: event.message,
      });
      scheduleStreamFlush();
      return;
    }

    if (event.type === "world") {
      if (!event.state || typeof event.state !== "object") return;
      pendingWorldStateRef.current = event.state as Record<string, unknown>;
      scheduleStreamFlush();
      return;
    }

    if (event.type === "final") {
      setCurrentPhase("complete");
      if (event.response && typeof event.response === "object") {
        const response = event.response as Record<string, unknown>;
        const summary = typeof response.summary === "string" ? response.summary : "Simulation completed.";
        const recommendation = typeof response.recommendation === "string" ? response.recommendation : "";
        const confidence = asNumber(response.confidence, 0.6);
        const keyTurningPoints = Array.isArray(response.key_turning_points)
          ? response.key_turning_points.filter((item): item is string => typeof item === "string")
          : [];
        const personaObservations = Array.isArray(response.persona_observations)
          ? response.persona_observations.filter(
              (item): item is NonNullable<FinalReport["persona_observations"]>[number] =>
                !!item && typeof item === "object" && typeof (item as Record<string, unknown>).persona_id === "string",
            )
          : [];
        const htmlSlides = typeof response.html_slides === "string" ? response.html_slides : "";
        setFinalReport({
          summary,
          recommendation,
          confidence,
          key_turning_points: keyTurningPoints,
          persona_observations: personaObservations,
          html_slides: htmlSlides,
        });
        setProgressSummary(summary);
      }
      setAgents((prev) => prev.map((agent) => ({ ...agent, status: "done" })));
      return;
    }

    if (event.type === "error") {
      setError(event.error ?? "Deep simulation stream failed.");
      setRunning(false);
      return;
    }

    if (event.type === "done") {
      setRunning(false);
    }
  };

  const startSimulation = async () => {
    if (running || !query.trim()) return;
    setError(null);
    setTick(0);
    setMaxTicks(requestedTicks);
    setProgressSummary("Setting up dynamic districts and crisis deck...");
    setAgents(BASE_AGENTS.map((agent) => ({ ...agent, transcript: "", toolCalls: [], status: "idle", score: 0 })));
    setTimeline([]);
    setKpi({ revenue: 0, margin: 0, sentiment: 0, churn_risk: 0 });
    setCurrentPhase(DEFAULT_PHASE);
    setPendingActions([]);
    setResolvedActions([]);
    setActiveEvent(null);
    setSocialLinks([]);
    setLatestScoreBreakdown(null);
    setTickSnapshots({});
    setReplayTick(0);
    setFollowLive(true);
    setIsReplayPlaying(false);
    pendingProgressRef.current = null;
    pendingTimelineRowsRef.current = [];
    pendingWorldStateRef.current = null;
    if (streamFlushFrameRef.current !== null) {
      window.cancelAnimationFrame(streamFlushFrameRef.current);
      streamFlushFrameRef.current = null;
    }
    setScoreSeries([]);
    setFinalReport(null);
    setShowResultCard(false);
    setShowInfoCard(false);
    setBoardScale(1);
    setBoardOffset({ x: 0, y: 0 });
    setIsBoardDragging(false);
    boardDragRef.current = null;
    setRunning(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamDeepSimulator(
        { query: query.trim(), max_ticks: requestedTicks, scenario_id: "pricing_war_v1" },
        { onEvent: handleEvent, signal: controller.signal },
      );
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        const message = err instanceof Error ? err.message : "Failed to stream deep simulation.";
        setError(message);
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setRunning(false);
    }
  };

  useEffect(() => {
    if (!selectedAgent && agents.length > 0) {
      setSelectedAgentId(agents[0].id);
    }
  }, [agents, selectedAgent]);

  useEffect(() => {
    if (!running || isBoardDragging || Date.now() > cameraFollowUntil) return;
    const focus =
      agents.find((agent) => agent.status === "acting") ??
      agents.find((agent) => agent.status === "thinking") ??
      selectedAgent;
    if (!focus) return;
    const target = {
      x: clamp((50 - focus.x) * 1.15, -145, 145),
      y: clamp((50 - focus.y) * 0.9, -105, 105),
    };
    setBoardOffset((prev) => {
      const dx = Math.abs(prev.x - target.x);
      const dy = Math.abs(prev.y - target.y);
      if (dx < 0.8 && dy < 0.8) return prev;
      return {
        x: Number((prev.x + (target.x - prev.x) * 0.38).toFixed(2)),
        y: Number((prev.y + (target.y - prev.y) * 0.38).toFixed(2)),
      };
    });
  }, [agents, cameraFollowUntil, isBoardDragging, running, selectedAgent]);

  const sortedAgents = useMemo(() => [...agents].sort((a, b) => b.score - a.score), [agents]);
  const agentById = useMemo(() => new Map(agents.map((agent) => [agent.id, agent])), [agents]);
  const relationshipEdges = useMemo(() => {
    const dedupe = new Set<string>();
    const edges: Array<{ from: AgentCard; to: AgentCard; trust: number }> = [];
    for (const link of socialLinks) {
      if (Math.abs(link.trust) < 0.08) continue;
      const from = agentById.get(link.source_persona_id);
      const to = agentById.get(link.target_persona_id);
      if (!from || !to) continue;
      const a = from.id < to.id ? from.id : to.id;
      const b = from.id < to.id ? to.id : from.id;
      const key = `${a}:${b}`;
      if (dedupe.has(key)) continue;
      dedupe.add(key);
      const mirror = socialLinks.find(
        (item) => item.source_persona_id === link.target_persona_id && item.target_persona_id === link.source_persona_id,
      );
      const trust = mirror ? (link.trust + mirror.trust) / 2 : link.trust;
      edges.push({ from, to, trust });
    }
    return edges.slice(0, 18);
  }, [agentById, socialLinks]);
  const selectedScoreBreakdown = useMemo(() => {
    if (!selectedAgent || !activeScoreBreakdown) return null;
    return activeScoreBreakdown.personas.find((item) => item.persona_id === selectedAgent.id) ?? null;
  }, [activeScoreBreakdown, selectedAgent]);
  const topScoreBreakdown = useMemo(() => {
    if (!activeScoreBreakdown) return [];
    return [...activeScoreBreakdown.personas].sort((a, b) => b.total_delta - a.total_delta).slice(0, 3);
  }, [activeScoreBreakdown]);
  const actionQueue = useMemo(
    () => [...activeActions].sort((a, b) => (b.tick - a.tick) || a.status.localeCompare(b.status)).slice(0, 12),
    [activeActions],
  );
  const actionByPersona = useMemo(() => {
    const map = new Map<string, ActionRecord>();
    for (const action of actionQueue) {
      if (!map.has(action.persona_id)) {
        map.set(action.persona_id, action);
      }
    }
    return map;
  }, [actionQueue]);
  const relationshipEdgeLines = useMemo(
    () =>
      relationshipEdges.map((edge, idx) => {
        const stroke = edge.trust >= 0 ? "hsl(148 55% 38% / 0.72)" : "hsl(2 70% 44% / 0.72)";
        const width = 1.2 + Math.min(1.8, Math.abs(edge.trust) * 2.2);
        return (
          <line
            key={`rel-${edge.from.id}-${edge.to.id}-${idx}`}
            x1={edge.from.x}
            y1={edge.from.y}
            x2={edge.to.x}
            y2={edge.to.y}
            stroke={stroke}
            strokeWidth={width}
            strokeDasharray={edge.trust >= 0 ? undefined : "4 3"}
            strokeLinecap="round"
          />
        );
      }),
    [relationshipEdges],
  );
  const boardRouteLines = useMemo(
    () =>
      boardEdges.map((edge) => {
        const from = boardTilesById.get(edge.from);
        const to = boardTilesById.get(edge.to);
        if (!from || !to) return null;
        return (
          <g key={`${edge.from}-${edge.to}`}>
            <line
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke="hsl(var(--muted-foreground) / 0.2)"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
            <line
              className="board-edge-flow"
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke="hsl(var(--muted-foreground) / 0.68)"
              strokeWidth="0.95"
              strokeDasharray="3.1 3.1"
              strokeLinecap="round"
              markerEnd="url(#board-route-arrow)"
            />
          </g>
        );
      }),
    [boardEdges, boardTilesById],
  );
  const boardTileNodes = useMemo(
    () =>
      boardTiles.map((tile) => {
        const visual = tileVisual(tile.id);
        const TileIcon = visual.icon;
        const intensity = tileActivity[tile.id] ?? 0;
        const pulsed = pulsedTileIds.includes(tile.id);
        return (
          <div
            key={tile.id}
            className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${tile.x}%`, top: `${tile.y}%` }}
          >
            <div className="relative w-28">
              <span
                className={`pointer-events-none absolute left-1/2 top-[48%] h-16 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full blur-xl ${pulsed ? "tile-ping" : ""}`}
                style={{
                  backgroundColor: visual.glowColor,
                  opacity: pulsed ? 0.95 : Math.min(0.54, 0.2 + intensity * 0.12),
                }}
              />
              <span
                className="pointer-events-none absolute left-1/2 top-[48%] h-20 w-20 -translate-x-1/2 -translate-y-1/2 rounded-full border border-border/45"
                style={{
                  boxShadow: intensity > 0 ? `0 0 0 1px ${visual.glowColor}, 0 0 24px ${visual.glowColor}` : undefined,
                  opacity: intensity > 0 ? Math.min(0.88, 0.36 + intensity * 0.18) : 0,
                }}
              />
              <div className="relative mx-auto mb-1 flex h-12 w-12 items-center justify-center overflow-hidden rounded-xl border border-border/90 bg-card/95 shadow-[0_7px_14px_rgba(0,0,0,0.18)]">
                <div className={`absolute inset-x-0 top-0 h-1 ${visual.accentClass}`} />
                <TileIcon className={`relative h-5 w-5 ${visual.iconClass}`} />
              </div>
              <div className="rounded-md border border-border/80 bg-card px-2 py-1.5 text-card-foreground shadow-sm">
                <p className="line-clamp-1 text-center text-[10px] font-semibold uppercase tracking-[0.08em] text-foreground">
                  {tile.name}
                </p>
                <div className="mt-1 flex items-center justify-center gap-1">
                  <span className={`rounded-full border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.06em] ${visual.effectToneClass}`}>
                    {zoneSummary(tile.id)}
                  </span>
                </div>
                <div className="mt-1.5 flex gap-0.5">
                  {Array.from({ length: visual.blocks }).map((_, idx) => (
                    <span
                      key={`${tile.id}-b-${idx}`}
                      className="h-1.5 flex-1 rounded-[2px] border border-border/70 bg-muted"
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        );
      }),
    [boardTiles, tileActivity, pulsedTileIds],
  );
  const boardAgentNodes = useMemo(
    () =>
      agents.map((agent) => {
        const isSelected = agent.id === selectedAgentId;
        const tokenMotionClass = boardTokenTone(agent.status);
        return (
          <button
            key={agent.id}
            type="button"
            onClick={() => setSelectedAgentId(agent.id)}
            className="absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${agent.x}%`, top: `${agent.y}%` }}
            title={`${agent.name}: ${boardStatusBubble(agent)}`}
          >
            <span
              className={`inline-flex rounded-full border-2 bg-card/95 p-0.5 shadow-lg ${tokenMotionClass} ${isSelected ? "ring-2 ring-primary/70" : ""}`}
              style={{ borderColor: agent.color }}
            >
              <PersonaAvatar personaId={agent.id} name={agent.name} size={28} />
            </span>
            <span
              className="pointer-events-none absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md border border-border bg-card px-1.5 py-0.5 text-[9px] font-medium text-foreground shadow-sm"
              style={{ borderColor: `${agent.color}66` }}
            >
              {boardStatusBubble(agent)}
            </span>
          </button>
        );
      }),
    [agents, selectedAgentId],
  );

  const adjustBoardScale = (delta: number) => {
    setBoardScale((prev) => clamp(Number((prev + delta).toFixed(2)), 0.8, 1.9));
  };

  const resetBoardViewport = () => {
    setBoardScale(1);
    setBoardOffset({ x: 0, y: 0 });
    setIsBoardDragging(false);
    boardDragRef.current = null;
  };

  const onBoardWheel = (event: WheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    adjustBoardScale(event.deltaY < 0 ? 0.08 : -0.08);
  };

  const onBoardPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    boardDragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: boardOffset.x,
      originY: boardOffset.y,
    };
    setIsBoardDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onBoardPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const drag = boardDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const x = clamp(drag.originX + event.clientX - drag.startX, -190, 190);
    const y = clamp(drag.originY + event.clientY - drag.startY, -130, 130);
    setBoardOffset({ x, y });
  };

  const onBoardPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (boardDragRef.current?.pointerId === event.pointerId) {
      boardDragRef.current = null;
      setIsBoardDragging(false);
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const exportFinalHtml = () => {
    if (!finalReport?.html_slides) return;
    const blob = new Blob([finalReport.html_slides], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `deep-simulation-report-day-${tick || maxTicks}.html`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="w-full text-foreground">
      <div className="border-b border-border/70 px-5 py-3 md:px-8">
        <div className="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div className="h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${progressPct}%` }} />
        </div>
        <p className="text-[11px] font-light tracking-[0.08em] text-muted-foreground">
          Day {activeTick}/{maxTicks} | {activeSummary}
        </p>
      </div>

      <div className="grid min-h-[calc(100vh-10.8rem)] gap-4 px-5 py-5 md:px-8 lg:grid-cols-[minmax(320px,1.2fr)_minmax(540px,1.5fr)_minmax(320px,1.2fr)]">
        <aside className="flex min-h-0 min-w-0 flex-col overflow-y-auto rounded-2xl border border-border bg-card/85 p-4 sim-scroll">
          <div className="mb-3 flex flex-col gap-2">
            <Textarea
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              rows={2}
              className="min-h-[3.1rem] resize-none border-border bg-background/80 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground"
              placeholder="Ask a deep simulation question..."
            />
            <div className="grid grid-cols-[1fr_auto] items-center gap-2 rounded-xl border border-border bg-background/70 px-2 py-2">
              <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Ticks Before End</p>
              <Input
                type="number"
                min={RUN_TICK_MIN}
                max={RUN_TICK_MAX}
                step={1}
                value={requestedTicks}
                onChange={(event) => {
                  const next = Number(event.target.value);
                  if (!Number.isFinite(next)) return;
                  const bounded = Math.max(RUN_TICK_MIN, Math.min(RUN_TICK_MAX, Math.floor(next)));
                  setRequestedTicks(bounded);
                }}
                className="h-8 w-24 border-border bg-background text-right text-sm"
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={startSimulation} disabled={running} className="h-9 border border-primary/35 bg-primary px-3 text-primary-foreground hover:bg-primary/90">
                <Play className="mr-1.5 h-3.5 w-3.5" /> Start
              </Button>
              <Button onClick={stopStream} disabled={!running} variant="secondary" className="h-9 px-3">
                <Pause className="mr-1.5 h-3.5 w-3.5" /> Pause
              </Button>
              <Button onClick={resetSimulation} variant="outline" className="h-9 px-3">
                <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Reset
              </Button>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <Button
                onClick={() => setShowResultCard(true)}
                disabled={!finalReport}
                variant="outline"
                className="h-9 px-3"
              >
                <FileText className="mr-1.5 h-3.5 w-3.5" /> Result
              </Button>
              <Button onClick={() => setShowInfoCard(true)} variant="outline" className="h-9 px-3">
                <Info className="mr-1.5 h-3.5 w-3.5" /> Info
              </Button>
            </div>
            <div className="rounded-xl border border-border bg-background/80 px-2 py-2">
              <p className="mb-2 text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Replay</p>
              <div className="flex flex-wrap items-center gap-1.5">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setFollowLive(false);
                    setReplayTick((prev) => Math.max(0, prev - 1));
                    setIsReplayPlaying(false);
                  }}
                  disabled={activeTick <= 0}
                  className="h-7 px-2 text-xs"
                >
                  Prev
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    if (activeTick >= maxReplayTick) {
                      setFollowLive(false);
                      setReplayTick(0);
                    }
                    setIsReplayPlaying((prev) => !prev);
                  }}
                  disabled={maxReplayTick <= 0}
                  className="h-7 px-2 text-xs"
                >
                  {isReplayPlaying ? <Pause className="mr-1 h-3 w-3" /> : <Play className="mr-1 h-3 w-3" />}
                  {isReplayPlaying ? "Pause" : "Play"}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setFollowLive(false);
                    setReplayTick((prev) => Math.min(maxReplayTick, prev + 1));
                    setIsReplayPlaying(false);
                  }}
                  disabled={activeTick >= maxReplayTick}
                  className="h-7 px-2 text-xs"
                >
                  Next
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={followLive ? "default" : "ghost"}
                  onClick={() => {
                    setFollowLive(true);
                    setReplayTick(tick);
                    setIsReplayPlaying(false);
                  }}
                  className="h-7 px-2 text-xs"
                >
                  Live
                </Button>
                <div className="flex min-w-[170px] flex-1 items-center gap-2">
                  <input
                    type="range"
                    min={0}
                    max={Math.max(maxReplayTick, 0)}
                    value={activeTick}
                    className="h-2 min-w-0 flex-1 cursor-pointer accent-primary"
                    onChange={(event) => {
                      setFollowLive(false);
                      setIsReplayPlaying(false);
                      setReplayTick(Number(event.target.value));
                    }}
                  />
                </div>
                <span className="text-[11px] font-semibold text-foreground">
                  Day {activeTick} / {Math.max(maxReplayTick, tick)}
                </span>
              </div>
            </div>
            {error ? <p className="text-xs text-destructive">{error}</p> : null}
          </div>

          <div className="mb-3 grid grid-cols-2 gap-2">
            <div className="rounded-xl border border-border bg-background/80 p-2.5">
              <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Revenue</p>
              <p className="mt-1 text-sm font-semibold">{formatSigned(activeKpi.revenue)}%</p>
            </div>
            <div className="rounded-xl border border-border bg-background/80 p-2.5">
              <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Margin</p>
              <p className="mt-1 text-sm font-semibold">{formatSigned(activeKpi.margin)}%</p>
            </div>
            <div className="rounded-xl border border-border bg-background/80 p-2.5">
              <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Brand Trust</p>
              <p className="mt-1 text-sm font-semibold">{formatSigned(activeKpi.sentiment)}</p>
            </div>
            <div className="rounded-xl border border-border bg-background/80 p-2.5">
              <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Churn Risk</p>
              <p className="mt-1 text-sm font-semibold">{formatSigned(activeKpi.churn_risk)}</p>
            </div>
          </div>

          <div className="mb-3 h-56 rounded-xl border border-border bg-background/80 p-2.5">
            <div className="mb-1.5 flex items-center justify-between">
              <p className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Strategist Score Lines</p>
              <TrendingUp className="h-3.5 w-3.5 text-muted-foreground" />
            </div>
            <div className="mb-2 flex flex-wrap gap-1.5">
              {sortedAgents.map((agent) => (
                <span
                  key={`legend-${agent.id}`}
                  className="inline-flex items-center gap-1 rounded-full border border-border bg-card/80 px-1.5 py-0.5 text-[10px] text-foreground"
                >
                  <PersonaAvatar personaId={agent.id} name={agent.name} size={16} />
                  <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: agent.color }} />
                  {agent.name}
                </span>
              ))}
            </div>
            <ResponsiveContainer width="100%" height="74%">
              <LineChart data={scoreSeries} margin={{ top: 4, right: 8, bottom: 6, left: -16 }}>
                <XAxis dataKey="tick" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} width={30} />
                <Tooltip
                  contentStyle={{
                    borderRadius: 12,
                    border: "1px solid hsl(var(--border))",
                    background: "hsl(var(--card))",
                    fontSize: 11,
                  }}
                />
                {sortedAgents.map((agent) => (
                  <Line
                    key={`line-${agent.id}`}
                    type="monotone"
                    dataKey={agent.id}
                    stroke={agent.color}
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="rounded-xl border border-border bg-background/85 p-2.5">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Why Score Changed</p>
              <span className="text-[10px] text-muted-foreground">
                {activeScoreBreakdown ? `Day ${activeScoreBreakdown.tick}` : "No tick yet"}
              </span>
            </div>
            {activeScoreBreakdown ? (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">
                  KPI Shift <span className="font-semibold text-foreground">{formatSigned(activeScoreBreakdown.kpi_shift)}</span>
                </p>
                {selectedScoreBreakdown ? (
                  <div className="rounded-lg border border-border bg-card/85 p-2">
                    <p className="text-xs font-semibold text-foreground">{selectedScoreBreakdown.persona_name}</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Delta {formatSigned(selectedScoreBreakdown.total_delta)} | Score {selectedScoreBreakdown.total_score.toFixed(2)}
                    </p>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      KPI {formatSigned(selectedScoreBreakdown.kpi_contribution_points)} | Timing {formatSigned(selectedScoreBreakdown.timing_points)} | Resource {formatSigned(selectedScoreBreakdown.resource_efficiency_points)} | Social {formatSigned(selectedScoreBreakdown.social_influence_points)}
                    </p>
                  </div>
                ) : null}
                <div className="space-y-1">
                  {topScoreBreakdown.map((row) => (
                    <div key={`score-delta-${row.persona_id}`} className="flex items-center justify-between rounded-md border border-border bg-card/80 px-2 py-1 text-xs">
                      <span className="text-foreground">{row.persona_name}</span>
                      <span className={row.total_delta >= 0 ? "text-emerald-700" : "text-red-700"}>
                        {formatSigned(row.total_delta)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Run a simulation tick to view deterministic score breakdown.</p>
            )}
          </div>

        </aside>

        <main className="relative flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-[24px] border border-border/75 bg-[linear-gradient(160deg,hsl(var(--card)/0.94),hsl(var(--background)/0.92))] p-4 shadow-[0_12px_28px_rgba(15,23,42,0.1)]">
          <div className="pointer-events-none absolute inset-0 opacity-60 [background-image:radial-gradient(circle_at_15%_18%,rgba(233,119,46,0.08),transparent_32%),radial-gradient(circle_at_82%_85%,rgba(26,160,145,0.09),transparent_32%)]" />
          <div className="relative z-10 mb-3 flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-background/80 px-3 py-2">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Business World</p>
              <p className="text-sm text-muted-foreground">Canonical board state driven by the simulation engine.</p>
            </div>
            <Badge className="border border-primary/50 bg-primary/12 px-2.5 py-1 text-foreground shadow-sm">
              <Sparkles className="mr-1 h-3 w-3" /> {phaseLabel(activePhase)}
            </Badge>
          </div>

          <div className="relative z-10 mb-3 grid gap-2 rounded-xl border border-border/80 bg-background/88 p-2.5 shadow-[inset_0_1px_0_hsl(var(--background)/0.55)] lg:grid-cols-[1.35fr_1fr]">
            <div>
              <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Turn Loop</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {PHASE_ORDER.map((phase, idx) => {
                  const active = phase === activePhase;
                  const complete = PHASE_ORDER.indexOf(phase) < PHASE_ORDER.indexOf(activePhase);
                  return (
                    <div
                      key={phase}
                      className={`min-w-[102px] flex-1 rounded-lg border px-2 py-2 text-[11px] transition-all duration-200 ${
                        active
                          ? "border-primary/70 bg-primary/12 text-foreground shadow-[0_0_0_1px_hsl(var(--primary)/0.15)]"
                          : complete
                            ? "border-emerald-300/70 bg-emerald-50/80 text-emerald-900"
                            : "border-border/80 bg-card/95 text-foreground/80"
                      }`}
                    >
                      <p className="inline-flex items-center gap-1.5 font-semibold uppercase tracking-[0.05em]">
                        <span className={`inline-flex h-4 w-4 items-center justify-center rounded-full border text-[9px] ${active ? "border-primary/55 bg-primary/15" : "border-border/75 bg-background/85"}`}>
                          {idx + 1}
                        </span>
                        {phaseLabel(phase)}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="rounded-lg border border-border/85 bg-card/92 px-3 py-2.5 shadow-sm">
              <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Current Phase</p>
              <p className="mt-1 text-sm font-semibold text-foreground">{phaseLabel(activePhase)}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{phaseDescription(activePhase)}</p>
            </div>
          </div>

          <div className={`relative z-10 mb-4 h-[352px] flex-none overflow-hidden rounded-2xl border border-border/80 bg-[radial-gradient(circle_at_15%_10%,rgba(233,119,46,0.24),transparent_34%),radial-gradient(circle_at_88%_88%,rgba(22,154,142,0.2),transparent_36%),linear-gradient(180deg,hsl(var(--background)),hsl(var(--muted)))] shadow-[0_12px_25px_rgba(0,0,0,0.12)] ${isBoardShaking ? "board-shake" : ""}`}>
            {activeEvent ? (
              <div className="absolute left-3 top-3 z-20 max-w-[54%] rounded-lg border border-red-300/70 bg-card/95 px-3 py-2 text-card-foreground shadow-md backdrop-blur-sm">
                <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Active Event</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{activeEvent.title}</p>
                {activeEvent.summary ? <p className="mt-1 text-xs text-muted-foreground">{activeEvent.summary}</p> : null}
                <div className="mt-2 flex flex-wrap gap-1">
                  {Object.entries(activeEvent.effects).map(([key, value]) => (
                    <span key={key} className="rounded-full border border-border bg-background px-2 py-0.5 text-[10px] text-foreground">
                      {key.replaceAll("_", " ")} {formatSigned(value)}
                    </span>
                  ))}
                  {activeEvent.matched_actions.map((action) => (
                    <span key={action} className="rounded-full border border-emerald-300/70 bg-emerald-50 px-2 py-0.5 text-[10px] text-emerald-800">
                      Countered by {action.replaceAll("_", " ")}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="absolute right-3 top-3 z-20 inline-flex items-center gap-1 rounded-lg border border-border/85 bg-card/96 p-1 text-card-foreground shadow-md backdrop-blur-sm">
              <Button type="button" variant="outline" className="h-7 px-2 text-xs" onClick={() => adjustBoardScale(-0.08)}>
                -
              </Button>
              <p className="w-12 text-center text-[11px] font-medium tabular-nums text-muted-foreground">{Math.round(boardScale * 100)}%</p>
              <Button type="button" variant="outline" className="h-7 px-2 text-xs" onClick={() => adjustBoardScale(0.08)}>
                +
              </Button>
              <Button type="button" variant="outline" className="h-7 px-2 text-[10px]" onClick={resetBoardViewport}>
                Reset View
              </Button>
            </div>

            <div className="pointer-events-none absolute inset-0 opacity-20 [background-image:linear-gradient(to_right,rgba(28,28,28,0.1)_1px,transparent_1px),linear-gradient(to_bottom,rgba(28,28,28,0.1)_1px,transparent_1px)] [background-size:26px_26px]" />
            <div className="pointer-events-none absolute inset-2 rounded-xl border border-border/60 shadow-inner" />
            <div className="pointer-events-none absolute inset-[6%] rounded-[24px] border border-border/40 bg-[linear-gradient(165deg,hsl(var(--background)/0.65),hsl(var(--muted)/0.35))]" />
            <div className="pointer-events-none absolute inset-[8.5%] rounded-[20px] border border-white/45 bg-[radial-gradient(circle_at_50%_45%,hsl(var(--card)/0.58),hsl(var(--card)/0.12))]" />

            <div
              className={`relative h-full w-full touch-none ${isBoardDragging ? "cursor-grabbing" : "cursor-grab"}`}
              onWheel={onBoardWheel}
              onPointerDown={onBoardPointerDown}
              onPointerMove={onBoardPointerMove}
              onPointerUp={onBoardPointerUp}
              onPointerCancel={onBoardPointerUp}
            >
                <div
                  className="absolute inset-x-0 bottom-0 top-10 origin-center"
                  style={{
                    transform: `translate(${boardOffset.x}px, ${boardOffset.y}px) scale(${boardScale})`,
                    transition: "none",
                  }}
                >
                <div className="pointer-events-none absolute left-1/2 top-1/2 h-[73%] w-[86%] -translate-x-1/2 -translate-y-1/2 rounded-[28px] border border-border/55 bg-[linear-gradient(180deg,hsl(var(--background)/0.4),hsl(var(--muted)/0.24))]" />
                <div className="pointer-events-none absolute left-1/2 top-1/2 h-[63%] w-[74%] -translate-x-1/2 -translate-y-1/2 rounded-[999px] border border-primary/25 bg-primary/5" />

                <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                  <defs>
                    <marker id="board-route-arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4.3" markerHeight="4.3" orient="auto-start-reverse">
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="hsl(var(--muted-foreground) / 0.72)" />
                    </marker>
                  </defs>
                  {relationshipEdgeLines}
                  {boardRouteLines}
                </svg>

                {boardTileNodes}

                <div className="pointer-events-none absolute inset-0 rounded-[18px] border border-white/35" />

                {boardAgentNodes}
              </div>
            </div>

            <div className="pointer-events-none absolute bottom-3 left-3 max-w-[76%] rounded-md border border-border/90 bg-card/96 px-2.5 py-1.5 text-card-foreground shadow-sm backdrop-blur-sm">
              <p className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">Latest Event</p>
              <p className="line-clamp-1 text-xs text-foreground">{latestTimelineMessage}</p>
            </div>
          </div>

          <div className="relative z-10 grid min-h-0 min-w-0 flex-1 gap-3">
            <div className="min-h-0 overflow-y-auto rounded-xl border border-border/80 bg-background/95 p-3 shadow-sm sim-scroll">
              <div className="mb-3 flex items-center justify-between rounded-lg border border-border/70 bg-card/80 px-2.5 py-2">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Tick Feed</p>
                  <p className="text-xs text-muted-foreground">Summary, action, and points for Day {activeTick}.</p>
                </div>
                <Badge className="border border-border bg-card text-foreground">{actionQueue.length}</Badge>
              </div>
              <div className="space-y-2">
                {actionQueue.length === 0 ? <p className="text-sm text-muted-foreground">No action records for this day yet.</p> : null}
                {actionQueue.map((action, idx) => (
                  <div key={`${action.persona_id}-${action.tick}-${action.action_type}-${idx}`} className="rounded-xl border border-border/80 bg-card/90 p-3 shadow-sm">
                    {(() => {
                      const points = activeScoreBreakdown?.personas.find((row) => row.persona_id === action.persona_id);
                      return (
                        <>
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-foreground">{action.persona_name}</p>
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${actionStatusTone(action.status)}`}>
                        {action.status}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Day {action.tick} | {phaseLabel(action.phase)} | {action.action_type.replaceAll("_", " ")}
                    </p>
                    <p className="mt-2 text-sm text-foreground">{action.summary}</p>
                    {points ? (
                      <p className="mt-1 text-[11px] text-muted-foreground">
                        Points {formatSigned(points.total_delta)} | Total {points.total_score.toFixed(2)}
                      </p>
                    ) : null}
                    {action.target_zone_id ? (
                      <p className="mt-1 text-[11px] text-muted-foreground">Zone: {boardTilesById.get(action.target_zone_id)?.name ?? action.target_zone_id}</p>
                    ) : null}
                    {action.outcome ? <p className="mt-2 text-xs text-muted-foreground">{action.outcome}</p> : null}
                        </>
                      );
                    })()}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>

        <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-2xl border border-border bg-card/85 p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Strategist Swarm</p>
            <Badge className="border border-border bg-secondary text-secondary-foreground">{agents.length}</Badge>
          </div>

          <div className="mb-3 rounded-xl border border-border bg-background/80 p-2.5">
            <p className="text-[11px] uppercase tracking-[0.13em] text-muted-foreground">Scoreboard</p>
            <div className="mt-2 space-y-1.5">
              {sortedAgents.map((agent, idx) => (
                <div key={`rank-${agent.id}`} className="flex items-center justify-between gap-2 rounded-md border border-border bg-card/85 px-2 py-1.5 text-xs">
                  <span className="inline-flex min-w-0 items-center gap-1.5 text-foreground">
                    <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-muted text-[10px]">{idx + 1}</span>
                    <PersonaAvatar personaId={agent.id} name={agent.name} size={18} />
                    <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: agent.color }} />
                    <span className="truncate">{agent.name}</span>
                  </span>
                  <span className="font-semibold" style={{ color: agent.color }}>{agent.score.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto pr-1 sim-scroll">
            <div className="space-y-2">
              {agents.map((agent) => {
                const selected = selectedAgentId === agent.id;
                const action = actionByPersona.get(agent.id);
                const points = activeScoreBreakdown?.personas.find((row) => row.persona_id === agent.id);
                return (
                  <button
                    key={agent.id}
                    type="button"
                    onClick={() => setSelectedAgentId(agent.id)}
                    className={`w-full rounded-xl border p-3 text-left transition ${selected ? "bg-card shadow-[0_0_0_1px_hsl(var(--primary)/0.25)]" : "bg-card/80 hover:border-primary/40 hover:bg-card"}`}
                    style={{ borderColor: selected ? agent.color : undefined }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="inline-flex items-center gap-2 text-sm font-semibold">
                        <PersonaAvatar personaId={agent.id} name={agent.name} size={18} />
                        <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: agent.color }} />
                        {agent.name}
                      </p>
                      <Badge className={statusBadgeTone(agent.status)}>
                        {agent.status === "done" ? <CheckCircle2 className="mr-1 h-3 w-3" /> : null}
                        {humanStatus(agent.status)}
                      </Badge>
                    </div>
                    <p className="mt-1 text-[11px] text-muted-foreground">Confidence {Math.round(agent.confidence * 100)}% | Score {agent.score.toFixed(2)}</p>
                    {agent.objective ? <p className="mt-1 text-[11px] text-muted-foreground">{agent.objective}</p> : null}
                    <p className="mt-2 rounded-md border border-border bg-background/80 px-2 py-1.5 text-[11px] text-muted-foreground">
                      Action: {action ? action.action_type.replaceAll("_", " ") : "no action"}
                    </p>
                    <p className="mt-2 rounded-md border border-border bg-background/80 px-2 py-1.5 text-xs text-foreground">
                      {action?.summary || "No summary available for this day."}
                    </p>
                    {points ? (
                      <p className="mt-1 text-[11px] text-muted-foreground">
                        Points {formatSigned(points.total_delta)} | Total {points.total_score.toFixed(2)}
                      </p>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>
        </aside>
      </div>

      {showResultCard && finalReport ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-border bg-card p-4 shadow-2xl sim-scroll">
            <div className="mb-2 flex items-start justify-between gap-2">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Simulation Result</p>
                <p className="text-lg font-semibold text-foreground">Observer Final Report</p>
              </div>
              <button
                type="button"
                className="rounded-md border border-border bg-background p-1 text-muted-foreground hover:text-foreground"
                onClick={() => setShowResultCard(false)}
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mb-3 flex items-center justify-between gap-2 rounded-xl border border-border bg-background/80 px-3 py-2">
              <p className="text-sm font-semibold text-foreground">{finalReport.summary}</p>
              <Badge className="border border-primary/40 bg-primary/10 text-foreground">
                Confidence {Math.round(finalReport.confidence * 100)}%
              </Badge>
            </div>

            {finalReport.recommendation ? (
              <div className="mb-3 rounded-xl border border-border bg-background/80 p-3">
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Recommendation</p>
                <p className="mt-1 text-sm leading-relaxed text-foreground">{finalReport.recommendation}</p>
              </div>
            ) : null}

            {finalReport.key_turning_points.length > 0 ? (
              <div className="mb-3 rounded-xl border border-border bg-background/80 p-3">
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Turning Points</p>
                <ul className="mt-2 space-y-1 text-xs text-foreground">
                  {finalReport.key_turning_points.slice(0, 8).map((point, idx) => (
                    <li key={`result-turn-${idx}`} className="rounded-md border border-border bg-card px-2 py-1.5">
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {finalReport.persona_observations && finalReport.persona_observations.length > 0 ? (
              <div className="mb-3 rounded-xl border border-border bg-background/80 p-3">
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Persona Breakdown</p>
                <div className="mt-2 space-y-2">
                  {finalReport.persona_observations.slice(0, 10).map((persona) => (
                    <div key={`result-persona-${persona.persona_id}`} className="rounded-md border border-border bg-card px-2 py-2">
                      <p className="text-xs font-semibold text-foreground">
                        {persona.name} | {persona.role}
                      </p>
                      <p className="text-xs text-muted-foreground">{persona.objective}</p>
                      <p className="mt-1 text-xs text-foreground">{persona.stance}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {finalReport.html_slides ? (
              <Button variant="outline" className="h-8 px-2.5 text-xs" onClick={exportFinalHtml}>
                Export Final HTML Report
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}

      {showInfoCard ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-border bg-card p-4 shadow-2xl">
            <div className="mb-3 flex items-start justify-between gap-2">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">How The Game Works</p>
                <p className="text-lg font-semibold text-foreground">Deep Simulation Rules</p>
              </div>
              <button
                type="button"
                className="rounded-md border border-border bg-background p-1 text-muted-foreground hover:text-foreground"
                onClick={() => setShowInfoCard(false)}
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="max-h-[65vh] space-y-3 overflow-y-auto rounded-xl border border-border bg-background/80 p-3 text-sm leading-relaxed text-foreground sim-scroll">
              <div>
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Objective</p>
                <p>
                  Run a multi-day strategy simulation to test a business decision under uncertainty. The goal is not to
                  "beat" a game board, but to learn which strategy mix improves `revenue`, `margin`, and `sentiment`
                  while controlling `churn_risk`.
                </p>
              </div>

              <div>
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Setup</p>
                <p>`1 tick = 1 day` in simulation time.</p>
                <p>You choose the number of ticks before start. More ticks = deeper scenario evolution.</p>
                <p>Personas are generated dynamically by the orchestrator, based on your query and scenario context.</p>
              </div>

              <div>
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Per-Tick Flow</p>
                <p>1. Active strategists are selected for the day.</p>
                <p>2. Each active strategist rolls and moves to a district tile.</p>
                <p>3. District effects apply pressure or boosts to KPI dimensions.</p>
                <p>4. Strategists think in real time, may call tools, and may submit action intents.</p>
                <p>5. Intents are validated and conflicts resolved; accepted intents change world KPIs.</p>
                <p>6. Crisis card may trigger and create external shock (mitigated by matching actions).</p>
                <p>7. Scores update from move quality, intent confidence, and KPI contribution.</p>
              </div>

              <div>
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">KPI Rules</p>
                <p><strong>Revenue</strong>: top-line impact from pricing, demand, and campaign effects.</p>
                <p><strong>Margin</strong>: unit-economics efficiency and cost discipline.</p>
                <p><strong>Brand Trust (Sentiment)</strong>: customer perception trajectory.</p>
                <p><strong>Churn Risk</strong>: likelihood of customer loss; lower is better.</p>
                <p>
                  Good runs usually raise `revenue/margin/sentiment` while keeping `churn_risk` flat or declining.
                </p>
              </div>

              <div>
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Action & Validation Rules</p>
                <p>
                  Allowed legal actions include `move`, `talk`, `propose`, `support`, `oppose`, `price_adjust`,
                  `spend_shift`, `campaign`, `procurement`, `wait`.
                </p>
                <p>Low-quality or invalid intents can be rejected by engine constraints.</p>
                <p>When multiple intents conflict, resolver keeps the strongest compatible set.</p>
              </div>

              <div>
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Crisis Rules</p>
                <p>Crisis cards represent exogenous market shocks (competitor move, supply issue, sentiment event).</p>
                <p>
                  If strategist intents include matching counter-actions, shock impact is partially mitigated;
                  otherwise KPI downside applies at near full force.
                </p>
              </div>

              <div>
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">How To Read The UI</p>
                <p><strong>Left panel</strong>: controls, KPI snapshots, score trends.</p>
                <p><strong>Center panel</strong>: board state + per-tick strategist summaries, actions, and points.</p>
                <p><strong>Right panel</strong>: all strategist cards with confidence, score, current move, preview.</p>
                <p>
                  Board controls: wheel or +/- to zoom, drag to pan, and `Reset View` to re-center map.
                </p>
              </div>

              <div>
                <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">End Of Simulation</p>
                <p>
                  When the final tick completes, `Result` unlocks. Open it to view observer summary, turning points,
                  per-persona observations, and recommendation.
                </p>
                <p>Use export to download the final HTML slides report for presentation/replay.</p>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
