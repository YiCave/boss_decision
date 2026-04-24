import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sparkles, Loader2, Upload, FileText, X, Users, Settings2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface InputPanelProps {
  onAnalyze: (payload: {
    query: string;
    context?: string;
    targetType?: string;
    targetId?: number;
    allowMockFallback: boolean;
    document?: File;
    mode: string;
    forcedAgents?: string[];
  }) => void;
  isAnalyzing: boolean;
}

const SAMPLE_QUERIES = [
  "Should we fire employee #1023?",
  "Should we acquire competitor BetaCorp?",
  "Should we expand to the Singapore market?",
];

const AVAILABLE_AGENTS = [
  { id: "hr", name: "HR", icon: "≡ƒæñ" },
  { id: "sales", name: "Sales", icon: "≡ƒôê" },
  { id: "legal", name: "Legal", icon: "ΓÜû∩╕Å" },
  { id: "marketing", name: "Marketing", icon: "≡ƒôó" },
  { id: "supply_chain", name: "Supply Chain", icon: "≡ƒôª" },
];

export const InputPanel = ({ onAnalyze, isAnalyzing }: InputPanelProps) => {
  const [query, setQuery] = useState("Should we fire employee #1023?");
  const [context, setContext] = useState("");
  /** Empty = no target (org-wide). Avoid defaulting to a non-existent id. */
  const [targetType, setTargetType] = useState("");
  const [targetId, setTargetId] = useState("");
  const [allowMockFallback, setAllowMockFallback] = useState(true);
  const [selectedFile, setSelectedFile] = useState<File | undefined>(undefined);
  
  // Group Chat State
  const [mode, setMode] = useState<"hybrid" | "manual">("hybrid");
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);

  const handleSubmit = () => {
    if (!query.trim() || isAnalyzing) return;
    onAnalyze({
      query: query.trim(),
      context: context.trim() || undefined,
      targetType: targetType.trim() || undefined,
      targetId: targetId.trim() ? Number(targetId) : undefined,
      allowMockFallback,
      document: selectedFile,
      mode,
      forcedAgents: mode === "manual" ? selectedAgents : undefined,
    });
  };

  const toggleAgent = (id: string) => {
    setSelectedAgents(prev => 
      prev.includes(id) ? prev.filter(a => a !== id) : [...prev, id]
    );
  };

  return (
    <aside className="bg-card/90 rounded-3xl shadow-elevated border border-border/70 p-6 h-fit lg:sticky lg:top-6 backdrop-blur-sm">
      <div className="flex items-center gap-2 mb-1">
        <div className="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center shadow-glow">
          <Sparkles className="w-4 h-4 text-primary-foreground" />
        </div>
        <h2 className="text-lg font-semibold text-foreground">Ask the Engine</h2>
      </div>
      <p className="text-sm text-muted-foreground mb-4">
        Pose a strategic decision. Watch the agents reason.
      </p>

      {/* Mode Selection */}
      <div className="mb-4 bg-secondary/50 p-1 rounded-xl flex gap-1 border border-border/50">
        <button
          onClick={() => setMode("hybrid")}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 py-1.5 text-xs font-semibold rounded-lg transition-all",
            mode === "hybrid" ? "bg-background shadow-sm text-primary" : "text-muted-foreground hover:text-foreground"
          )}
        >
          <Sparkles className="w-3.5 h-3.5" />
          Hybrid Mode
        </button>
        <button
          onClick={() => setMode("manual")}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 py-1.5 text-xs font-semibold rounded-lg transition-all",
            mode === "manual" ? "bg-background shadow-sm text-primary" : "text-muted-foreground hover:text-foreground"
          )}
        >
          <Users className="w-3.5 h-3.5" />
          Manual Select
        </button>
      </div>

      {/* Agent Selection (Only in Manual mode) */}
      {mode === "manual" && (
        <div className="mb-4 animate-in fade-in slide-in-from-top-2 duration-300">
          <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-2 block">
            Select Chat Participants
          </label>
          <div className="flex flex-wrap gap-1.5">
            {AVAILABLE_AGENTS.map(agent => (
              <button
                key={agent.id}
                onClick={() => toggleAgent(agent.id)}
                className={cn(
                  "px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-all flex items-center gap-1.5",
                  selectedAgents.includes(agent.id) 
                    ? "bg-primary/10 border-primary/40 text-primary shadow-sm" 
                    : "bg-background border-border text-muted-foreground hover:border-muted-foreground"
                )}
              >
                <span>{agent.icon}</span>
                {agent.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Decision query
      </label>
      <Textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="e.g. Should we fire employee #1023?"
        className="mt-2 min-h-[120px] resize-none text-base bg-background border-border focus-visible:ring-primary shadow-inner-sm"
        disabled={isAnalyzing}
      />

      <div className="mt-3 rounded-xl border border-dashed border-border bg-background/70 p-3">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Upload file for analysis
        </p>
        <label className="flex items-center justify-center gap-2 rounded-lg bg-secondary px-3 py-2 text-sm text-secondary-foreground cursor-pointer hover:bg-accent hover:text-accent-foreground transition-smooth border border-border/50">
          <Upload className="w-4 h-4" />
          Choose file
          <input
            type="file"
            className="hidden"
            onChange={(e) => setSelectedFile(e.target.files?.[0])}
            disabled={isAnalyzing}
          />
        </label>

        {selectedFile && (
          <div className="mt-2 flex items-center justify-between rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground">
            <span className="inline-flex items-center gap-1.5 truncate pr-2">
              <FileText className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">{selectedFile.name}</span>
            </span>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground"
              onClick={() => setSelectedFile(undefined)}
              disabled={isAnalyzing}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Advanced Settings */}
      <div className="mt-4 pt-4 border-t border-border/40">
        <div className="flex items-center gap-1.5 mb-3">
          <Settings2 className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Targeting Info</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <input
            value={targetType}
            onChange={(e) => setTargetType(e.target.value)}
            placeholder="target_type (e.g. employee, or empty)"
            className="h-10 rounded-lg border border-border bg-background px-3 text-sm focus:ring-1 focus:ring-primary outline-none"
            disabled={isAnalyzing}
          />
          <input
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            placeholder="target_id (or empty for org-wide)"
            className="h-10 rounded-lg border border-border bg-background px-3 text-sm focus:ring-1 focus:ring-primary outline-none"
            disabled={isAnalyzing}
          />
        </div>
      </div>

      <Textarea
        value={context}
        onChange={(e) => setContext(e.target.value)}
        placeholder="Optional context for routing"
        className="mt-3 min-h-[72px] resize-none text-sm bg-background border-border"
        disabled={isAnalyzing}
      />

      <label className="mt-4 flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
        <input
          type="checkbox"
          className="rounded border-border text-primary focus:ring-primary"
          checked={allowMockFallback}
          onChange={(e) => setAllowMockFallback(e.target.checked)}
          disabled={isAnalyzing}
        />
        Enable mock fallback
      </label>

      <Button
        onClick={handleSubmit}
        disabled={isAnalyzing || !query.trim() || (mode === "manual" && selectedAgents.length === 0)}
        className="w-full mt-4 h-11 bg-gradient-primary text-primary-foreground font-bold shadow-elevated hover:shadow-glow transition-all active:scale-[0.98] border-0"
      >
        {isAnalyzing ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            AnalyzingΓÇª
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4 mr-2" />
            Analyze Decision
          </>
        )}
      </Button>

      <div className="mt-6 pt-6 border-t border-border">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
          Quick access
        </p>
        <div className="flex flex-col gap-2">
          {SAMPLE_QUERIES.map((s) => (
            <button
              key={s}
              onClick={() => !isAnalyzing && setQuery(s)}
              disabled={isAnalyzing}
              className="text-left text-sm px-3 py-2 rounded-lg bg-secondary/80 hover:bg-accent hover:text-accent-foreground transition-smooth text-secondary-foreground disabled:opacity-50 border border-transparent hover:border-border"
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
};
