import { CheckCircle2, AlertTriangle, Gauge, Shield, Flame } from "lucide-react";
import { Decision } from "@/lib/decision-engine";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  decision: Decision;
}

const riskPill = {
  Low: "text-success border-success/40 bg-success/10",
  Medium: "text-warning border-warning/40 bg-warning/10",
  High: "text-destructive border-destructive/40 bg-destructive/10",
} as const;

export const FinalDecision = ({ decision }: Props) => {
  const riskKey = (["Low", "Medium", "High"] as const).includes(decision.risk as "Low" | "Medium" | "High")
    ? (decision.risk as keyof typeof riskPill)
    : "Medium";
  const riskColor = riskPill[riskKey];
  const hasViews = decision.conservativeView || decision.aggressiveView;

  return (
    <section className="relative rounded-xl bg-gradient-decision text-primary-foreground p-4 shadow-elevated animate-scale-in overflow-hidden flex flex-col gap-3">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_hsl(var(--primary-glow)/0.3),_transparent_50%)] pointer-events-none" />

      <div className="relative flex flex-col gap-3">
        {/* Header */}
        <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider opacity-85">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
          <span>Final Decision</span>
        </div>

        {/* Verdict */}
        <p className="text-sm sm:text-base font-semibold leading-snug max-w-4xl" title={decision.verdict}>
          {decision.verdict}
        </p>

        {/* Manager synthesis */}
        {decision.reasoning && (
          <div className="prose prose-sm dark:prose-invert max-w-3xl text-primary-foreground/90 leading-normal text-[13px] [&_p]:my-1">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{decision.reasoning}</ReactMarkdown>
          </div>
        )}

        {/* Conservative vs Aggressive perspectives */}
        {hasViews && (
          <div className="grid sm:grid-cols-2 gap-2.5 pt-1">
            {decision.conservativeView && (
              <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-3.5 flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-blue-500/70 shrink-0">
                    <Shield className="w-3.5 h-3.5 text-white" />
                  </div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-primary-foreground/80">
                    Conservative Perspective
                  </span>
                </div>
                <p className="text-[13px] text-primary-foreground/80 leading-relaxed">
                  {decision.conservativeView}
                </p>
              </div>
            )}
            {decision.aggressiveView && (
              <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-3.5 flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-red-500/70 shrink-0">
                    <Flame className="w-3.5 h-3.5 text-white" />
                  </div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-primary-foreground/80">
                    Aggressive Perspective
                  </span>
                </div>
                <p className="text-[13px] text-primary-foreground/80 leading-relaxed">
                  {decision.aggressiveView}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Risk & Confidence */}
        <div className="grid grid-cols-2 gap-2 pt-0.5">
          <div className="rounded-lg border border-border/20 bg-background/90 backdrop-blur-sm p-2.5">
            <div className="flex items-center gap-1.5 text-foreground/70 text-[10px] font-semibold uppercase tracking-wide mb-1">
              <AlertTriangle className="w-3 h-3" />
              Risk
            </div>
            <div className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-bold text-foreground ${riskColor}`}>
              {decision.risk}
            </div>
          </div>

          <div className="rounded-lg border border-border/20 bg-background/90 backdrop-blur-sm p-2.5">
            <div className="flex items-center gap-1.5 text-foreground/70 text-[10px] font-semibold uppercase tracking-wide mb-1">
              <Gauge className="w-3 h-3" />
              Confidence
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-foreground tabular-nums">
                {decision.confidence}%
              </span>
              <div className="flex-1 h-1 bg-secondary rounded-full overflow-hidden min-w-0">
                <div
                  className="h-full bg-gradient-primary rounded-full transition-all duration-1000"
                  style={{ width: `${decision.confidence}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
