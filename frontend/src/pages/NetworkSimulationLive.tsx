import { Brain, ChevronLeft, Network, Spline } from "lucide-react";
import { Link } from "react-router-dom";
import { NetworkSimulationSection } from "@/components/simulator/network/NetworkSimulationSection";

const NetworkSimulationLive = () => {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_8%_0%,rgba(233,119,46,0.16),transparent_34%),radial-gradient(circle_at_90%_10%,rgba(27,133,122,0.18),transparent_38%),linear-gradient(180deg,rgba(249,245,236,0.98),rgba(241,235,224,0.98))]">
      <div className="pointer-events-none absolute -left-28 top-24 h-72 w-72 rounded-full bg-accent/15 blur-3xl" />
      <div className="pointer-events-none absolute -right-20 top-12 h-80 w-80 rounded-full bg-primary/20 blur-3xl" />
      <div className="pointer-events-none absolute inset-0 opacity-10 [background-image:linear-gradient(to_right,rgba(28,28,28,0.2)_1px,transparent_1px),linear-gradient(to_bottom,rgba(28,28,28,0.2)_1px,transparent_1px)] [background-size:40px_40px]" />

      <header className="sticky top-0 z-20 border-b border-border/80 bg-background/80 backdrop-blur-md">
        <div className="container max-w-[1400px] py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-gradient-primary flex items-center justify-center shadow-glow">
              <Brain className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-3xl leading-none text-foreground">Network Simulation Lab</h1>
              <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Live Relationship World</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/simulation-deep"
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-foreground hover:bg-card"
            >
              <Spline className="h-3.5 w-3.5" />
              Deep 2D Arena
            </Link>
            <Link
              to="/simulation-live"
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-foreground hover:bg-card"
            >
              <Network className="h-3.5 w-3.5" />
              Classic Simulation
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

      <main className="w-full">
        <NetworkSimulationSection />
      </main>
    </div>
  );
};

export default NetworkSimulationLive;
