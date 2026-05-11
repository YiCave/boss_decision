import { useMemo, useState } from "react";
import { Brain, ChevronLeft, Network, Orbit, Spline } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { SimulatorSection } from "@/components/simulator/SimulatorSection";
import { DeepSimulationSection } from "@/components/simulator/deep/DeepSimulationSection";
import { NetworkSimulationSection } from "@/components/simulator/network/NetworkSimulationSection";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type SimulatorTab = "classic" | "deep" | "network";

const tabItems: Array<{ value: SimulatorTab; label: string; icon: typeof Orbit }> = [
  { value: "classic", label: "Classic", icon: Orbit },
  { value: "deep", label: "Deep 2D", icon: Spline },
  { value: "network", label: "Network", icon: Network }
];

const SimulatorsHub = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get("query") ?? "";
  const initialTab = searchParams.get("tab");
  const safeInitialTab: SimulatorTab = initialTab === "deep" || initialTab === "network" ? initialTab : "classic";

  const [activeTab, setActiveTab] = useState<SimulatorTab>(safeInitialTab);

  const subtitle = useMemo(() => {
    if (activeTab === "classic") return "Realtime swarm mission control";
    if (activeTab === "deep") return "Tycoon sprint with crisis cards";
    return "Relationship and influence live world";
  }, [activeTab]);

  const handleTabChange = (value: string) => {
    const next = value as SimulatorTab;
    setActiveTab(next);

    const params = new URLSearchParams(searchParams);
    params.set("tab", next);
    setSearchParams(params, { replace: true });
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_12%_0%,rgba(233,119,46,0.18),transparent_34%),radial-gradient(circle_at_88%_10%,rgba(22,154,142,0.16),transparent_36%),linear-gradient(180deg,rgba(252,246,238,0.98),rgba(247,240,230,0.98))]">
      <div className="pointer-events-none absolute -left-28 top-24 h-72 w-72 rounded-full bg-accent/15 blur-3xl" />
      <div className="pointer-events-none absolute -right-20 top-12 h-80 w-80 rounded-full bg-primary/20 blur-3xl" />
      <div className="pointer-events-none absolute inset-0 opacity-10 [background-image:linear-gradient(to_right,rgba(28,28,28,0.2)_1px,transparent_1px),linear-gradient(to_bottom,rgba(28,28,28,0.2)_1px,transparent_1px)] [background-size:40px_40px]" />

      <header className="sticky top-0 z-30 border-b border-border/80 bg-background/85 backdrop-blur-md">
        <div className="container mx-auto max-w-[1400px] py-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-gradient-primary flex items-center justify-center shadow-glow">
              <Brain className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-3xl leading-none text-foreground">Simulators</h1>
            </div>
          </div>

          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-foreground hover:bg-card"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Back
          </Link>
        </div>
      </header>

      <main className="container mx-auto max-w-[1400px] py-6 space-y-6">
        <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-4">
          <TabsList className="h-auto w-full flex-wrap gap-2 rounded-2xl border border-border bg-card/80 p-2 text-foreground">
            {tabItems.map((tab) => {
              const Icon = tab.icon;
              return (
                <TabsTrigger
                  key={tab.value}
                  value={tab.value}
                  className="h-10 min-w-[150px] rounded-xl border border-border/85 bg-background/70 px-4 text-xs font-semibold uppercase tracking-[0.14em] text-foreground data-[state=active]:border-primary/50 data-[state=active]:bg-primary/10 data-[state=active]:text-foreground"
                >
                  <Icon className="mr-2 h-3.5 w-3.5" />
                  {tab.label}
                </TabsTrigger>
              );
            })}
          </TabsList>

          <section className="rounded-[1.6rem] border border-border bg-card/70 p-3 shadow-card md:p-4">
            <div className="mb-3 rounded-xl border border-border bg-background/65 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Active Tab</p>
              <h3 className="text-2xl text-foreground">{tabItems.find((item) => item.value === activeTab)?.label} Simulator</h3>
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            </div>

            <TabsContent value="classic" className="mt-0">
              <SimulatorSection initialQuery={initialQuery} />
            </TabsContent>

            <TabsContent value="deep" className="mt-0">
              <DeepSimulationSection />
            </TabsContent>

            <TabsContent value="network" className="mt-0">
              <NetworkSimulationSection />
            </TabsContent>
          </section>
        </Tabs>
      </main>
    </div>
  );
};

export default SimulatorsHub;
