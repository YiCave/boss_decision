import { CheckCircle2, AlertTriangle, Gauge } from "lucide-react";
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

  return (
    <section className="relative rounded-xl bg-gradient-decision text-primary-foreground p-3.5 sm:p-4 shadow-elevated animate-scale-in overflow-hidden max-h-[min(70vh,540px)] flex flex-col">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_hsl(var(--primary-glow)/0.3),_transparent_50%)]" />

      <div className="relative min-h-0 flex flex-col gap-2">
        <div className="flex items-center gap-1.5 flex-shrink-0 text-[10px] font-bold uppercase tracking-wider opacity-85">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
          <span>Final decision</span>
        </div>

        <p
          className="text-sm sm:text-base font-semibold leading-snug flex-shrink-0 max-w-4xl line-clamp-3"
          title={decision.verdict}
        >
          {decision.verdict}
        </p>

        <div className="prose prose-sm dark:prose-invert max-w-3xl text-primary-foreground/90 leading-normal min-h-0 max-h-[30vh] sm:max-h-[28vh] overflow-y-auto pr-0.5 text-[13px] [&_p]:my-1.5">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{decision.reasoning}</ReactMarkdown>
        </div>

        <div className="grid grid-cols-2 gap-2 flex-shrink-0 pt-0.5">
          <div className="rounded-lg border border-border/20 bg-background/90 backdrop-blur-sm p-2.5">
            <div className="flex items-center gap-1.5 text-foreground/70 text-[10px] font-semibold uppercase tracking-wide mb-1">
              <AlertTriangle className="w-3 h-3" />
              Risk
            </div>
            <div
              className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-bold text-foreground ${riskColor}`}
            >
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
