export interface Signal {
  id: string;
  title: string;
  description: string | null;
  cluster: string | null;
  signal_type: "noise" | "weak_signal" | "emerging_trend" | "strong_signal";
  novelty_score: number;
  momentum_score: number;
  composite_score: number;
  confidence_level: number;
  time_horizon: string | null;
  impact_domains: string[] | null;
  evidence_ids: string[] | null;
  first_detected: string;
  last_updated: string;
  status: "active" | "archived" | "dismissed" | "confirmed";
}

export interface TenantSignal {
  id: string;
  tenant_id: string;
  signal_id: string;
  signal: Signal;
  relevance_score: number;
  industry_relevance: number;
  competitor_activity: number;
  opportunity_score: number;
  is_dismissed: boolean;
  created_at: string;
}

export interface SignalTrajectoryPoint {
  timestamp: string;
  metric_name: string;
  value: number;
}

export interface Tenant {
  id: string;
  name: string;
  industry_verticals: string[];
  technology_watchlist: string[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  size: number;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  type: string;
}

export interface LandscapeData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface WeeklyDigest {
  tenant_name: string;
  period: { start: string; end: string };
  summary: {
    total_active_signals: number;
    new_this_week: number;
    trending: number;
  };
  cluster_breakdown: Record<string, number>;
  top_signals: DigestSignalBrief[];
  new_signals: DigestSignalBrief[];
  trending_signals: DigestSignalBrief[];
  ai_summary: AISummary | null;
  watchlist: string[];
}

export interface DigestSignalBrief {
  id: string;
  title: string;
  description: string | null;
  cluster: string | null;
  cluster_name: string;
  signal_type: string;
  composite_score: number;
  novelty_score: number;
  momentum_score: number;
  confidence_level: number;
  status: string;
  first_detected: string | null;
  relevance_score: number;
  industry_relevance: number;
  competitor_activity: number;
  opportunity_score: number;
}

export interface AISummary {
  key_insights: string[];
  recommendations: string[];
  risk_alerts: string[];
  opportunities: string[];
}

export interface SourceDocument {
  id: string;
  external_id: string | null;
  source: string;
  title: string;
  abstract: string | null;
  authors: Record<string, unknown> | unknown[] | null;
  published_date: string | null;
  url: string | null;
}

export const SOURCE_LABELS: Record<string, string> = {
  pubmed: "PubMed",
  openalex: "OpenAlex",
  arxiv: "arXiv",
  clinicaltrials: "ClinicalTrials.gov",
  rss: "Новости",
};

export const CLUSTER_NAMES: Record<string, string> = {
  ai_drug_discovery: "AI в разработке лекарств",
  oncology: "Онкология нового поколения",
  biosimilars: "Биоаналоги и биосимиляры",
  regulatory: "Регуляторика и GMP",
  competitors_ru: "Конкуренты РФ",
  export_markets: "Китай и экспортные рынки",
};

export const SIGNAL_TYPE_LABELS: Record<string, string> = {
  noise: "Шум",
  weak_signal: "Слабый сигнал",
  emerging_trend: "Зарождающийся тренд",
  strong_signal: "Сильный сигнал",
};
