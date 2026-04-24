import { ReactNode } from "react";
import { Loader2, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface StageCardProps {
  icon: ReactNode;
  title: string;
  subtitle?: string;
  status: "pending" | "loading" | "done";
  children?: ReactNode;
  accent?: "primary" | "accent" | "warning";
}

export const StageCard = ({
  icon,
  title,
  subtitle,
  status,
  children,
  accent = "primary",
}: StageCardProps) => {
  if (status === "pending") return null;

  const accentRing = {
    primary: "ring-primary/20",
    accent: "ring-accent/25",
    warning: "ring-warning/25",
  }[accent];

  const accentBadge = {
    primary: "text-primary bg-primary/10",
    accent: "text-accent bg-accent/10",
    warning: "text-warning bg-warning/10",
  }[accent];

  return (
    <section className={cn("rounded-[1.4rem] border border-border bg-card/85 p-6 shadow-card ring-1 animate-fade-in-up", accentRing)}>
      <header className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl", accentBadge)}>{icon}</div>
          <div>
            <h3 className="text-3xl leading-none text-foreground">{title}</h3>
            {subtitle && <p className="mt-1 text-xs uppercase tracking-[0.16em] text-muted-foreground">{subtitle}</p>}
          </div>
        </div>
        <div>
          {status === "loading" ? (
            <div className="flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-primary">
              <Loader2 className="h-3 w-3 animate-spin" />
              Working
            </div>
          ) : (
            <div className="flex items-center gap-1.5 rounded-full bg-success/10 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-success">
              <Check className="h-3 w-3" />
              Done
            </div>
          )}
        </div>
      </header>

      {status === "done" && <div className="space-y-3">{children}</div>}
      {status === "loading" && (
        <div className="space-y-2">
          <div className="h-3 w-3/4 animate-pulse-glow rounded bg-secondary" />
          <div className="h-3 w-1/2 animate-pulse-glow rounded bg-secondary" />
        </div>
      )}
    </section>
  );
};
