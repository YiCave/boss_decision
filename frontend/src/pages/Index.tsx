import { useEffect, useMemo, useState } from "react";
import { Brain, AlertTriangle, FileText, MessageSquare, Package, TrendingUp } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { InputPanel } from "@/components/decision/InputPanel";
import { FinalDecision } from "@/components/decision/FinalDecision";
import { analyzeDecision, AnalysisResult, type ChatMessage } from "@/lib/decision-engine";
import { getChatBubbleClass, getLabelAccentClass } from "@/lib/agentChatStyles";

const Index = () => {
  const navigate = useNavigate();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [activeQuery, setActiveQuery] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [visibleMessages, setVisibleMessages] = useState(0);

  const chatMessages: ChatMessage[] = result?.chat || [];

  useEffect(() => {
    if (!chatMessages.length) {
      setVisibleMessages(0);
      return;
    }

    setVisibleMessages(0);
    const timer = setInterval(() => {
      setVisibleMessages((prev) => {
        if (prev >= chatMessages.length) {
          clearInterval(timer);
          return prev;
        }
        return prev + 1;
      });
    }, 260);

    return () => clearInterval(timer);
  }, [result, chatMessages.length]);

  const handleAnalyze = async (payload: {
    query: string;
    context?: string;
    targetType?: string;
    targetId?: number;
    allowMockFallback: boolean;
    document?: File;
    mode: string;
    forcedAgents?: string[];
  }) => {
    setIsAnalyzing(true);
    setError("");
    setActiveQuery(payload.query);
    try {
      const analyzed = await analyzeDecision(payload.query, {
        context: payload.context,
        targetType: payload.targetType,
        targetId: payload.targetId,
        allowMockFallback: payload.allowMockFallback,
        document: payload.document,
        mode: payload.mode,
        forcedAgents: payload.forcedAgents,
      });
      setResult(analyzed);
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const shownChat = useMemo(() => chatMessages.slice(0, visibleMessages), [chatMessages, visibleMessages]);

  return (
    <div className="min-h-screen bg-gradient-subtle flex flex-col items-center">
      <header className="border-b border-border bg-card/60 backdrop-blur-sm sticky top-0 z-10 w-full">
        <div className="container max-w-7xl px-4 md:px-6 py-4 mx-auto flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-gradient-primary flex items-center justify-center shadow-glow shrink-0">
                <Brain className="w-5 h-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground leading-tight">
                  AI Decision Engine
                </h1>
                <p className="text-xs text-muted-foreground">
                  #manager-orchestrator · group-chat orchestration view
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate("/documents")}
                className="bg-gradient-to-r from-orange-400 to-orange-600 text-white border-0 hover:from-orange-500 hover:to-orange-700 shadow-md"
              >
                <FileText className="w-4 h-4 mr-2" />
                Documents
              </Button>
              <Button variant="secondary" size="sm" asChild>
                <Link to="/simulators">Simulators</Link>
              </Button>
              <div className="hidden md:flex items-center gap-2 text-xs font-medium text-muted-foreground">
                <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                Engine online
              </div>
            </div>
          </div>
          <nav
            className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 pt-1 border-t border-border/60"
            aria-label="Sales and supply tools"
          >
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground shrink-0">
              {"Sales & supply"}
            </span>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" className="h-8" asChild>
                <Link to="/agents/sales" className="inline-flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5" />
                  Sales agent
                </Link>
              </Button>
              <Button variant="outline" size="sm" className="h-8" asChild>
                <Link to="/agents/supply-chain" className="inline-flex items-center gap-1.5">
                  <Package className="w-3.5 h-3.5" />
                  Supply chain
                </Link>
              </Button>
              <Button variant="outline" size="sm" className="h-8" asChild>
                <Link
                  to="/simulation-sales-supply-debate"
                  className="inline-flex items-center gap-1.5"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  Sales vs supply debate
                </Link>
              </Button>
            </div>
          </nav>
        </div>
      </header>

      <main className="container max-w-7xl px-4 md:px-6 py-8 mx-auto">
        <div className="grid lg:grid-cols-[360px_1fr] gap-6 w-full">
          <InputPanel onAnalyze={handleAnalyze} isAnalyzing={isAnalyzing} />

          <div className="space-y-5 min-w-0">
            {!result && !isAnalyzing && !error && (
              <div className="rounded-2xl border-2 border-dashed border-border bg-card/40 p-12 text-center">
                <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-primary flex items-center justify-center shadow-glow mb-4">
                  <Brain className="w-7 h-7 text-primary-foreground" />
                </div>
                <h2 className="text-xl font-semibold text-foreground mb-2">
                  Ready to reason
                </h2>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Enter a strategic question on the left. The engine will pull data, consult specialist agents, debate perspectives, and deliver a decision.
                </p>
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {error}
              </div>
            )}

            {result && (
              <>
                <div className="rounded-xl bg-card border border-border px-4 py-3 shadow-card animate-fade-in-up">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1 flex items-center justify-between">
                    Query
                    {result.routing.routeSource === "fallback" && (
                      <span className="inline-flex items-center gap-1 text-warning">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Backend fallback
                      </span>
                    )}
                  </p>
                  <p className="text-base font-medium text-foreground">"{activeQuery}"</p>
                </div>

                <div className="rounded-2xl bg-card border border-border p-4 shadow-card">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                    Multi-agent thread
                  </p>
                  <div className="space-y-3.5 max-h-[min(52vh,520px)] overflow-y-auto pr-1 scroll-smooth">
                    {shownChat.map((msg) => (
                      <div
                        key={msg.id}
                        className={getChatBubbleClass(msg.actor, msg.label)}
                      >
                        <p
                          className={`text-[11px] font-bold uppercase tracking-wide mb-1.5 ${getLabelAccentClass(msg.label, msg.actor)}`}
                        >
                          {msg.label}
                        </p>
                        <div
                          className={
                            "text-sm leading-relaxed prose prose-sm max-w-none dark:prose-invert " +
                            "prose-p:leading-relaxed prose-pre:bg-muted/80 prose-pre:text-muted-foreground " +
                            "prose-headings:text-foreground prose-strong:text-foreground"
                          }
                        >
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                        </div>
                      </div>
                    ))}
                    {isAnalyzing && (
                      <div className="mr-auto max-w-[40%] rounded-2xl px-4 py-3 border-l-4 border-l-muted-foreground/40 bg-muted/40 border border-border/60">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                          System
                        </p>
                        <p className="text-sm text-muted-foreground">TypingΓÇª</p>
                      </div>
                    )}
                  </div>
                </div>

                <FinalDecision decision={result.decision} />
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Index;
