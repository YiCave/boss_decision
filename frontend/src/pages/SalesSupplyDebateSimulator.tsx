import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Brain, ChevronLeft, Loader2, MessageSquareText, Scale } from "lucide-react";
import { Link } from "react-router-dom";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { DebateSimulationResult, runSalesSupplyDebateSimulation, SalesSupplyDebateResponse } from "@/lib/sales-supply-debate-client";

type DebateMessage = {
  id: string;
  round: number;
  speaker: "sales" | "supply";
  role: string;
  agentId: string;
  body: string;
  marketSignal?: string;
  validity?: "valid" | "invalid";
  strictChecks?: string[];
};

const DebateChatPlayback = ({
  session,
  sessionKey,
  onPlaybackComplete,
}: {
  session: DebateSimulationResult;
  sessionKey: string;
  onPlaybackComplete: (sessionKey: string, done: boolean) => void;
}) => {
  const messages = useMemo<DebateMessage[]>(() => {
    return session.rounds.slice(0, 5).flatMap((debateRound) => [
      {
        id: `${session.supply_id}-r${debateRound.round}-sales`,
        round: debateRound.round,
        speaker: "sales" as const,
        role: debateRound.sales_agent.role,
        agentId: debateRound.sales_agent.agent_id,
        body: debateRound.sales_agent.suggestion,
        marketSignal: debateRound.sales_agent.market_signal,
      },
      {
        id: `${session.supply_id}-r${debateRound.round}-supply`,
        round: debateRound.round,
        speaker: "supply" as const,
        role: debateRound.supply_chain_agent.role,
        agentId: debateRound.supply_chain_agent.agent_id,
        body: debateRound.supply_chain_agent.response,
        validity: debateRound.supply_chain_agent.validity,
        strictChecks: debateRound.supply_chain_agent.strict_checks?.slice(0, 3) ?? [],
      },
    ]);
  }, [session]);

  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    setVisibleCount(0);
    onPlaybackComplete(sessionKey, false);

    if (!messages.length) {
      onPlaybackComplete(sessionKey, true);
      return;
    }

    let revealIndex = 0;
    let timer: number | undefined;

    const revealNext = () => {
      revealIndex += 1;
      setVisibleCount(revealIndex);

      if (revealIndex >= messages.length) {
        onPlaybackComplete(sessionKey, true);
        return;
      }

      const nextSpeaker = messages[revealIndex].speaker;
      const gapMs = nextSpeaker === "supply" ? 2300 : 1700;
      timer = window.setTimeout(revealNext, gapMs);
    };

    timer = window.setTimeout(revealNext, 600);

    return () => {
      if (timer) window.clearTimeout(timer);
    };
  }, [messages, onPlaybackComplete, sessionKey]);

  const isCompleted = visibleCount >= messages.length;
  const nextSpeaker = !isCompleted ? messages[visibleCount]?.speaker : null;

  return (
    <div className="rounded-2xl border border-border bg-background/75 p-4">
      <div className="mb-4 flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Debate Chat Replay</p>
        <Badge variant={isCompleted ? "secondary" : "default"} className={isCompleted ? "" : "animate-pulse"}>
          {isCompleted ? "Debate Completed" : "Debate In Progress"}
        </Badge>
      </div>

      <div className="max-h-[520px] space-y-3 overflow-y-auto pr-2 sim-scroll">
        {messages.slice(0, visibleCount).map((message) => {
          const isSales = message.speaker === "sales";
          return (
            <div key={message.id} className={`chat-pop flex ${isSales ? "justify-end" : "justify-start"}`}>
              <article
                className={`max-w-[92%] rounded-2xl border p-3 text-sm shadow-sm md:max-w-[80%] ${
                  isSales
                    ? "border-primary/25 bg-primary/10 text-foreground"
                    : "border-accent/30 bg-accent/10 text-foreground"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.11em] text-muted-foreground">
                    Round {message.round} | {message.role} ({message.agentId})
                  </p>
                  {!isSales && message.validity && (
                    <Badge
                      className={
                        message.validity === "valid"
                          ? "border border-success/40 bg-success/10 text-foreground"
                          : "border border-destructive/40 bg-destructive/10 text-foreground"
                      }
                    >
                      {message.validity === "valid" ? "Valid" : "Invalid"}
                    </Badge>
                  )}
                </div>

                <p className="mt-2 leading-relaxed">{message.body}</p>

                {isSales && message.marketSignal && (
                  <p className="mt-2 text-xs text-muted-foreground">Market signal: {message.marketSignal}</p>
                )}

                {!isSales && (message.strictChecks?.length ?? 0) > 0 && (
                  <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                    {message.strictChecks?.map((check, idx) => (
                      <li key={`${message.id}-check-${idx}`}>- {check}</li>
                    ))}
                  </ul>
                )}
              </article>
            </div>
          );
        })}

        {!isCompleted && nextSpeaker && (
          <div className={`flex ${nextSpeaker === "sales" ? "justify-end" : "justify-start"}`}>
            <div className="rounded-full border border-border bg-card px-4 py-2 text-xs text-muted-foreground">
              <span className="debate-typing">
                {nextSpeaker === "sales" ? "Sales Agent is preparing next response..." : "Supply Chain Agent is evaluating and replying..."}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const JudgeResultPanel = ({ session }: { session: DebateSimulationResult }) => {
  if (!session.judge_result) {
    return (
      <Card className="border-border/80 bg-card/60">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Scale className="h-4 w-4 text-muted-foreground" />
            Judge Result
          </CardTitle>
          <CardDescription>No judge output was returned for this debate.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="judge-highlight border-border/80 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Scale className="h-4 w-4 text-foreground" />
          Judge Result Session
        </CardTitle>
        <CardDescription>AI-3 arbitration summary and final outcome for this debate.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            className={
              session.final_result.status === "approved"
                ? "border border-success/40 bg-success/10 text-foreground"
                : "border border-destructive/40 bg-destructive/10 text-foreground"
            }
          >
            Final: {session.final_result.status === "approved" ? "Approved" : "Rejected"}
          </Badge>
        </div>
        <p className="rounded-lg border border-border bg-background/80 p-3 leading-relaxed">{session.final_result.conclusion}</p>
        <div className="flex flex-wrap items-center gap-2">
          <Badge className="border border-border bg-background text-foreground">
            Winner: {session.judge_result.winner === "sales" ? "Sales Agent" : "Supply Chain Agent"}
          </Badge>
          <Badge className="border border-border bg-background text-foreground">
            Verdict: {session.judge_result.verdict === "execute" ? "Execute plan" : "Hold plan"}
          </Badge>
          <Badge className="border border-border bg-background text-foreground">
            Confidence: {Math.round((session.judge_result.confidence ?? 0) * 100)}%
          </Badge>
        </div>
        <p className="rounded-lg border border-border bg-background/80 p-3 leading-relaxed">{session.judge_result.rationale}</p>
      </CardContent>
    </Card>
  );
};

const SalesSupplyDebateSimulator = () => {
  const [itemName, setItemName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SalesSupplyDebateResponse | null>(null);
  const [playbackDoneBySession, setPlaybackDoneBySession] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setPlaybackDoneBySession({});
  }, [result]);

  const handlePlaybackComplete = useCallback((sessionKey: string, done: boolean) => {
    setPlaybackDoneBySession((prev) => {
      if (prev[sessionKey] === done) return prev;
      return { ...prev, [sessionKey]: done };
    });
  }, []);

  const handleRun = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = await runSalesSupplyDebateSimulation({
        item_name: itemName.trim() || undefined,
        max_rounds: 5,
      });
      setResult(payload);
    } catch (requestError) {
      setResult(null);
      setError(requestError instanceof Error ? requestError.message : "Failed to run debate simulator.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_12%_0%,rgba(28,87,161,0.18),transparent_36%),radial-gradient(circle_at_84%_9%,rgba(11,122,101,0.14),transparent_34%),linear-gradient(180deg,rgba(242,246,250,0.98),rgba(234,240,245,0.98))]">
      <div className="pointer-events-none absolute -left-24 top-12 h-72 w-72 rounded-full bg-primary/15 blur-3xl" />
      <div className="pointer-events-none absolute -right-20 top-16 h-80 w-80 rounded-full bg-accent/20 blur-3xl" />

      <header className="sticky top-0 z-20 border-b border-border/80 bg-background/80 backdrop-blur-md">
        <div className="container max-w-7xl py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-gradient-primary flex items-center justify-center shadow-glow">
              <Brain className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-3xl leading-none text-foreground">Sales vs Supply Debate Simulator</h1>
              <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">AI-1 Sales Agent and AI-2 Supply Chain Agent</p>
            </div>
          </div>
          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-foreground hover:bg-card"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Back to Landing
          </Link>
        </div>
      </header>

      <main className="container max-w-7xl py-10 space-y-6">
        <Card className="border-border/80 bg-card/85">
          <CardHeader>
            <CardTitle className="text-2xl">Debate Runner</CardTitle>
            <CardDescription>
              The simulator reads `supply_record.item_name`, sends item context to Sales AI, then starts a debate loop where Supply Chain AI approves or rejects until a final decision is reached.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4 md:grid-cols-4" onSubmit={handleRun}>
              <div className="md:col-span-2 space-y-2">
                <label className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground" htmlFor="item-name-input">
                  Item Name Filter (optional)
                </label>
                <Input
                  id="item-name-input"
                  value={itemName}
                  onChange={(event) => setItemName(event.target.value)}
                  placeholder="Example: Running shoes"
                />
              </div>
              <div className="md:col-span-2 space-y-2">
                <label className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground" htmlFor="max-rounds-input">
                  Debate Rounds (Fixed)
                </label>
                <Input
                  id="max-rounds-input"
                  type="number"
                  value={5}
                  disabled
                />
              </div>
              <div className="md:col-span-4 flex justify-end">
                <Button type="submit" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Running Debate
                    </>
                  ) : (
                    <>
                      <MessageSquareText className="mr-2 h-4 w-4" />
                      Start Simulation
                    </>
                  )}
                </Button>
              </div>
            </form>
            <p className="mt-3 text-xs text-muted-foreground">
              Item retrieval is fixed to 1 record and debate is fixed to 5 rounds per simulation run.
            </p>
          </CardContent>
        </Card>

        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Simulation failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {result && (
          <div className="space-y-4">
            <Card className="bg-card/85">
              <CardHeader>
                <CardTitle className="text-xl">Retrieval and Outcome Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p><span className="font-semibold">Status:</span> {result.status}</p>
                <p><span className="font-semibold">Retrieved item_name values:</span> {result.retrieved_item_names.join(", ") || "-"}</p>
                {result.summary && (
                  <p>
                    <span className="font-semibold">Result:</span> {result.summary.approved} approved / {result.summary.rejected} rejected (total {result.summary.total_items})
                  </p>
                )}
                {result.message && <p className="text-muted-foreground">{result.message}</p>}
              </CardContent>
            </Card>

            {result.simulations.map((session) => {
              const sessionKey = `${session.supply_id}-${session.item_name}`;
              const isPlaybackDone = !!playbackDoneBySession[sessionKey];

              return (
              <Card key={sessionKey} className="bg-card/85">
                <CardHeader>
                  <CardTitle className="text-lg">
                    Supply #{session.supply_id} - {session.item_name}
                  </CardTitle>
                  <CardDescription>
                    Inventory {session.inventory_context.inventory_level ?? "-"} | Forecast {session.inventory_context.demand_forecast ?? "-"} | Reorder {session.inventory_context.reorder_point ?? "-"}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <DebateChatPlayback
                    session={session}
                    sessionKey={sessionKey}
                    onPlaybackComplete={handlePlaybackComplete}
                  />
                  {isPlaybackDone ? (
                    <JudgeResultPanel session={session} />
                  ) : (
                    <Card className="border-border/80 bg-card/60">
                      <CardHeader className="pb-3">
                        <CardTitle className="flex items-center gap-2 text-base">
                          <Scale className="h-4 w-4 text-muted-foreground" />
                          Judge Result Session
                        </CardTitle>
                        <CardDescription>
                          Judge result will appear after the full debate conversation is completed.
                        </CardDescription>
                      </CardHeader>
                    </Card>
                  )}
                </CardContent>
              </Card>
            );
            })}
          </div>
        )}
      </main>
    </div>
  );
};

export default SalesSupplyDebateSimulator;
