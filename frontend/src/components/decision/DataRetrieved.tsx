import { Database } from "lucide-react";
import { StageCard } from "./StageCard";
import { DataItem } from "@/lib/decision-engine";

interface Props {
  status: "pending" | "loading" | "done";
  items: DataItem[];
}

export const DataRetrieved = ({ status, items }: Props) => {
  return (
    <StageCard
      icon={<Database className="h-5 w-5" />}
      title="Data Retrieved"
      subtitle="Cross-system signals pulled in real time"
      status={status}
    >
      <div className="grid gap-3 sm:grid-cols-3">
        {items.map((item, i) => (
          <div
            key={item.source}
            className="animate-fade-in-up rounded-xl border border-border bg-background/80 p-4"
            style={{ animationDelay: `${i * 100}ms` }}
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">{item.source}</span>
              <span
                className={
                  item.trend === "down"
                    ? "text-destructive text-xs font-medium"
                    : item.trend === "up"
                      ? "text-success text-xs font-medium"
                      : "text-muted-foreground text-xs font-medium"
                }
              >
                {item.trend === "down" ? "v" : item.trend === "up" ? "^" : "-"}
              </span>
            </div>
            <p className="text-xl font-semibold leading-tight text-foreground">{item.value}</p>
            <p className="mt-1 text-xs text-muted-foreground">{item.label}</p>
          </div>
        ))}
      </div>
    </StageCard>
  );
};
