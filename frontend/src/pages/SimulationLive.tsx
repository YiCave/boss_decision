import { Brain, ChevronLeft, Network, Radio, Sparkles, Spline } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { SimulatorSection } from "@/components/simulator/SimulatorSection";

const SimulationLive = () => {
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get("query") ?? "";

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_12%_0%,rgba(233,119,46,0.18),transparent_34%),radial-gradient(circle_at_88%_10%,rgba(22,154,142,0.16),transparent_36%),linear-gradient(180deg,rgba(252,246,238,0.98),rgba(247,240,230,0.98))]">
      <div className="pointer-events-none absolute -left-28 top-24 h-72 w-72 rounded-full bg-accent/15 blur-3xl" />
      <div className="pointer-events-none absolute -right-20 top-12 h-80 w-80 rounded-full bg-primary/20 blur-3xl" />
      <div className="pointer-events-none absolute inset-0 opacity-10 [background-image:linear-gradient(to_right,rgba(28,28,28,0.2)_1px,transparent_1px),linear-gradient(to_bottom,rgba(28,28,28,0.2)_1px,transparent_1px)] [background-size:40px_40px]" />

      <header className="sticky top-0 z-20 border-b border-border/80 bg-background/80 backdrop-blur-md">
        <div className="container max-w-7xl py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-gradient-primary flex items-center justify-center shadow-glow">
              <Brain className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-3xl leading-none text-foreground">Simulation Live</h1>
              <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Realtime Swarm Mission Control</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden md:inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              Judge Mode
            </span>
            <span className="hidden md:inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              <Radio className="h-3.5 w-3.5 text-primary" />
              Live Stream
            </span>
            <Link
              to="/simulation-deep"
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-foreground hover:bg-card"
            >
              <Spline className="h-3.5 w-3.5" />
              Deep 2D
            </Link>
            <Link
              to="/simulation-network"
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-foreground hover:bg-card"
            >
              <Network className="h-3.5 w-3.5" />
              Network Lab
            </Link>
            <Link
              to="/"
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-foreground hover:bg-card"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Back to Decision
            </Link>
          </div>
        </div>
      </header>

      <main className="container max-w-7xl py-8">
        <SimulatorSection initialQuery={initialQuery} />
      </main>
    </div>
  );
};

export default SimulationLive;
