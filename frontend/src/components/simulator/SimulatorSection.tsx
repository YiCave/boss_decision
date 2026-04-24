import { useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, Loader2, Rocket, Sparkles, Wrench, XCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { streamSimulator, SimulatorStreamEvent } from "@/lib/simulator-client";

const defaultPrompt = "Should we increase price by 10% for student segment next quarter?";

const STEP_ORDER = [
  "parse_decision",
  "build_scenario",
  "select_personas",
  "persona_worker",
  "collect_results",
  "aggregate_impacts",
  "scenario_branch_worker",
  "generate_recommendation",
  "format_response",
] as const;

const STEP_LABEL: Record<string, string> = {
  parse_decision: "Interpreting your decision question",
  build_scenario: "Building scenario constraints and assumptions",
  select_personas: "Picking specialist subagents for this case",
  persona_worker: "Running subagents in parallel and collecting evidence",
  collect_results: "Collecting subagent outputs",
  aggregate_impacts: "Calculating KPI and risk/opportunity impact",
  scenario_branch_worker: "Stress testing optimistic and downside branches",
  generate_recommendation: "Synthesizing one recommendation",
  format_response: "Packaging the final answer",
};

type PersonaState = "queued" | "running" | "done" | "fallback";
type PersonaEventType = "tool";

interface PersonaEvent {
  id: string;
  type: PersonaEventType;
  text: string;
}

interface PersonaCard {
  persona_id: string;
  confidence: number;
  risks: string[];
  opportunities: string[];
  rationale: string;
  kpi_deltas: Record<string, number>;
  status: PersonaState;
  transcript: string;
  events: PersonaEvent[];
}

interface SimulatorSectionProps {
  initialQuery?: string;
}

function titleizePersonaId(personaId: string): string {
  return personaId
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function clipText(input: string, max = 130): string {
  const text = input.trim().replace(/\s+/g, " ");
  if (text.length <= max) return text;
  return `${text.slice(0, max)}...`;
}

function normalizePersona(data: unknown): PersonaCard | null {
  if (!data || typeof data !== "object") return null;
  const raw = data as Record<string, unknown>;
  const persona_id = typeof raw.persona_id === "string" ? raw.persona_id : "unknown";
  const confidence = typeof raw.confidence === "number" ? raw.confidence : 0;
  const risks = Array.isArray(raw.risks) ? raw.risks.filter((r): r is string => typeof r === "string") : [];
  const opportunities = Array.isArray(raw.opportunities)
    ? raw.opportunities.filter((o): o is string => typeof o === "string")
    : [];
  const rationale = typeof raw.rationale === "string" ? raw.rationale : "";
  const kpi_deltas = raw.kpi_deltas && typeof raw.kpi_deltas === "object" ? (raw.kpi_deltas as Record<string, number>) : {};
  const fallback = risks.some((risk) => risk.toLowerCase().includes("fallback")) || rationale.toLowerCase().includes("fallback");
  return {
    persona_id,
    confidence,
    risks,
    opportunities,
    rationale,
    kpi_deltas,
    status: fallback ? "fallback" : "done",
    transcript: "",
    events: [],
  };
}

function statusTone(status: PersonaState): string {
  if (status === "done") return "border-success/40 bg-success/10 text-foreground";
  if (status === "fallback") return "border-warning/40 bg-warning/10 text-foreground";
  if (status === "running") return "border-primary/60 bg-primary/10 text-foreground";
  return "border-border bg-secondary text-secondary-foreground";
}

export function SimulatorSection({ initialQuery }: SimulatorSectionProps) {
  const [query, setQuery] = useState(initialQuery?.trim() || defaultPrompt);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [personas, setPersonas] = useState<Record<string, PersonaCard>>({});
  const [personaOrder, setPersonaOrder] = useState<string[]>([]);
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);

  const [recommendation, setRecommendation] = useState("");
  const [topRisks, setTopRisks] = useState<string[]>([]);
  const [topOpportunities, setTopOpportunities] = useState<string[]>([]);

  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [completedStepFlags, setCompletedStepFlags] = useState<Record<string, boolean>>({});

  const transcriptBufferRef = useRef<Record<string, string>>({});
  const flushTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (flushTimerRef.current !== null) window.clearTimeout(flushTimerRef.current);
    };
  }, []);

  const ensurePersonaExists = (personaId: string) => {
    setPersonas((prev) => {
      if (prev[personaId]) return prev;
      return {
        ...prev,
        [personaId]: {
          persona_id: personaId,
          confidence: 0,
          risks: [],
          opportunities: [],
          rationale: "",
          kpi_deltas: {},
          status: "queued",
          transcript: "",
          events: [],
        },
      };
    });
    setPersonaOrder((prev) => (prev.includes(personaId) ? prev : [...prev, personaId]));
  };

  const appendPersonaEvent = (personaId: string, type: PersonaEventType, text: string) => {
    ensurePersonaExists(personaId);
    setPersonas((prev) => {
      const item = prev[personaId];
      if (!item) return prev;
      const event: PersonaEvent = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        type,
        text,
      };
      return {
        ...prev,
        [personaId]: { ...item, events: [...item.events, event].slice(-80) },
      };
    });
  };

  const setPersonaStatus = (personaId: string, status: PersonaState) => {
    ensurePersonaExists(personaId);
    setPersonas((prev) => {
      const item = prev[personaId];
      if (!item) return prev;
      return { ...prev, [personaId]: { ...item, status } };
    });
  };

  const appendPersonaTranscript = (personaId: string, chunk: string) => {
    ensurePersonaExists(personaId);
    transcriptBufferRef.current[personaId] = `${transcriptBufferRef.current[personaId] ?? ""}${chunk}`;
    if (flushTimerRef.current !== null) return;
    flushTimerRef.current = window.setTimeout(() => {
      const updates = transcriptBufferRef.current;
      transcriptBufferRef.current = {};
      flushTimerRef.current = null;
      const ids = Object.keys(updates);
      if (ids.length === 0) return;
      setPersonas((prev) => {
        const next = { ...prev };
        ids.forEach((id) => {
          const item = next[id];
          const text = updates[id];
          if (!item || !text) return;
          const merged = `${item.transcript}${text}`;
          next[id] = { ...item, transcript: merged.length > 24000 ? merged.slice(-24000) : merged };
        });
        return next;
      });
    }, 75);
  };

  const flushTranscriptBuffers = () => {
    if (flushTimerRef.current !== null) {
      window.clearTimeout(flushTimerRef.current);
      flushTimerRef.current = null;
    }
    const updates = transcriptBufferRef.current;
    transcriptBufferRef.current = {};
    const ids = Object.keys(updates);
    if (ids.length === 0) return;
    setPersonas((prev) => {
      const next = { ...prev };
      ids.forEach((id) => {
        const item = next[id];
        const text = updates[id];
        if (!item || !text) return;
        const merged = `${item.transcript}${text}`;
        next[id] = { ...item, transcript: merged.length > 24000 ? merged.slice(-24000) : merged };
      });
      return next;
    });
  };

  const markStepFromNode = (node: string) => {
    const idx = STEP_ORDER.indexOf(node as (typeof STEP_ORDER)[number]);
    if (idx < 0) return;
    setCurrentStep(node);
    setCompletedStepFlags((prev) => {
      const next = { ...prev };
      for (let i = 0; i <= idx; i += 1) next[STEP_ORDER[i]] = true;
      return next;
    });
  };

  const handleEvent = (event: SimulatorStreamEvent) => {
    if (event.type === "update") {
      if (event.nodes?.length) {
        event.nodes.forEach((node) => markStepFromNode(node));
      }

      if (!event.updates || typeof event.updates !== "object") return;
      const payload = event.updates as Record<string, unknown>;
      const selectPayload = payload.select_personas as Record<string, unknown> | undefined;
      if (selectPayload && Array.isArray(selectPayload.selected_personas)) {
        const personaIds = selectPayload.selected_personas
          .map((item) => (item && typeof item === "object" ? (item as Record<string, unknown>).id : null))
          .filter((id): id is string => typeof id === "string");
        if (personaIds.length > 0) {
          setPersonaOrder(personaIds);
          personaIds.forEach((id) => ensurePersonaExists(id));
          setSelectedPersona((current) => current ?? personaIds[0]);
        }
      }

      const workerPayload = payload.persona_worker as Record<string, unknown> | undefined;
      if (workerPayload && Array.isArray(workerPayload.persona_stream_events)) {
        workerPayload.persona_stream_events.forEach((evt) => {
          if (!evt || typeof evt !== "object") return;
          const row = evt as Record<string, unknown>;
          const personaId = typeof row.persona_id === "string" ? row.persona_id : null;
          const text = typeof row.text === "string" ? row.text : "";
          if (!personaId || !text) return;
          setPersonaStatus(personaId, "running");
          appendPersonaTranscript(personaId, text);
          setSelectedPersona((current) => current ?? personaId);
        });
      }
      return;
    }

    if (event.type === "custom") {
      const data = event.data ?? {};
      const eventType = typeof event.event === "string" ? event.event : "";
      if (eventType === "subagent_token") {
        const personaId = typeof data.persona_id === "string" ? data.persona_id : null;
        const text = typeof data.text === "string" ? data.text : "";
        if (personaId && text) {
          setPersonaStatus(personaId, "running");
          appendPersonaTranscript(personaId, text);
          setSelectedPersona((current) => current ?? personaId);
        }
        return;
      }
      if (eventType === "subagent_tool") {
        const personaId = typeof data.persona_id === "string" ? data.persona_id : null;
        const toolName = typeof data.tool_name === "string" ? data.tool_name : "";
        if (personaId && toolName) {
          appendPersonaEvent(personaId, "tool", `Called tool: ${toolName}`);
          setSelectedPersona((current) => current ?? personaId);
        }
        return;
      }
      if (eventType === "subagent_status") {
        const personaId = typeof data.persona_id === "string" ? data.persona_id : null;
        const status = typeof data.status === "string" ? data.status : "";
        if (!personaId) return;
        if (status === "running" || status === "queued" || status === "done" || status === "fallback") {
          setPersonaStatus(personaId, status);
        }
      }
      return;
    }

    if (event.type === "final") {
      flushTranscriptBuffers();
      setCompletedStepFlags(Object.fromEntries(STEP_ORDER.map((step) => [step, true])));
      setCurrentStep("format_response");

      const payload = (event.response ?? event.state ?? null) as Record<string, unknown> | null;
      const response = (payload?.response ?? payload) as Record<string, unknown> | undefined;
      if (typeof response?.recommendation === "string") setRecommendation(response.recommendation);
      if (Array.isArray(response?.ranked_risks)) setTopRisks((response.ranked_risks as string[]).slice(0, 5));
      if (Array.isArray(response?.ranked_opportunities)) setTopOpportunities((response.ranked_opportunities as string[]).slice(0, 5));

      const personaRows = Array.isArray(response?.persona_reactions) ? response.persona_reactions : [];
      const parsed = personaRows.map((item) => normalizePersona(item)).filter((item): item is PersonaCard => item !== null);
      if (parsed.length > 0) {
        setPersonas((prev) => {
          const next = { ...prev };
          parsed.forEach((persona) => {
            const existing = next[persona.persona_id];
            next[persona.persona_id] = {
              ...persona,
              transcript: existing?.transcript ?? "",
              events: existing?.events ?? [],
            };
          });
          return next;
        });
      }
      return;
    }

    if (event.type === "error") {
      flushTranscriptBuffers();
      setError(event.error ?? "Unknown simulator error.");
    }
  };

  const runSimulation = async () => {
    if (!query.trim() || isRunning) return;
    setIsRunning(true);
    setError(null);
    setPersonas({});
    setPersonaOrder([]);
    setSelectedPersona(null);
    setRecommendation("");
    setTopRisks([]);
    setTopOpportunities([]);
    setCurrentStep(null);
    setCompletedStepFlags({});
    transcriptBufferRef.current = {};
    if (flushTimerRef.current !== null) {
      window.clearTimeout(flushTimerRef.current);
      flushTimerRef.current = null;
    }

    try {
      await streamSimulator({ query: query.trim() }, { onEvent: handleEvent });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to reach simulator stream endpoint.";
      setError(message);
    } finally {
      flushTranscriptBuffers();
      setIsRunning(false);
    }
  };

  const orderedPersonas = (personaOrder.length > 0 ? personaOrder : Object.keys(personas))
    .map((id) => personas[id])
    .filter((item): item is PersonaCard => Boolean(item));
  const selectedPersonaCard = selectedPersona ? personas[selectedPersona] ?? null : null;

  const swarmCounts = useMemo(() => {
    const counts = { queued: 0, running: 0, done: 0, fallback: 0 };
    Object.values(personas).forEach((persona) => {
      counts[persona.status] += 1;
    });
    return counts;
  }, [personas]);

  const completedCount = STEP_ORDER.filter((step) => completedStepFlags[step]).length;
  const progressPct = Math.min(100, Math.round((completedCount / STEP_ORDER.length) * 100));
  const currentStepText = currentStep ? STEP_LABEL[currentStep] ?? "Running simulation" : "Waiting to start";

  return (
    <section className="w-full bg-background text-foreground">
      <div className="border-b border-border/70 px-5 py-5 md:px-8">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="text-[0.62rem] uppercase tracking-[0.32em] text-primary">Simulation</p>
            <h2 className="mt-2 text-3xl leading-tight md:text-4xl" style={{ fontFamily: '"Baskerville Old Face", "Times New Roman", serif' }}>
              Swarm Liveboard
            </h2>
          </div>
          <div className="flex w-full flex-col gap-2 xl:w-[62%]">
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="h-11 border-border bg-card/90 text-foreground placeholder:text-muted-foreground focus-visible:ring-primary"
                placeholder="Ask a strategic decision question..."
                style={{ fontFamily: '"IBM Plex Mono", monospace' }}
              />
              <Button
                onClick={runSimulation}
                disabled={isRunning}
                className="h-11 min-w-44 border border-primary/35 bg-primary px-5 font-semibold text-primary-foreground hover:bg-primary/90"
                style={{ fontFamily: '"IBM Plex Mono", monospace' }}
              >
                {isRunning ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Running
                  </>
                ) : (
                  <>
                    <Rocket className="mr-2 h-4 w-4" />
                    Launch Simulation
                  </>
                )}
              </Button>
            </div>
            <div className="space-y-1">
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <p className="text-[11px] font-light tracking-[0.08em] text-muted-foreground">
                {progressPct}% complete. {currentStepText}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid h-[calc(100vh-13.5rem)] items-stretch gap-4 px-5 py-5 md:px-8 lg:grid-cols-[0.86fr_1.45fr_0.92fr]">
        <aside className="flex h-full min-h-0 flex-col rounded-2xl border border-border bg-card/85 p-4">
          <ScrollArea className="min-h-0 flex-1">
            <div className="space-y-4 pr-1">
              <div className="rounded-xl border border-border bg-background/80 p-3">
                <p className="text-[11px] font-light uppercase tracking-[0.14em] text-muted-foreground">Simulation Progress</p>
                <p className="mt-1 text-xl font-semibold">{progressPct}%</p>
                <p className="mt-1 text-xs text-muted-foreground">{currentStepText}</p>
              </div>

              <div className="rounded-xl border border-border bg-background/80 p-3">
                <p className="mb-2 inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  <Sparkles className="h-4 w-4 text-success" />
                  Final Decision
                </p>
                <div className="text-sm leading-relaxed text-foreground">
                  {recommendation || "Recommendation will appear after synthesis."}
                </div>
              </div>

              <div className="grid gap-2">
                <div className="rounded-xl border border-border bg-background/80 p-3">
                  <p className="mb-1 text-[11px] font-light uppercase tracking-[0.14em] text-muted-foreground">Top Risks</p>
                  <div className="space-y-1">
                    {(topRisks.length > 0 ? topRisks.slice(0, 3) : ["No dominant downside signal yet."]).map((risk, idx) => (
                      <p key={`${risk}-${idx}`} className="rounded-md border border-border bg-background/90 px-2 py-1 text-xs">
                        {risk}
                      </p>
                    ))}
                  </div>
                </div>
                <div className="rounded-xl border border-border bg-background/80 p-3">
                  <p className="mb-1 text-[11px] font-light uppercase tracking-[0.14em] text-muted-foreground">Top Opportunities</p>
                  <div className="space-y-1">
                    {(topOpportunities.length > 0 ? topOpportunities.slice(0, 3) : ["No dominant upside signal yet."]).map((item, idx) => (
                      <p key={`${item}-${idx}`} className="rounded-md border border-border bg-background/90 px-2 py-1 text-xs">
                        {item}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </ScrollArea>
        </aside>

        <main className="flex h-full min-h-0 flex-col rounded-2xl border border-border bg-card/85 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Selected Subagent</p>
              <p className="text-base font-semibold">
                {selectedPersonaCard ? titleizePersonaId(selectedPersonaCard.persona_id) : "No subagent selected"}
              </p>
            </div>
            {selectedPersonaCard && <Badge className={statusTone(selectedPersonaCard.status)}>{selectedPersonaCard.status}</Badge>}
          </div>

          {!selectedPersonaCard && <p className="text-sm text-muted-foreground">Select a subagent on the right to inspect live output.</p>}
          {selectedPersonaCard && (
            <ScrollArea className="min-h-0 flex-1 rounded-xl border border-border bg-background/85">
              <div className="p-3">
              {(selectedPersonaCard.status === "running" || selectedPersonaCard.status === "queued") && (
                <div className="space-y-3">
                  <div>
                    <p className="mb-2 text-[11px] font-light uppercase tracking-[0.14em] text-muted-foreground">Tool Calls</p>
                    <div className="space-y-2">
                      {selectedPersonaCard.events.length === 0 && <p className="text-xs text-muted-foreground">No tool calls yet.</p>}
                      {selectedPersonaCard.events.map((event) => (
                        <div key={event.id} className="rounded-md border border-border bg-card/80 px-2 py-1.5">
                          <p className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                            <Wrench className="h-3 w-3" />
                            Tool call
                          </p>
                          <p className="text-xs text-foreground">{event.text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  {selectedPersonaCard.transcript.trim() && (
                    <div>
                      <p className="mb-2 text-[11px] font-light uppercase tracking-[0.14em] text-muted-foreground">Live Response</p>
                      <div className="break-words text-sm leading-relaxed text-foreground [&_a]:text-primary [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_li]:ml-5 [&_li]:list-disc [&_ol]:ml-5 [&_ol]:list-decimal [&_p]:whitespace-pre-wrap [&_pre]:overflow-auto [&_pre]:rounded-md [&_pre]:border [&_pre]:border-border [&_pre]:bg-muted/40 [&_pre]:p-2">
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                          {selectedPersonaCard.transcript}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {(selectedPersonaCard.status === "done" || selectedPersonaCard.status === "fallback") && (
                <div className="space-y-3">
                  <details>
                    <summary className="cursor-pointer list-none rounded-md border border-border bg-card/80 px-2 py-1.5 text-xs text-muted-foreground">
                      Tool calls ({selectedPersonaCard.events.length})
                    </summary>
                    <div className="mt-2 space-y-2">
                      {selectedPersonaCard.events.length === 0 && <p className="text-xs text-muted-foreground">No tool calls captured.</p>}
                      {selectedPersonaCard.events.map((event) => (
                        <div key={event.id} className="rounded-md border border-border bg-card/80 px-2 py-1.5">
                          <p className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                            <Wrench className="h-3 w-3" />
                            Tool call
                          </p>
                          <p className="text-xs text-foreground">{event.text}</p>
                        </div>
                      ))}
                    </div>
                  </details>

                  <div>
                    <p className="mb-2 text-[11px] font-light uppercase tracking-[0.14em] text-muted-foreground">Final Response</p>
                    {selectedPersonaCard.transcript ? (
                      <div className="break-words text-sm leading-relaxed text-foreground [&_a]:text-primary [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_li]:ml-5 [&_li]:list-disc [&_ol]:ml-5 [&_ol]:list-decimal [&_p]:whitespace-pre-wrap [&_pre]:overflow-auto [&_pre]:rounded-md [&_pre]:border [&_pre]:border-border [&_pre]:bg-muted/40 [&_pre]:p-2">
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                          {selectedPersonaCard.transcript}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">No final response content captured.</p>
                    )}
                  </div>
                </div>
              )}
              </div>
            </ScrollArea>
          )}
        </main>

        <aside className="flex h-full min-h-0 flex-col rounded-2xl border border-border bg-card/85 p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Subagent Swarm</p>
            <div className="flex gap-1 text-[10px]">
              <Badge className="border border-border bg-secondary text-secondary-foreground">Q {swarmCounts.queued}</Badge>
              <Badge className="border border-primary/40 bg-primary/10 text-foreground">R {swarmCounts.running}</Badge>
              <Badge className="border border-success/40 bg-success/10 text-foreground">D {swarmCounts.done}</Badge>
              <Badge className="border border-warning/40 bg-warning/10 text-foreground">F {swarmCounts.fallback}</Badge>
            </div>
          </div>

          <ScrollArea className="min-h-0 flex-1">
            <div className="space-y-2 pr-1">
              {orderedPersonas.length === 0 && <p className="rounded-md border border-border bg-background/75 p-3 text-sm text-muted-foreground">No subagents spawned yet.</p>}
              {orderedPersonas.map((persona) => {
                const selected = selectedPersona === persona.persona_id;
                const lastTool = persona.events.length > 0 ? persona.events[persona.events.length - 1]?.text : "";
                const preview = persona.transcript
                  ? clipText(persona.transcript)
                  : lastTool
                    ? clipText(lastTool)
                    : "Awaiting stream...";
                return (
                  <button
                    key={persona.persona_id}
                    type="button"
                    onClick={() => setSelectedPersona(persona.persona_id)}
                    className={`w-full rounded-xl border p-3 text-left transition ${selected ? "border-primary/65 bg-card shadow-[0_0_0_1px_hsl(var(--primary)/0.25)]" : "border-border bg-card/80 hover:border-primary/45 hover:bg-card"}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold">{titleizePersonaId(persona.persona_id)}</p>
                      <Badge className={statusTone(persona.status)}>
                        {persona.status === "done" ? <CheckCircle2 className="mr-1 h-3 w-3" /> : null}
                        {persona.status === "fallback" ? <XCircle className="mr-1 h-3 w-3" /> : null}
                        {persona.status}
                      </Badge>
                    </div>
                    <p className="mt-2 text-[11px] font-light text-muted-foreground">{persona.persona_id}</p>
                    <p className="mt-2 rounded-md border border-border bg-background/80 px-2 py-1.5 text-xs">{preview}</p>
                  </button>
                );
              })}
            </div>
          </ScrollArea>
        </aside>
      </div>

      {error && (
        <div className="px-5 pb-5 md:px-8">
          <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</div>
        </div>
      )}
    </section>
  );
}
