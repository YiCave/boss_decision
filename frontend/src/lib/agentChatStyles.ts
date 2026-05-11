import type { ChatMessage } from "./decision-engine";

/**
 * Per-role chat bubble look (left accent + soft fill). Extensible for future agents.
 * Labels are typically "Sales Agent", "Manager Router", etc.
 */
export function getChatBubbleClass(actor: ChatMessage["actor"], label: string): string {
  const l = (label || "").toLowerCase();

  const baseLeft = "max-w-[85%] rounded-2xl px-4 py-3 text-left border shadow-sm";

  if (actor === "user") {
    return `ml-auto ${baseLeft} bg-primary text-primary-foreground border-border/0`;
  }

  if (actor === "manager_router") {
    return `mr-auto ${baseLeft} border-l-4 border-l-violet-500 bg-violet-500/10 dark:bg-violet-500/15 text-foreground border border-violet-500/20`;
  }

  if (actor === "manager_tldr") {
    return `mr-auto ${baseLeft} border-l-4 border-l-emerald-500 bg-emerald-500/10 dark:bg-emerald-500/15 text-foreground border border-emerald-500/25`;
  }

  if (actor === "system") {
    if (l.includes("document")) {
      return `mr-auto ${baseLeft} border-l-4 border-l-zinc-500 bg-zinc-500/10 dark:bg-zinc-500/15 text-foreground border border-zinc-500/20`;
    }
    return `mr-auto ${baseLeft} border-l-4 border-l-slate-500 bg-slate-500/10 dark:bg-slate-500/15 text-foreground border border-slate-500/20`;
  }

  if (actor === "agent") {
    if (l.includes("sales")) {
      return `mr-auto ${baseLeft} border-l-4 border-l-sky-500 bg-sky-500/10 dark:bg-sky-500/20 text-foreground border border-sky-500/20`;
    }
    if (l.includes("marketing")) {
      return `mr-auto ${baseLeft} border-l-4 border-l-fuchsia-500 bg-fuchsia-500/10 dark:bg-fuchsia-500/15 text-foreground border border-fuchsia-500/20`;
    }
    if (l.includes("hr") || l.includes("human")) {
      return `mr-auto ${baseLeft} border-l-4 border-l-teal-600 bg-teal-500/10 dark:bg-teal-500/15 text-foreground border border-teal-500/25`;
    }
    if (l.includes("legal")) {
      return `mr-auto ${baseLeft} border-l-4 border-l-slate-600 bg-slate-500/10 dark:bg-slate-500/15 text-foreground border border-slate-500/25`;
    }
    if (l.includes("finance")) {
      return `mr-auto ${baseLeft} border-l-4 border-l-amber-500 bg-amber-500/10 dark:bg-amber-500/15 text-foreground border border-amber-500/25`;
    }
    if (l.includes("supply") || l.includes("chain")) {
      return `mr-auto ${baseLeft} border-l-4 border-l-orange-500 bg-orange-500/10 dark:bg-orange-500/15 text-foreground border border-orange-500/20`;
    }
    if (l.includes("operation") || l.includes("ops")) {
      return `mr-auto ${baseLeft} border-l-4 border-l-cyan-500 bg-cyan-500/10 dark:bg-cyan-500/15 text-foreground border border-cyan-500/20`;
    }
    if (l.includes("product") || l.includes("engineer") || l.includes("tech")) {
      return `mr-auto ${baseLeft} border-l-4 border-l-indigo-500 bg-indigo-500/10 dark:bg-indigo-500/15 text-foreground border border-indigo-500/20`;
    }
    if (l.includes("data") || l.includes("analytic")) {
      return `mr-auto ${baseLeft} border-l-4 border-l-rose-500 bg-rose-500/10 dark:bg-rose-500/15 text-foreground border border-rose-500/20`;
    }
    if (l.includes("customer") || l.includes("success")) {
      return `mr-auto ${baseLeft} border-l-4 border-l-pink-500 bg-pink-500/10 dark:bg-pink-500/15 text-foreground border border-pink-500/20`;
    }
    return `mr-auto ${baseLeft} border-l-4 border-l-violet-400 bg-violet-500/10 dark:bg-violet-500/12 text-foreground border border-violet-500/20`;
  }

  return `mr-auto ${baseLeft} bg-amber-500/10 border border-amber-500/25 text-foreground`;
}

/** Muted but readable label color to pair with the bubble */
export function getLabelAccentClass(label: string, actor: ChatMessage["actor"]): string {
  const l = (label || "").toLowerCase();
  if (actor === "user") return "text-primary-foreground/90";
  if (actor === "manager_router") return "text-violet-800 dark:text-violet-200";
  if (actor === "manager_tldr") return "text-emerald-800 dark:text-emerald-200";
  if (actor === "system") {
    if (l.includes("document")) return "text-zinc-700 dark:text-zinc-200";
    return "text-slate-700 dark:text-slate-200";
  }
  if (l.includes("sales")) return "text-sky-800 dark:text-sky-200";
  if (l.includes("marketing")) return "text-fuchsia-800 dark:text-fuchsia-200";
  if (l.includes("hr") || l.includes("human")) return "text-teal-800 dark:text-teal-200";
  if (l.includes("legal")) return "text-slate-800 dark:text-slate-200";
  if (l.includes("finance")) return "text-amber-800 dark:text-amber-200";
  if (l.includes("supply") || l.includes("chain")) return "text-orange-800 dark:text-orange-200";
  if (l.includes("operation") || l.includes("ops")) return "text-cyan-800 dark:text-cyan-200";
  if (l.includes("product") || l.includes("engineer") || l.includes("tech")) return "text-indigo-800 dark:text-indigo-200";
  if (l.includes("data") || l.includes("analytic")) return "text-rose-800 dark:text-rose-200";
  if (l.includes("customer") || l.includes("success")) return "text-pink-800 dark:text-pink-200";
  if (actor === "agent") return "text-violet-800 dark:text-violet-200";
  return "text-muted-foreground";
}
