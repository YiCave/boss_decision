export interface SalesCampaignRequest {
  product: string;
  region?: string;
}

export interface WeekAction {
  day: number;
  action: string;
}

export interface CampaignSuggestion {
  type: "campaign" | "event";
  title: string;
  objective: string;
  why_now: string;
  channels: string[];
  next_week_plan: WeekAction[];
  success_metric: string;
  sources: string[];
}

export interface NewsSignal {
  title: string;
  url: string;
  source: string;
  published_date?: string;
  summary: string;
  score: number;
}

export interface SalesCampaignResponse {
  product: string;
  region: string;
  search_query: string;
  generated_at: string;
  hints: string[];
  news_signals: NewsSignal[];
  suggestions: CampaignSuggestion[];
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getSalesCampaignSuggestions(
  request: SalesCampaignRequest,
): Promise<SalesCampaignResponse> {
  const response = await fetch(`${API_BASE}/api/sales/campaign-suggestions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let message = `Sales campaign request failed (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Keep generic message when server response is not JSON.
    }
    throw new Error(message);
  }

  return (await response.json()) as SalesCampaignResponse;
}
