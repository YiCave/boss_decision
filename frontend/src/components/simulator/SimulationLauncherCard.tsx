import { ArrowUpRight, Clock3, MessageSquareText, Network, Orbit, Sparkles, Spline } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

interface SimulationLauncherCardProps {
  query?: string;
}

interface LastRunSummary {
  query: string;
  recommendation?: string;
  status: "ok" | "error";
  completedAt: string;
}

const STORAGE_KEY = "simulator:last-run";

function readLastRun(): LastRunSummary | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as LastRunSummary;
    if (!parsed || typeof parsed !== "object") return null;
    return parsed;
  } catch {
    return null;
  }
}

const modeCards: Array<{
  id: "classic" | "deep" | "network";
  title: string;
  subtitle: string;
  detail: string;
  icon: typeof Orbit;
  accentClass: string;
}> = [
  {
    id: "classic",
    title: "Classic Simulation",
    subtitle: "Realtime Swarm Debate",
    detail: "Judge-style multi-agent reasoning with streamed turn updates.",
    icon: Orbit,
    accentClass: "from-primary/30 via-primary/10 to-transparent"
  },
  {
    id: "deep",
    title: "Deep 2D Arena",
    subtitle: "Tycoon + Crisis Sprint",
    detail: "Board-style strategic moves and crisis-card pressure testing.",
    icon: Spline,
    accentClass: "from-accent/30 via-accent/10 to-transparent"
  },
  {
    id: "network",
    title: "Network Lab",
    subtitle: "Live Relationship World",
    detail: "Influence links, observer chat, and storyline evolution in real time.",
    icon: Network,
    accentClass: "from-warning/35 via-warning/10 to-transparent"
  }
];

export function SimulationLauncherCard({ query }: SimulationLauncherCardProps) {
  const [lastRun, setLastRun] = useState<LastRunSummary | null>(null);

  useEffect(() => {
    setLastRun(readLastRun());
    const onStorage = () => setLastRun(readLastRun());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const baseQuery = useMemo(() => {
    const params = new URLSearchParams();
    const trimmed = query?.trim();
    if (trimmed) params.set("query", trimmed);
    return params;
  }, [query]);

  const hintText = useMemo(() => {
    if (!query?.trim()) return "No active query yet. You can still enter the unified simulator page.";
    return `Current query will preload Classic mode: "${query.trim()}"`;
  }, [query]);

  return (
    <section className="rounded-[1.6rem] border border-border bg-card/75 p-6 shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Simulator Entry</p>
          <h3 className="mt-1 text-3xl leading-none text-foreground">All Three Simulators</h3>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            One page with tab buttons. Use cards to open the unified simulator page on the right tab.
          </p>
        </div>
        <p className="max-w-md rounded-xl border border-border/80 bg-background/70 px-3 py-2 text-xs text-muted-foreground">
          {hintText}
        </p>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
        {modeCards.map((item) => {
          const Icon = item.icon;
          const params = new URLSearchParams(baseQuery);
          params.set("tab", item.id);
          const href = `/simulators?${params.toString()}`;

          return (
            <Link
              key={item.id}
              to={href}
              className={cn(
                "group relative overflow-hidden rounded-2xl border border-border bg-card/85 p-4 text-left transition-all duration-300",
                "min-h-[180px] hover:-translate-y-0.5 hover:border-primary/40 hover:bg-card"
              )}
            >
              <div
                className={cn(
                  "pointer-events-none absolute inset-0 bg-gradient-to-br opacity-0 transition-opacity duration-300 group-hover:opacity-100",
                  item.accentClass
                )}
              />
              <div className="relative flex h-full flex-col gap-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-border/80 bg-background/90 text-foreground">
                    <Icon className="h-4.5 w-4.5" />
                  </span>
                  <span className="rounded-full border border-border bg-background/90 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground group-hover:text-foreground">
                    Open
                  </span>
                </div>

                <div className="space-y-1">
                  <h4 className="text-xl leading-tight text-foreground">{item.title}</h4>
                  <p className="text-xs font-semibold uppercase tracking-[0.17em] text-muted-foreground group-hover:text-foreground/80">
                    {item.subtitle}
                  </p>
                </div>

                <p className="mt-auto text-sm leading-5 text-foreground/85">{item.detail}</p>
              </div>
            </Link>
          );
        })}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Link
          to="/simulation-live"
          target="_blank"
          rel="noreferrer"
          className={cn(
            "inline-flex h-11 items-center rounded-lg border border-border bg-card px-5 text-sm text-foreground transition-colors hover:bg-card/80"
          )}
        >
          <Orbit className="mr-2 h-4 w-4" />
          Open Classic Simulation
          <ArrowUpRight className="ml-2 h-4 w-4" />
        </Link>
        <Link
          to="/simulation-deep"
          target="_blank"
          rel="noreferrer"
          className={cn(
            "inline-flex h-11 items-center rounded-lg border border-border bg-card px-5 text-sm text-foreground transition-colors hover:bg-card/80"
          )}
        >
          <Spline className="mr-2 h-4 w-4" />
          Open Deep 2D Arena
          <ArrowUpRight className="ml-2 h-4 w-4" />
        </Link>
        <Link
          to="/simulation-network"
          target="_blank"
          rel="noreferrer"
          className={cn(
            "inline-flex h-11 items-center rounded-lg border border-border bg-card px-5 text-sm text-foreground transition-colors hover:bg-card/80"
          )}
        >
          <Network className="mr-2 h-4 w-4" />
          Open Network Lab
          <ArrowUpRight className="ml-2 h-4 w-4" />
        </Link>
        <Link
          to="/simulation-sales-supply-debate"
          target="_blank"
          rel="noreferrer"
          className={cn(
            "inline-flex h-11 items-center rounded-lg border border-border bg-card px-5 text-sm text-foreground transition-colors hover:bg-card/80"
          )}
        >
          <MessageSquareText className="mr-2 h-4 w-4" />
          Open Sales-Supply Debate
          <ArrowUpRight className="ml-2 h-4 w-4" />
        </Link>
      </div>

      <div className="mt-5 rounded-xl border border-border bg-background/70 p-4">
        <p className="mb-2 inline-flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
          <Clock3 className="h-3.5 w-3.5" />
          Last Run Snapshot
        </p>
        {!lastRun && <p className="text-sm text-muted-foreground">No simulation run recorded yet.</p>}
        {lastRun && (
          <div className="space-y-2 text-sm">
            <p className="text-foreground">
              <span className="text-muted-foreground">Status:</span> {lastRun.status === "ok" ? "Completed" : "Error"}
            </p>
            <p className="text-foreground">
              <span className="text-muted-foreground">Query:</span> {lastRun.query}
            </p>
            {lastRun.recommendation && (
              <p className="text-foreground">
                <span className="text-muted-foreground">Recommendation:</span> {lastRun.recommendation}
              </p>
            )}
            <p className="text-muted-foreground">{new Date(lastRun.completedAt).toLocaleString()}</p>
          </div>
        )}
      </div>

      <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-border bg-background/85 px-3 py-1.5 text-xs text-muted-foreground">
        <Sparkles className="h-3.5 w-3.5 text-primary" />
        Hover a card for preview, click to open the corresponding tab in the unified simulator page.
      </div>
    </section>
  );
}
