import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent, type WheelEvent } from "react";
import { Compass, Download, Network, Pause, Play, Plus, Send, Sparkles, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  chatNetworkObserver,
  downloadNetworkStoryline,
  injectNetworkShock,
  streamNetworkSimulator,
  type NetworkSimulatorStreamEvent,
} from "@/lib/simulator-client";

type NodeType = "business" | "consumer" | "supplier" | "competitor" | "community" | "bank" | "regulator" | "platform";
type EdgeType = "transaction" | "influence" | "trust" | "dependency" | "information";
type NodeStatus = "stable" | "active" | "strained" | "watch";

interface NetworkNode {
  id: string;
  label: string;
  type: NodeType;
  buildingIcon: string;
  personaIcon: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  influence: number;
  status: NodeStatus;
  lastAction: string;
}

interface NetworkEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  weight: number;
  lastTick: number;
}

interface ChatMessage {
  role: "user" | "observer";
  text: string;
}

interface NarrativeImpact {
  direction: "up" | "down" | "stable";
  note: string;
}

interface NodeNarrative {
  headline: string;
  summary_short: string;
  reason: string;
  watch_next: string;
  confidence_band: "low" | "medium" | "high";
  sales: NarrativeImpact;
  cost: NarrativeImpact;
  risk: NarrativeImpact;
  full_response_md: string;
}

interface DaySnapshot {
  day: number;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  kpis?: { revenue_delta?: number; cost_delta?: number; risk_delta?: number };
  summary?: string;
}

const NODE_TYPE_STYLE: Record<NodeType, { color: string; ring: string }> = {
  business: { color: "#e9772e", ring: "rgba(233,119,46,0.35)" },
  consumer: { color: "#2f7f73", ring: "rgba(47,127,115,0.35)" },
  supplier: { color: "#5f7d36", ring: "rgba(95,125,54,0.35)" },
  competitor: { color: "#bd4a2d", ring: "rgba(189,74,45,0.35)" },
  community: { color: "#577ea4", ring: "rgba(87,126,164,0.35)" },
  bank: { color: "#7d5aa7", ring: "rgba(125,90,167,0.35)" },
  regulator: { color: "#5b6775", ring: "rgba(91,103,117,0.35)" },
  platform: { color: "#7f6d42", ring: "rgba(127,109,66,0.35)" },
};

const EDGE_COLORS: Record<EdgeType, string> = {
  transaction: "#e08a3e",
  influence: "#4f8ec2",
  trust: "#2c9a7c",
  dependency: "#a06acc",
  information: "#c2a84f",
};

const SHOCK_CATALOG = [
  "Competitor launched emergency discount campaign",
  "Supplier lead time slipped by 2 days",
  "Community sentiment dipped after price rumor",
  "Regulator announced temporary promotion guideline review",
];

const INITIAL_QUERY = "Can I increase my price by 10% without damaging retention?";
const DEFAULT_DAYS = 16;
const BUILDING_ICON_COUNT = 60;
const PERSONA_ICON_COUNT = 49;
const BUILDING_ICON_POOL: Record<NodeType, number[]> = {
  business: [1, 3, 4, 20, 21, 24, 30, 36, 52, 54],
  consumer: [2, 6, 13, 14, 15, 18, 31, 32, 45, 46, 47, 49],
  supplier: [8, 16, 17, 25, 26, 27, 28, 29],
  competitor: [19, 20, 21, 45, 46, 53, 54],
  community: [2, 12, 23, 31, 41, 43, 44],
  bank: [5, 11, 33, 35],
  regulator: [7, 9, 10, 22, 24, 44, 50, 51],
  platform: [33, 34, 37, 38, 39, 40],
};

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function randomPick<T>(rows: T[]): T {
  return rows[Math.floor(Math.random() * rows.length)];
}

function stableHash(value: string): number {
  let hash = 0;
  for (let idx = 0; idx < value.length; idx += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(idx);
    hash |= 0;
  }
  return Math.abs(hash);
}

function buildingIconPath(index: number): string {
  return `/assets/buildings/building_${String(index + 1).padStart(2, "0")}.png`;
}

function personaIconPath(index: number): string {
  return `/assets/personas/persona_${String(index + 1).padStart(2, "0")}.png`;
}

function pickNodeIcons(nodeId: string, type: NodeType): { buildingIcon: string; personaIcon: string } {
  const nodeSeed = stableHash(nodeId);
  const pool = BUILDING_ICON_POOL[type];
  const buildingNumber =
    pool.length > 0 ? pool[nodeSeed % pool.length] : (nodeSeed % BUILDING_ICON_COUNT) + 1;
  const personaIndex = nodeSeed % PERSONA_ICON_COUNT;
  return {
    buildingIcon: buildingIconPath(buildingNumber - 1),
    personaIcon: personaIconPath(personaIndex),
  };
}

function asNodeType(value: string): NodeType {
  if (value in NODE_TYPE_STYLE) return value as NodeType;
  return "business";
}

function asEdgeType(value: string): EdgeType {
  if (value in EDGE_COLORS) return value as EdgeType;
  return "information";
}

function asNodeStatus(value: string): NodeStatus {
  if (value === "stable" || value === "active" || value === "strained" || value === "watch") return value;
  return "stable";
}

function formatNodeType(type: NodeType): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function formatDirection(value: "up" | "down" | "stable"): string {
  if (value === "up") return "up";
  if (value === "down") return "down";
  return "stable";
}

function normalizeNarrative(raw: unknown): NodeNarrative | null {
  if (!raw || typeof raw !== "object") return null;
  const source = raw as Record<string, unknown>;
  const normalizeImpact = (value: unknown): NarrativeImpact => {
    if (!value || typeof value !== "object") {
      return { direction: "stable", note: "No clear signal yet." };
    }
    const impact = value as Record<string, unknown>;
    const directionRaw = String(impact.direction ?? "stable").toLowerCase();
    const direction = directionRaw === "up" || directionRaw === "down" ? directionRaw : "stable";
    return {
      direction,
      note: String(impact.note ?? "No clear signal yet."),
    };
  };
  const confidenceRaw = String(source.confidence_band ?? "medium").toLowerCase();
  const confidence = confidenceRaw === "low" || confidenceRaw === "high" ? confidenceRaw : "medium";
  return {
    headline: String(source.headline ?? "Node update"),
    summary_short: String(source.summary_short ?? "Node responded to the current conditions."),
    reason: String(source.reason ?? "Local pressures shaped this response."),
    watch_next: String(source.watch_next ?? "Watch market response in the next turn."),
    confidence_band: confidence,
    sales: normalizeImpact(source.sales),
    cost: normalizeImpact(source.cost),
    risk: normalizeImpact(source.risk),
    full_response_md: String(source.full_response_md ?? "No detailed response was produced."),
  };
}

function buildInitialNodes(): NetworkNode[] {
  const definitions: Array<[string, string, NodeType]> = [
    ["n_business_hq", "SME HQ", "business"],
    ["n_consumer_stu", "Student Cluster", "consumer"],
    ["n_consumer_young", "Young Professional", "consumer"],
    ["n_supplier_mat", "Raw Supplier", "supplier"],
    ["n_supplier_log", "Logistics Vendor", "supplier"],
    ["n_comp_fast", "Fast Competitor", "competitor"],
    ["n_comp_prem", "Premium Competitor", "competitor"],
    ["n_bank_local", "Local Bank", "bank"],
    ["n_reg_trade", "Trade Regulator", "regulator"],
    ["n_community_campus", "Campus Community", "community"],
    ["n_platform_social", "Social Platform", "platform"],
    ["n_platform_market", "Marketplace", "platform"],
  ];

  const centerX = 420;
  const centerY = 270;
  const radius = 195;

  return definitions.map(([id, label, type], idx) => {
    const icons = pickNodeIcons(id, type);
    const angle = (idx / definitions.length) * Math.PI * 2;
    const jitterX = (Math.random() - 0.5) * 42;
    const jitterY = (Math.random() - 0.5) * 42;
    return {
      id,
      label,
      type,
      ...icons,
      x: centerX + Math.cos(angle) * radius + jitterX,
      y: centerY + Math.sin(angle) * radius + jitterY,
      vx: 0,
      vy: 0,
      influence: 0.45 + Math.random() * 0.4,
      status: "stable",
      lastAction: "waiting for scenario run",
    };
  });
}

function buildInitialEdges(): NetworkEdge[] {
  const rows: Array<[string, string, EdgeType, number]> = [
    ["n_business_hq", "n_consumer_stu", "transaction", 0.82],
    ["n_business_hq", "n_consumer_young", "transaction", 0.68],
    ["n_business_hq", "n_supplier_mat", "dependency", 0.73],
    ["n_business_hq", "n_supplier_log", "dependency", 0.66],
    ["n_business_hq", "n_platform_market", "transaction", 0.57],
    ["n_business_hq", "n_platform_social", "information", 0.52],
    ["n_comp_fast", "n_consumer_stu", "influence", 0.61],
    ["n_comp_prem", "n_consumer_young", "influence", 0.58],
    ["n_community_campus", "n_consumer_stu", "trust", 0.69],
    ["n_reg_trade", "n_business_hq", "information", 0.51],
    ["n_bank_local", "n_business_hq", "dependency", 0.46],
    ["n_platform_social", "n_community_campus", "information", 0.48],
    ["n_platform_market", "n_comp_fast", "transaction", 0.54],
  ];

  return rows.map(([source, target, type, weight], idx) => ({
    id: `edge_${idx + 1}`,
    source,
    target,
    type,
    weight,
    lastTick: 0,
  }));
}

export function NetworkSimulationSection() {
  const [query, setQuery] = useState(INITIAL_QUERY);
  const [maxDays, setMaxDays] = useState(DEFAULT_DAYS);
  const [currentDay, setCurrentDay] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [nodes, setNodes] = useState<NetworkNode[]>(() => buildInitialNodes());
  const [edges, setEdges] = useState<NetworkEdge[]>(() => buildInitialEdges());
  const [selectedNodeId, setSelectedNodeId] = useState("n_business_hq");
  const [activeDialogNodeId, setActiveDialogNodeId] = useState<string | null>(null);
  const [observerReport, setObserverReport] = useState("");
  const [observerReady, setObserverReady] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [nodeNarratives, setNodeNarratives] = useState<Record<string, NodeNarrative>>({});
  const [timelineByDay, setTimelineByDay] = useState<Record<number, DaySnapshot>>({});
  const [narrativesByDay, setNarrativesByDay] = useState<Record<number, Record<string, NodeNarrative>>>({});
  const [replayDay, setReplayDay] = useState(0);
  const [followLive, setFollowLive] = useState(true);
  const [isReplayPlaying, setIsReplayPlaying] = useState(false);

  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  const streamAbortRef = useRef<AbortController | null>(null);
  const followLiveRef = useRef(true);
  const currentDayRef = useRef(0);
  const graphViewportRef = useRef<HTMLDivElement | null>(null);
  const nodesRef = useRef<NetworkNode[]>(nodes);
  const narrativesByDayRef = useRef<Record<number, Record<string, NodeNarrative>>>({});
  const dragCanvasRef = useRef<{ active: boolean; startX: number; startY: number }>({
    active: false,
    startX: 0,
    startY: 0,
  });
  const dragNodeRef = useRef<{ nodeId: string; pointerId: number } | null>(null);

  const maxReplayDay = useMemo(() => {
    const days = Object.keys(timelineByDay).map((value) => Number(value)).filter((value) => Number.isFinite(value));
    return days.length > 0 ? Math.max(...days) : currentDay;
  }, [timelineByDay, currentDay]);
  const activeDay = followLive ? currentDay : replayDay;
  const displaySnapshot = timelineByDay[activeDay];
  const displayNodes = displaySnapshot?.nodes ?? nodes;
  const displayEdges = displaySnapshot?.edges ?? edges;
  const activeNarratives = narrativesByDay[activeDay] ?? nodeNarratives;

  const nodeMap = useMemo(() => new Map(displayNodes.map((node) => [node.id, node])), [displayNodes]);
  const selectedNode = nodeMap.get(selectedNodeId) ?? displayNodes[0];
  const dialogNode = useMemo(
    () => (activeDialogNodeId ? nodeMap.get(activeDialogNodeId) : undefined),
    [activeDialogNodeId, nodeMap],
  );
  const dialogNarrative = dialogNode ? activeNarratives[dialogNode.id] : undefined;

  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    followLiveRef.current = followLive;
  }, [followLive]);

  useEffect(() => {
    currentDayRef.current = currentDay;
  }, [currentDay]);

  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  useEffect(() => {
    narrativesByDayRef.current = narrativesByDay;
  }, [narrativesByDay]);

  useEffect(() => {
    if (!dialogNode) return;
    if (dragCanvasRef.current.active || dragNodeRef.current) return;
    const viewport = graphViewportRef.current;
    if (!viewport) return;
    const rect = viewport.getBoundingClientRect();
    const anchorX = rect.width * 0.43;
    const anchorY = rect.height * 0.5;
    setOffset({
      x: anchorX - dialogNode.x * zoom,
      y: anchorY - dialogNode.y * zoom,
    });
    setSelectedNodeId(dialogNode.id);
  }, [dialogNode, zoom]);

  useEffect(() => {
    if (!isReplayPlaying) return;
    if (maxReplayDay <= 0) return;

    const timer = window.setInterval(() => {
      setFollowLive(false);
      setReplayDay((previousDay) => {
        const nextDay = previousDay + 1;
        if (nextDay > maxReplayDay) {
          setIsReplayPlaying(false);
          return maxReplayDay;
        }
        return nextDay;
      });
    }, 900);

    return () => window.clearInterval(timer);
  }, [isReplayPlaying, maxReplayDay]);

  function applyStreamEvent(event: NetworkSimulatorStreamEvent) {
    if (event.session_id) setSessionId(event.session_id);

    if (event.type === "progress") {
      const tick = event.tick ?? 0;
      setCurrentDay(tick);
      if (followLiveRef.current) setReplayDay(tick);
      return;
    }

    if (event.type === "network_state") {
      const state = event.state as {
        nodes?: Array<Record<string, unknown>>;
        edges?: Array<Record<string, unknown>>;
        kpis?: { revenue_delta?: number; cost_delta?: number; risk_delta?: number };
        llm_context?: Record<string, unknown>;
        day_summary_ai?: string;
      } | undefined;
      const tick = event.tick ?? 0;
      if (state?.nodes) {
        const dayNarratives = narrativesByDayRef.current[tick] ?? {};
        const mappedNodes = state.nodes.map((node) => {
          const id = String(node.node_id ?? "");
          const type = asNodeType(String(node.node_type ?? "business"));
          return {
            id,
            label: String(node.label ?? node.node_id ?? "Node"),
            type,
            ...pickNodeIcons(id, type),
            x: Number(node.x ?? 120),
            y: Number(node.y ?? 120),
            vx: 0,
            vy: 0,
            influence: Number(node.influence ?? 0.5),
            status: asNodeStatus(String(node.status ?? "stable")),
            lastAction: dayNarratives[id]?.summary_short ?? "awaiting action",
          };
        });
        setNodes(mappedNodes);
        setTimelineByDay((prev) => ({
          ...prev,
          [tick]: {
            day: tick,
            nodes: mappedNodes,
            edges: prev[tick]?.edges ?? [],
            kpis: state.kpis,
            summary:
              (typeof state.day_summary_ai === "string" && state.day_summary_ai.trim().length > 0
                ? state.day_summary_ai
                : "") ||
              (typeof state.llm_context === "object" && state.llm_context && "summary" in state.llm_context
                ? String((state.llm_context as Record<string, unknown>).summary ?? "")
                : prev[tick]?.summary),
          },
        }));
      }
      if (state?.edges) {
        const mappedEdges = state.edges.map((edge) => ({
          id: String(edge.edge_id ?? ""),
          source: String(edge.source ?? ""),
          target: String(edge.target ?? ""),
          type: asEdgeType(String(edge.edge_type ?? "information")),
          weight: Number(edge.weight ?? 0.5),
          lastTick: tick,
        }));
        setEdges(mappedEdges);
        setTimelineByDay((prev) => ({
          ...prev,
          [tick]: {
            day: tick,
            nodes: prev[tick]?.nodes ?? nodesRef.current,
            edges: mappedEdges,
            kpis: prev[tick]?.kpis,
            summary: prev[tick]?.summary,
          },
        }));
      }
      return;
    }

    if (event.type === "node_action") {
      const action = event.action as { source_node_id?: string; action_type?: string } | undefined;
      const sourceId = String(action?.source_node_id ?? "unknown");
      const actionLabel = String(action?.action_type ?? "action");
      setNodes((prev) => prev.map((node) => (node.id === sourceId ? { ...node, lastAction: actionLabel, status: "active" } : node)));
      return;
    }

    if (event.type === "node_message") {
      const message = event.message as { node_id?: string; text?: string; narrative?: unknown } | undefined;
      const nodeId = String(message?.node_id ?? "");
      const narrative = normalizeNarrative(message?.narrative);
      if (nodeId && narrative) {
        const tick = event.tick ?? currentDayRef.current;
        setNodeNarratives((prev) => ({ ...prev, [nodeId]: narrative }));
        setNarrativesByDay((prev) => ({
          ...prev,
          [tick]: {
            ...(prev[tick] ?? {}),
            [nodeId]: narrative,
          },
        }));
        setActiveDialogNodeId(nodeId);
        setSelectedNodeId(nodeId);
        setNodes((prev) =>
          prev.map((node) =>
            node.id === nodeId
              ? { ...node, status: "active", lastAction: narrative.summary_short }
              : node,
          ),
        );
      }
      return;
    }

    if (event.type === "edge_update") {
      const edge = event.edge as { edge_id?: string; weight?: number } | undefined;
      const edgeId = String(edge?.edge_id ?? "");
      setEdges((prev) =>
        prev.map((item) =>
          item.id === edgeId
            ? { ...item, weight: Number(edge?.weight ?? item.weight), lastTick: event.tick ?? item.lastTick }
            : item,
        ),
      );
      return;
    }

    if (event.type === "observer_summary") {
      setObserverReport(event.summary ?? "Observer summary unavailable.");
      setObserverReady(true);
      return;
    }

    if (event.type === "error") {
      setStreamError(event.error ?? "Stream error");
      setIsRunning(false);
      return;
    }

    if (event.type === "done") {
      setIsRunning(false);
    }
  }

  function resetSimulation() {
    streamAbortRef.current?.abort();
    setIsRunning(false);
    setSessionId(null);
    setStreamError(null);
    setCurrentDay(0);
    setNodes(buildInitialNodes());
    setEdges(buildInitialEdges());
    setSelectedNodeId("n_business_hq");
    setActiveDialogNodeId(null);
    setObserverReady(false);
    setObserverReport("");
    setChatMessages([]);
    setNodeNarratives({});
    setTimelineByDay({});
    setNarrativesByDay({});
    setReplayDay(0);
    setFollowLive(true);
    setIsReplayPlaying(false);
  }

  function startSimulation() {
    resetSimulation();
    setStreamError(null);
    setIsRunning(true);
    const controller = new AbortController();
    streamAbortRef.current = controller;

    void streamNetworkSimulator(
      {
        query,
        max_ticks: maxDays,
        seed: 7,
        min_nodes: 15,
        max_nodes: 30,
        scenario_id: "business_network_v1",
      },
      {
        signal: controller.signal,
        onEvent: (event) => applyStreamEvent(event),
      },
    )
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : "Failed to start network simulation stream.";
        setStreamError(message);
        setIsRunning(false);
      })
      .finally(() => {
        setIsRunning(false);
      });
  }

  function stopSimulation() {
    streamAbortRef.current?.abort();
    setIsRunning(false);
  }

  async function injectShock() {
    if (!sessionId) return;
    const shock = randomPick(SHOCK_CATALOG);
    try {
      await injectNetworkShock(sessionId, {
        shock_type: "market_disruption",
        summary: shock,
        severity: 0.6,
        targets: [],
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to inject shock.";
      setStreamError(message);
    }
  }

  async function sendObserverMessage() {
    const text = chatInput.trim();
    if (!text || !observerReady || !sessionId) return;
    setChatMessages((prev) => [...prev, { role: "user", text }]);
    setChatInput("");
    try {
      const response = await chatNetworkObserver(sessionId, text);
      setChatMessages((prev) => [...prev, { role: "observer", text: response.answer }]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Observer chat failed.";
      setChatMessages((prev) => [...prev, { role: "observer", text: message }]);
    }
  }

  async function downloadStoryline() {
    if (!sessionId) return;
    try {
      const blob = await downloadNetworkStoryline(sessionId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${sessionId}_storyline.md`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to download storyline.";
      setStreamError(message);
    }
  }

  function handleWheel(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    const direction = event.deltaY > 0 ? -0.08 : 0.08;
    setZoom((prev) => clamp(prev + direction, 0.55, 1.85));
  }

  function handleCanvasPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (dragNodeRef.current) return;
    setActiveDialogNodeId(null);
    dragCanvasRef.current = {
      active: true,
      startX: event.clientX - offset.x,
      startY: event.clientY - offset.y,
    };
  }

  function handleCanvasPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (!dragCanvasRef.current.active) return;
    setOffset({
      x: event.clientX - dragCanvasRef.current.startX,
      y: event.clientY - dragCanvasRef.current.startY,
    });
  }

  function handleCanvasPointerUp() {
    dragCanvasRef.current.active = false;
  }

  function handleNodePointerDown(event: ReactPointerEvent<SVGElement>, nodeId: string) {
    event.stopPropagation();
    dragNodeRef.current = { nodeId, pointerId: event.pointerId };
    setSelectedNodeId(nodeId);
    if (activeNarratives[nodeId]) setActiveDialogNodeId(nodeId);
  }

  function handleSvgPointerMove(event: ReactPointerEvent<SVGSVGElement>) {
    const drag = dragNodeRef.current;
    if (!drag) return;
    const svgRect = event.currentTarget.getBoundingClientRect();
    const rawX = (event.clientX - svgRect.left - offset.x) / zoom;
    const rawY = (event.clientY - svgRect.top - offset.y) / zoom;
    setNodes((prev) =>
      prev.map((node) =>
        node.id === drag.nodeId ? { ...node, x: clamp(rawX, 40, 800), y: clamp(rawY, 30, 520), vx: 0, vy: 0 } : node,
      ),
    );
  }

  function handleSvgPointerUp(event: ReactPointerEvent<SVGSVGElement>) {
    const drag = dragNodeRef.current;
    if (drag && drag.pointerId === event.pointerId) dragNodeRef.current = null;
  }

  const popupPosition = dialogNode
    ? {
        left: clamp(dialogNode.x * zoom + offset.x + 18, 12, 520),
        top: clamp(dialogNode.y * zoom + offset.y - 170, 10, 320),
      }
    : null;
  const activeDaySummary = displaySnapshot?.summary ?? `Day ${activeDay}: simulation state snapshot.`;
  const activeDayKpis = displaySnapshot?.kpis;
  const activeDayNarrativeList = Object.entries(activeNarratives)
    .slice(0, 3)
    .map(([nodeId, narrative]) => {
      const node = nodeMap.get(nodeId);
      return `${node?.label ?? nodeId}: ${narrative.summary_short}`;
    });

  return (
    <section className="grid gap-4 px-4 py-5 lg:grid-cols-[300px_1fr_360px]">
      <aside className="space-y-4 rounded-3xl border border-border bg-card/75 p-4 shadow-card">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Scenario Input</p>
          <h2 className='mt-1 text-2xl text-foreground [font-family:"Iowan_Old_Style",Georgia,serif]'>Network Command Desk</h2>
        </div>
        <div className="space-y-3">
          <label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Decision Scenario</label>
          <Input value={query} onChange={(event) => setQuery(event.target.value)} />
          <label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Days</label>
          <Input
            type="number"
            min={1}
            max={90}
            value={maxDays}
            onChange={(event) => setMaxDays(clamp(Number(event.target.value || DEFAULT_DAYS), 1, 90))}
          />
        </div>

        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
          <Button className="h-10" onClick={() => startSimulation()} disabled={isRunning}>
            <Play className="mr-2 h-4 w-4" />
            Run Simulation
          </Button>
          <Button variant="outline" className="h-10" onClick={() => (isRunning ? stopSimulation() : startSimulation())}>
            {isRunning ? <Pause className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}
            {isRunning ? "Stop" : "Run Again"}
          </Button>
          <Button variant="outline" className="h-10" onClick={injectShock} disabled={!sessionId || !isRunning}>
            <Plus className="mr-2 h-4 w-4" />
            Inject Shock
          </Button>
          <Button variant="ghost" className="h-10" onClick={resetSimulation}>
            Reset
          </Button>
        </div>

        <div className="rounded-2xl border border-border bg-background/70 p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Session State</p>
          <div className="mt-2 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Session</span>
            <span className="font-semibold text-foreground">{sessionId ? sessionId.slice(-8) : "-"}</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Current day</span>
            <span className="font-semibold text-foreground">{currentDay}</span>
          </div>
          <div className="mt-1 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Nodes</span>
            <span className="font-semibold text-foreground">{nodes.length}</span>
          </div>
          <div className="mt-1 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Edges</span>
            <span className="font-semibold text-foreground">{edges.length}</span>
          </div>
        </div>

        {streamError && (
          <div className="rounded-xl border border-warning/40 bg-warning/10 p-2 text-xs text-foreground">
            <p className="font-semibold">Simulation Error</p>
            <p className="mt-1 text-muted-foreground">{streamError}</p>
          </div>
        )}
      </aside>

      <div className="rounded-3xl border border-border bg-card/80 p-3 shadow-card">
        <div className="mb-2 flex items-center justify-between px-2">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Live Graph</p>
            <p className='text-lg text-foreground [font-family:"Iowan_Old_Style",Georgia,serif]'>Economic Relationship Network</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">
              <Compass className="mr-1 h-3 w-3" />
              Zoom {zoom.toFixed(2)}x
            </Badge>
          </div>
        </div>
        <div className="mb-2 rounded-xl border border-border/80 bg-background/80 px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setFollowLive(false);
                setReplayDay((prev) => Math.max(0, prev - 1));
                setIsReplayPlaying(false);
              }}
              disabled={activeDay <= 0}
            >
              Prev
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                if (activeDay >= maxReplayDay) {
                  setFollowLive(false);
                  setReplayDay(0);
                }
                setIsReplayPlaying((prev) => !prev);
              }}
              disabled={maxReplayDay <= 0}
            >
              {isReplayPlaying ? <Pause className="mr-1 h-3.5 w-3.5" /> : <Play className="mr-1 h-3.5 w-3.5" />}
              {isReplayPlaying ? "Pause" : "Play"}
            </Button>
            <input
              type="range"
              min={0}
              max={Math.max(maxReplayDay, 0)}
              value={activeDay}
              className="h-2 w-[220px] cursor-pointer accent-primary"
              onChange={(event) => {
                setFollowLive(false);
                setIsReplayPlaying(false);
                setReplayDay(Number(event.target.value));
              }}
            />
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setFollowLive(false);
                setReplayDay((prev) => Math.min(maxReplayDay, prev + 1));
                setIsReplayPlaying(false);
              }}
              disabled={activeDay >= maxReplayDay}
            >
              Next
            </Button>
            <Button
              size="sm"
              variant={followLive ? "default" : "ghost"}
              onClick={() => {
                setFollowLive(true);
                setReplayDay(currentDay);
                setIsReplayPlaying(false);
              }}
            >
              Live
            </Button>
            <span className="text-xs font-semibold text-foreground">
              Day {activeDay} / {Math.max(maxReplayDay, currentDay)}
            </span>
          </div>
        </div>
        <div
          ref={graphViewportRef}
          className="relative h-[560px] overflow-hidden rounded-2xl border border-border/80 bg-[radial-gradient(circle_at_12%_18%,rgba(233,119,46,0.12),transparent_34%),radial-gradient(circle_at_84%_76%,rgba(60,131,123,0.15),transparent_38%),linear-gradient(180deg,rgba(250,246,239,0.95),rgba(241,235,224,0.94))]"
          onWheel={handleWheel}
          onPointerDown={handleCanvasPointerDown}
          onPointerMove={handleCanvasPointerMove}
          onPointerUp={handleCanvasPointerUp}
          onPointerLeave={handleCanvasPointerUp}
        >
          <svg className="h-full w-full touch-none" onPointerMove={handleSvgPointerMove} onPointerUp={handleSvgPointerUp}>
            <g transform={`translate(${offset.x}, ${offset.y}) scale(${zoom})`}>
              {displayEdges.map((edge) => {
                const source = nodeMap.get(edge.source);
                const target = nodeMap.get(edge.target);
                if (!source || !target) return null;
                const isSelected = selectedNode?.id === source.id || selectedNode?.id === target.id;
                return (
                  <line
                    key={edge.id}
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                    stroke={EDGE_COLORS[edge.type]}
                    strokeOpacity={isSelected ? 0.85 : 0.46}
                    strokeWidth={1.2 + edge.weight * (isSelected ? 3 : 2)}
                    strokeDasharray={edge.type === "information" ? "5 5" : edge.type === "influence" ? "2 6" : ""}
                  />
                );
              })}

              {displayNodes.map((node) => {
                const style = NODE_TYPE_STYLE[node.type];
                const isSelected = selectedNode?.id === node.id;
                const radius = isSelected ? 31 : 25 + node.influence * 5;
                const iconSize = isSelected ? 52 : 44;
                const personaSize = isSelected ? 22 : 18;
                return (
                  <g
                    key={node.id}
                    onPointerDown={(event) => {
                      event.stopPropagation();
                      setSelectedNodeId(node.id);
                      if (activeNarratives[node.id]) setActiveDialogNodeId(node.id);
                    }}
                    onClick={() => setSelectedNodeId(node.id)}
                  >
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={radius + 7}
                      fill={style.ring}
                      opacity={isSelected ? 0.8 : 0.5}
                      pointerEvents="none"
                    />
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={radius}
                      fill={style.color}
                      stroke={isSelected ? "#111827" : "rgba(17,24,39,0.4)"}
                      strokeWidth={isSelected ? 2.4 : 1.1}
                      opacity={0.35}
                    />
                    <image
                      href={node.buildingIcon}
                      x={node.x - iconSize / 2}
                      y={node.y - iconSize / 2}
                      width={iconSize}
                      height={iconSize}
                      style={{ imageRendering: "pixelated", pointerEvents: "none" }}
                    />
                    <image
                      href={node.personaIcon}
                      x={node.x + iconSize / 2 - personaSize}
                      y={node.y - iconSize / 2 - personaSize * 0.25}
                      width={personaSize}
                      height={personaSize}
                      style={{ imageRendering: "pixelated", pointerEvents: "none" }}
                    />
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={radius}
                      fill="transparent"
                      stroke="transparent"
                      onPointerDown={(event) => handleNodePointerDown(event, node.id)}
                      style={{ cursor: "grab" }}
                    />
                    <text
                      x={node.x}
                      y={node.y + radius + 14}
                      textAnchor="middle"
                      fontSize={11}
                      fill="rgba(17,24,39,0.84)"
                      style={{ userSelect: "none" }}
                    >
                      {node.label}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>

          {popupPosition && dialogNode && (
            <div
              className="absolute w-[310px] rounded-2xl border border-border bg-card/95 p-3 shadow-xl backdrop-blur-sm"
              style={{ left: popupPosition.left, top: popupPosition.top }}
              onWheelCapture={(event) => {
                event.stopPropagation();
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Agent Speaking</p>
                  <p className="text-sm font-semibold text-foreground">{dialogNode.label}</p>
                </div>
                <div className="flex items-center gap-1">
                  <Badge variant="outline" className="text-[10px]">{formatNodeType(dialogNode.type)}</Badge>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => setActiveDialogNodeId(null)}
                    aria-label="Close node dialog"
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
              {!dialogNarrative && (
                <p className="mt-2 text-xs text-muted-foreground">
                  This node has not responded yet. Run simulation or wait for this agent turn.
                </p>
              )}
              {dialogNarrative && (
                <div className="mt-2 space-y-2">
                  <p className="text-sm text-foreground">{dialogNarrative.headline}</p>
                  <p className="text-xs text-muted-foreground">{dialogNarrative.summary_short}</p>
                  <div className="grid grid-cols-3 gap-1 text-[10px]">
                    <Badge variant="outline">Sales {formatDirection(dialogNarrative.sales.direction)}</Badge>
                    <Badge variant="outline">Cost {formatDirection(dialogNarrative.cost.direction)}</Badge>
                    <Badge variant="outline">Risk {formatDirection(dialogNarrative.risk.direction)}</Badge>
                  </div>
                  <ScrollArea
                    className="h-28 rounded-xl border border-border/70 bg-background/60 p-2"
                    onWheelCapture={(event) => {
                      event.stopPropagation();
                    }}
                  >
                    <div className="break-words text-xs leading-relaxed text-foreground [&_a]:text-primary [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_li]:ml-4 [&_li]:list-disc [&_p]:whitespace-pre-wrap [&_pre]:overflow-auto [&_pre]:rounded-md [&_pre]:border [&_pre]:border-border [&_pre]:bg-muted/40 [&_pre]:p-2">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{dialogNarrative.full_response_md}</ReactMarkdown>
                    </div>
                  </ScrollArea>
                </div>
              )}
            </div>
          )}
        </div>
        <div className="mt-2 rounded-2xl border border-border bg-background/80 p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Day Summary</p>
          <p className="mt-1 text-sm text-foreground">{activeDaySummary}</p>
          <div className="mt-2 grid gap-2 text-xs sm:grid-cols-3">
            <div className="rounded-lg border border-border/70 bg-card/70 p-2">
              Revenue: {((activeDayKpis?.revenue_delta ?? 0) * 100).toFixed(2)}%
            </div>
            <div className="rounded-lg border border-border/70 bg-card/70 p-2">
              Cost: {((activeDayKpis?.cost_delta ?? 0) * 100).toFixed(2)}%
            </div>
            <div className="rounded-lg border border-border/70 bg-card/70 p-2">
              Risk: {((activeDayKpis?.risk_delta ?? 0) * 100).toFixed(2)}%
            </div>
          </div>
          {activeDayNarrativeList.length > 0 && (
            <div className="mt-2 rounded-lg border border-border/70 bg-card/70 p-2 text-xs text-muted-foreground">
              {activeDayNarrativeList.map((line) => (
                <p key={line} className="mb-1 last:mb-0">
                  {line}
                </p>
              ))}
            </div>
          )}
        </div>
      </div>

      <aside className="space-y-4 rounded-3xl border border-border bg-card/75 p-4 shadow-card">
        <div className="rounded-2xl border border-border bg-background/80 p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Final Observer Summary</p>
            <Button variant="outline" size="sm" onClick={downloadStoryline} disabled={!observerReady || !sessionId}>
              <Download className="mr-1 h-3.5 w-3.5" />
              Download Storyline
            </Button>
          </div>
          <div className="mt-2 rounded-xl border border-border/70 bg-card/70 p-3 text-sm text-foreground">
            {!observerReady && (
              <p className="flex items-center gap-2 text-muted-foreground">
                <Sparkles className="h-4 w-4" />
                Report will appear after simulation completes.
              </p>
            )}
            {observerReady && (
              <div className="break-words text-sm leading-relaxed text-foreground [&_a]:text-primary [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_li]:ml-5 [&_li]:list-disc [&_ol]:ml-5 [&_ol]:list-decimal [&_p]:whitespace-pre-wrap [&_pre]:overflow-auto [&_pre]:rounded-md [&_pre]:border [&_pre]:border-border [&_pre]:bg-muted/40 [&_pre]:p-2">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{observerReport}</ReactMarkdown>
              </div>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-background/80 p-3">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Observer Chat</p>
            <Badge variant={observerReady ? "default" : "outline"} className="text-[10px]">
              {observerReady ? "Ready" : "Locked"}
            </Badge>
          </div>
          <ScrollArea className="mt-2 h-80 rounded-xl border border-border/70 bg-card/70 p-2">
            <div className="space-y-2">
              {chatMessages.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  Ask observer questions after simulation completes.
                </p>
              )}
              {chatMessages.map((message, idx) => (
                <div
                  key={`${message.role}-${idx}`}
                  className={`rounded-lg px-2 py-1.5 text-xs ${
                    message.role === "observer"
                      ? "border border-primary/30 bg-primary/10 text-foreground"
                      : "border border-border/70 bg-background text-foreground"
                  }`}
                >
                  <p className="mb-1 font-semibold uppercase tracking-[0.12em] text-muted-foreground">{message.role}</p>
                  {message.role === "observer" ? (
                    <div className="break-words leading-relaxed text-foreground [&_a]:text-primary [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_li]:ml-4 [&_li]:list-disc [&_ol]:ml-4 [&_ol]:list-decimal [&_p]:whitespace-pre-wrap [&_pre]:overflow-auto [&_pre]:rounded-md [&_pre]:border [&_pre]:border-border [&_pre]:bg-muted/40 [&_pre]:p-2">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
                    </div>
                  ) : (
                    <p>{message.text}</p>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
          <div className="mt-2 flex gap-2">
            <Input
              placeholder="Ask observer after run..."
              value={chatInput}
              disabled={!observerReady}
              onChange={(event) => setChatInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") sendObserverMessage();
              }}
            />
            <Button size="icon" disabled={!observerReady || !chatInput.trim()} onClick={sendObserverMessage}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </aside>
    </section>
  );
}
