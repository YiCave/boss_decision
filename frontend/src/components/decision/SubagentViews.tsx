import { Brain, Shield, Flame } from "lucide-react";
import { StageCard } from "./StageCard";
import { SubagentView } from "@/lib/decision-engine";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  status: "pending" | "loading" | "done";
  views: SubagentView[];
}

export const SubagentViews = ({ status, views }: Props) => {
  return (
    <StageCard
      icon={<Brain className="w-5 h-5" />}
      title="Subagent Perspectives"
      subtitle="Two minds, two strategies ΓÇö debating in parallel"
      status={status}
      accent="warning"
    >
      <div className="grid sm:grid-cols-2 gap-3">
        {views.map((v, i) => {
          const isConservative = v.stance === "conservative";
          return (
            <div
              key={v.stance}
              className="relative rounded-xl border-2 p-5 animate-fade-in-up overflow-hidden"
              style={{
                animationDelay: `${i * 150}ms`,
                borderColor: isConservative ? "hsl(var(--conservative))" : "hsl(var(--aggressive))",
                background: isConservative
                  ? "hsl(var(--conservative) / 0.05)"
                  : "hsl(var(--aggressive) / 0.05)",
              }}
            >
              <div className="flex items-center gap-2 mb-3">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-primary-foreground"
                  style={{
                    background: isConservative
                      ? "hsl(var(--conservative))"
                      : "hsl(var(--aggressive))",
                  }}
                >
                  {isConservative ? (
                    <Shield className="w-4 h-4" />
                  ) : (
                    <Flame className="w-4 h-4" />
                  )}
                </div>
                <span className="text-sm font-bold uppercase tracking-wide text-foreground">
                  {isConservative ? "Conservative" : "Aggressive"}
                </span>
              </div>
              <p className="text-base font-semibold text-foreground mb-1">{v.recommendation}</p>
              <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{v.reasoning}</ReactMarkdown>
              </div>
            </div>
          );
        })}
      </div>
    </StageCard>
  );
};
