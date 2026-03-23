export interface Signal {
  id: string;
  title: string;
  description: string;
  signal_type: "weak_signal" | "emerging_trend" | "strong_signal";
  novelty_score: number;
  momentum_score: number;
  composite_score: number;
  confidence_level: number;
  time_horizon: "immediate" | "short_term" | "medium_term" | "long_term";
  impact_domains: string[];
  evidence_ids: string[];
  first_detected: string;
  last_updated: string;
  status: "active" | "archived" | "dismissed" | "confirmed";
}

export interface TenantSignal {
  signal: Signal;
  relevance_score: number;
  industry_relevance: number;
  competitor_activity: number;
  opportunity_score: number;
  is_dismissed: boolean;
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
  period: string;
  signals: TenantSignal[];
  summary: string;
}
