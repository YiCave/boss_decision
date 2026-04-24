import { FormEvent, useMemo, useState } from "react";
import {
  Brain,
  CalendarRange,
  ChevronLeft,
  Globe2,
  Lightbulb,
  Loader2,
  Newspaper,
  Sparkles,
  Target,
} from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getSalesCampaignSuggestions, SalesCampaignResponse } from "@/lib/sales-agent-client";

const DEFAULT_PRODUCT_HINTS = [
  "Healthy snack box",
  "Hydration bottle",
  "Skincare starter kit",
  "Wireless earbuds",
  "Study desk lamp",
  "Productivity software subscription",
];

const SalesAgent = () => {
  const [product, setProduct] = useState("");
  const [region, setRegion] = useState("Malaysia");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<SalesCampaignResponse | null>(null);

  const productHints = useMemo(() => {
    if (result?.hints?.length) {
      return result.hints;
    }
    return DEFAULT_PRODUCT_HINTS;
  }, [result]);

  const handleGenerateSuggestions = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleanProduct = product.trim();

    if (cleanProduct.length < 2) {
      setError("Please enter a valid product name before continuing.");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = await getSalesCampaignSuggestions({
        product: cleanProduct,
        region: region.trim() || "Malaysia",
      });
      setResult(response);
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Unable to generate suggestions right now.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_14%_0%,rgba(232,101,59,0.22),transparent_36%),radial-gradient(circle_at_88%_18%,rgba(250,182,64,0.18),transparent_34%),linear-gradient(180deg,rgba(252,247,241,0.98),rgba(247,237,226,0.98))]">
      <div className="pointer-events-none absolute -left-28 top-16 h-72 w-72 rounded-full bg-primary/15 blur-3xl" />
      <div className="pointer-events-none absolute -right-20 top-12 h-80 w-80 rounded-full bg-accent/20 blur-3xl" />

      <header className="sticky top-0 z-20 border-b border-border/80 bg-background/80 backdrop-blur-md">
        <div className="container max-w-7xl py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-gradient-primary flex items-center justify-center shadow-glow">
              <Brain className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-3xl leading-none text-foreground">Sales Agent</h1>
              <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Campaign and Event Suggestor</p>
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

      <main className="container max-w-7xl py-10">
        <section className="relative overflow-hidden rounded-[2rem] border border-border bg-card/75 p-6 shadow-card md:p-8">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_92%_4%,hsl(var(--primary)/0.18),transparent_36%)]" />
          <div className="relative grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/75 px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                Campaign Suggestor
              </p>
              <h2 className="mt-4 text-4xl leading-tight text-foreground md:text-5xl">
                Plan your next 7 days with a product-first sales advisor.
              </h2>
              <p className="mt-3 max-w-2xl text-sm text-muted-foreground md:text-base">
                Tell the Sales Agent what product you plan to sell. It then scrapes recent market news via Tavily and
                returns campaign and event ideas you can execute in the next week.
              </p>
            </div>

            <div className="grid gap-3">
              <div className="rounded-2xl border border-border bg-background/70 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Step 1</p>
                <p className="mt-1 flex items-center gap-2 text-base font-semibold text-foreground">
                  <Lightbulb className="h-4 w-4 text-primary" />
                  Pick product and region focus
                </p>
              </div>
              <div className="rounded-2xl border border-border bg-background/70 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Step 2</p>
                <p className="mt-1 flex items-center gap-2 text-base font-semibold text-foreground">
                  <Newspaper className="h-4 w-4 text-primary" />
                  Tavily scans recent news signals
                </p>
              </div>
              <div className="rounded-2xl border border-border bg-background/70 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Step 3</p>
                <p className="mt-1 flex items-center gap-2 text-base font-semibold text-foreground">
                  <CalendarRange className="h-4 w-4 text-primary" />
                  Receive a next-week execution plan
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <article className="rounded-[1.6rem] border border-border bg-card/80 p-6 shadow-card">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Sales Agent Prompt</p>
            <h3 className="mt-3 text-3xl leading-tight text-foreground">What product are you planning to sell this week?</h3>
            <p className="mt-3 text-sm text-muted-foreground">
              Choose from hints or type your own product, then the agent will scrape current market news and suggest
              campaigns and events to run in the next 7 days.
            </p>

            <div className="mt-5 flex flex-wrap gap-2">
              {productHints.map((hint) => (
                <button
                  key={hint}
                  type="button"
                  onClick={() => setProduct(hint)}
                  className="rounded-full border border-border bg-background px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                >
                  {hint}
                </button>
              ))}
            </div>

            <form className="mt-5 space-y-4" onSubmit={handleGenerateSuggestions}>
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground" htmlFor="product-input">
                  Product
                </label>
                <Input
                  id="product-input"
                  value={product}
                  onChange={(event) => setProduct(event.target.value)}
                  placeholder="Example: Protein snack pack"
                  className="h-11"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground" htmlFor="region-input">
                  Region
                </label>
                <Input
                  id="region-input"
                  value={region}
                  onChange={(event) => setRegion(event.target.value)}
                  placeholder="Example: Malaysia"
                  className="h-11"
                />
              </div>

              <Button
                type="submit"
                className="h-11 w-full border border-primary/30 bg-primary text-primary-foreground hover:bg-primary/90"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Scraping news and building plan...
                  </>
                ) : (
                  "Generate 7-Day Campaign Suggestions"
                )}
              </Button>
            </form>

            {error && (
              <div className="mt-4 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {error}
              </div>
            )}
          </article>

          <article className="rounded-[1.6rem] border border-border bg-card/80 p-6 shadow-card">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Execution Notes</p>
            <div className="mt-4 space-y-4">
              <div className="rounded-xl border border-border bg-background/70 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Input Quality</p>
                <p className="mt-1 text-sm text-foreground">
                  Use specific product names for stronger trend matching, for example "vegan protein bar" instead of
                  "food product".
                </p>
              </div>
              <div className="rounded-xl border border-border bg-background/70 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Campaign Scope</p>
                <p className="mt-1 text-sm text-foreground">
                  Suggestions combine awareness and conversion actions so your team can execute both top-funnel and
                  bottom-funnel moves in a single week.
                </p>
              </div>
              <div className="rounded-xl border border-border bg-background/70 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Source Transparency</p>
                <p className="mt-1 text-sm text-foreground">
                  Every campaign card includes source links from Tavily search results so your team can validate the
                  market signal before acting.
                </p>
              </div>
            </div>
          </article>
        </section>

        {result && (
          <>
            <section className="mt-8 rounded-[1.6rem] border border-border bg-card/80 p-6 shadow-card">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">News Signals</p>
                  <h3 className="mt-2 text-2xl text-foreground">Recent market context for {result.product}</h3>
                </div>
                <Badge variant="secondary" className="bg-background text-foreground">
                  Generated {new Date(result.generated_at).toLocaleString()}
                </Badge>
              </div>

              <p className="mt-3 text-sm text-muted-foreground">Search query: {result.search_query}</p>

              <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {result.news_signals.length === 0 && (
                  <div className="rounded-xl border border-border bg-background/70 p-4 text-sm text-muted-foreground">
                    No news signals were returned. Try a more specific product name or region.
                  </div>
                )}

                {result.news_signals.map((signal) => (
                  <article key={`${signal.title}-${signal.url}`} className="rounded-xl border border-border bg-background/70 p-4">
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{signal.source || "Source"}</p>
                    <h4 className="mt-2 line-clamp-2 text-base font-semibold text-foreground">{signal.title}</h4>
                    <p className="mt-2 line-clamp-4 text-sm text-muted-foreground">{signal.summary}</p>
                    <div className="mt-3 flex items-center justify-between gap-2 text-xs text-muted-foreground">
                      <span>{signal.published_date || "Recent"}</span>
                      {signal.url ? (
                        <a
                          href={signal.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 font-semibold text-foreground hover:text-primary"
                        >
                          <Globe2 className="h-3.5 w-3.5" />
                          Open source
                        </a>
                      ) : (
                        <span>Source unavailable</span>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="mt-8 rounded-[1.6rem] border border-border bg-card/80 p-6 shadow-card">
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-primary" />
                <h3 className="text-2xl text-foreground">Campaign and event playbook for the next week</h3>
              </div>

              <div className="mt-5 space-y-4">
                {result.suggestions.map((suggestion) => (
                  <article key={suggestion.title} className="rounded-xl border border-border bg-background/70 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className="bg-primary/90 text-primary-foreground">{suggestion.type.toUpperCase()}</Badge>
                      <h4 className="text-lg font-semibold text-foreground">{suggestion.title}</h4>
                    </div>

                    <p className="mt-3 text-sm text-foreground">
                      <span className="font-semibold">Objective:</span> {suggestion.objective}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      <span className="font-semibold text-foreground">Why now:</span> {suggestion.why_now}
                    </p>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {suggestion.channels.map((channel) => (
                        <Badge key={`${suggestion.title}-${channel}`} variant="outline" className="bg-background text-foreground">
                          {channel}
                        </Badge>
                      ))}
                    </div>

                    <div className="mt-4 grid gap-2 md:grid-cols-2">
                      {suggestion.next_week_plan.map((step) => (
                        <div key={`${suggestion.title}-${step.day}`} className="rounded-lg border border-border/70 bg-card/60 px-3 py-2 text-sm text-foreground">
                          <span className="font-semibold">Day {step.day}:</span> {step.action}
                        </div>
                      ))}
                    </div>

                    <p className="mt-3 text-sm text-muted-foreground">
                      <span className="font-semibold text-foreground">Success metric:</span> {suggestion.success_metric}
                    </p>

                    {suggestion.sources.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2 text-xs">
                        {suggestion.sources.map((source) => (
                          <a
                            key={`${suggestion.title}-${source}`}
                            href={source}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center rounded-full border border-border bg-background px-2.5 py-1 text-muted-foreground hover:text-foreground"
                          >
                            Source reference
                          </a>
                        ))}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>
          </>
        )}

        <section className="mt-8">
          <Button asChild variant="outline" className="h-11 border-border bg-background/80 px-5">
            <Link to="/">Return to Boardroom Atlas</Link>
          </Button>
        </section>
      </main>
    </div>
  );
};

export default SalesAgent;
