"use client";

import { useEffect, useState } from "react";
import { format } from "date-fns";
import { Activity, AlertTriangle, Bookmark, Radio, TrendingUp } from "lucide-react";
import type { TenantSignal } from "@/lib/types";
import { getSignals } from "@/lib/api";
import SignalCard from "@/components/SignalCard";
import SignalRadar from "@/components/SignalRadar";
import AlertFeed from "@/components/AlertFeed";
import KnowledgeMap from "@/components/KnowledgeMap";

const MOCK_SIGNALS: TenantSignal[] = [
  {
    signal: {
      id: "sig-001",
      title: "Autonomous AI Agent Frameworks Proliferating",
      description:
        "Multiple open-source frameworks for building autonomous AI agents have emerged in the past quarter. Key players include major tech companies and well-funded startups, signaling a paradigm shift from single-query LLM interactions to persistent, goal-oriented AI systems capable of multi-step reasoning and tool use.",
      signal_type: "strong_signal",
      novelty_score: 0.82,
      momentum_score: 0.91,
      composite_score: 0.88,
      confidence_level: 0.85,
      time_horizon: "short_term",
      impact_domains: ["Enterprise Software", "Automation", "Developer Tools"],
      evidence_ids: ["ev-101", "ev-102", "ev-103"],
      first_detected: "2026-01-15T08:00:00Z",
      last_updated: "2026-03-20T14:30:00Z",
      status: "active",
    },
    relevance_score: 0.94,
    industry_relevance: 0.88,
    competitor_activity: 0.79,
    opportunity_score: 0.91,
    is_dismissed: false,
  },
  {
    signal: {
      id: "sig-002",
      title: "Edge AI Inference Costs Dropping Below Cloud Threshold",
      description:
        "New custom silicon and optimized model architectures are making on-device AI inference cost-competitive with cloud-based solutions for an expanding range of use cases. This trend could fundamentally reshape the economics of AI deployment and data sovereignty strategies.",
      signal_type: "emerging_trend",
      novelty_score: 0.75,
      momentum_score: 0.68,
      composite_score: 0.72,
      confidence_level: 0.71,
      time_horizon: "medium_term",
      impact_domains: ["Hardware", "Cloud Infrastructure", "IoT"],
      evidence_ids: ["ev-201", "ev-202"],
      first_detected: "2026-02-01T10:00:00Z",
      last_updated: "2026-03-18T09:15:00Z",
      status: "active",
    },
    relevance_score: 0.76,
    industry_relevance: 0.69,
    competitor_activity: 0.55,
    opportunity_score: 0.73,
    is_dismissed: false,
  },
  {
    signal: {
      id: "sig-003",
      title: "Photonic Computing for Transformer Inference",
      description:
        "Two independent research groups have published promising results using photonic processors for transformer model inference, achieving 10x energy efficiency improvements. While still at lab stage, this could disrupt the GPU-dominated AI infrastructure market within 3-5 years.",
      signal_type: "weak_signal",
      novelty_score: 0.95,
      momentum_score: 0.35,
      composite_score: 0.58,
      confidence_level: 0.42,
      time_horizon: "long_term",
      impact_domains: ["Semiconductors", "AI Infrastructure", "Energy"],
      evidence_ids: ["ev-301"],
      first_detected: "2026-03-05T16:00:00Z",
      last_updated: "2026-03-19T11:00:00Z",
      status: "active",
    },
    relevance_score: 0.61,
    industry_relevance: 0.54,
    competitor_activity: 0.22,
    opportunity_score: 0.67,
    is_dismissed: false,
  },
  {
    signal: {
      id: "sig-004",
      title: "Synthetic Data Quality Surpassing Real-World Datasets",
      description:
        "Leading AI labs report that models trained on carefully curated synthetic datasets are outperforming those trained on equivalent real-world data for specific domains. This development reduces data acquisition costs and addresses privacy concerns simultaneously.",
      signal_type: "emerging_trend",
      novelty_score: 0.7,
      momentum_score: 0.78,
      composite_score: 0.75,
      confidence_level: 0.68,
      time_horizon: "short_term",
      impact_domains: ["Data Engineering", "Privacy", "Model Training"],
      evidence_ids: ["ev-401", "ev-402"],
      first_detected: "2026-01-20T12:00:00Z",
      last_updated: "2026-03-21T08:45:00Z",
      status: "active",
    },
    relevance_score: 0.81,
    industry_relevance: 0.77,
    competitor_activity: 0.63,
    opportunity_score: 0.79,
    is_dismissed: false,
  },
  {
    signal: {
      id: "sig-005",
      title: "EU AI Act Compliance Tooling Market Explosion",
      description:
        "The approaching enforcement deadlines for the EU AI Act have triggered a surge of compliance tooling startups. Over 40 new tools launched in Q1 2026, creating both a crowded market and significant enterprise demand for integrated governance solutions.",
      signal_type: "strong_signal",
      novelty_score: 0.55,
      momentum_score: 0.89,
      composite_score: 0.78,
      confidence_level: 0.82,
      time_horizon: "immediate",
      impact_domains: ["Regulatory", "GovTech", "Enterprise Software"],
      evidence_ids: ["ev-501", "ev-502", "ev-503", "ev-504"],
      first_detected: "2025-11-10T09:00:00Z",
      last_updated: "2026-03-22T16:00:00Z",
      status: "active",
    },
    relevance_score: 0.85,
    industry_relevance: 0.82,
    competitor_activity: 0.88,
    opportunity_score: 0.72,
    is_dismissed: false,
  },
  {
    signal: {
      id: "sig-006",
      title: "Mixture-of-Experts Models Becoming Default Architecture",
      description:
        "Sparse Mixture-of-Experts architectures are becoming the standard for frontier models, offering better performance per compute dollar. This shift is driving changes in training infrastructure requirements and deployment strategies across the industry.",
      signal_type: "emerging_trend",
      novelty_score: 0.62,
      momentum_score: 0.84,
      composite_score: 0.74,
      confidence_level: 0.79,
      time_horizon: "short_term",
      impact_domains: ["AI Research", "Cloud Infrastructure", "Model Architecture"],
      evidence_ids: ["ev-601", "ev-602"],
      first_detected: "2025-12-01T14:00:00Z",
      last_updated: "2026-03-19T10:30:00Z",
      status: "active",
    },
    relevance_score: 0.78,
    industry_relevance: 0.73,
    competitor_activity: 0.71,
    opportunity_score: 0.68,
    is_dismissed: false,
  },
  {
    signal: {
      id: "sig-007",
      title: "Neuromorphic Computing Startup Funding Wave",
      description:
        "Three neuromorphic computing startups raised Series B rounds exceeding $100M each in Q1 2026. Institutional investors are betting on brain-inspired computing as a complementary paradigm to traditional GPU-based AI acceleration.",
      signal_type: "weak_signal",
      novelty_score: 0.88,
      momentum_score: 0.45,
      composite_score: 0.62,
      confidence_level: 0.51,
      time_horizon: "long_term",
      impact_domains: ["Semiconductors", "VC/Investment", "AI Hardware"],
      evidence_ids: ["ev-701"],
      first_detected: "2026-02-15T11:00:00Z",
      last_updated: "2026-03-17T14:20:00Z",
      status: "active",
    },
    relevance_score: 0.56,
    industry_relevance: 0.48,
    competitor_activity: 0.31,
    opportunity_score: 0.59,
    is_dismissed: false,
  },
  {
    signal: {
      id: "sig-008",
      title: "Cross-Industry AI Safety Consortium Forming",
      description:
        "Major technology companies, financial institutions, and healthcare organizations are establishing a cross-industry consortium focused on AI safety standards and shared evaluation benchmarks, suggesting the industry is moving toward self-regulation ahead of legislation.",
      signal_type: "emerging_trend",
      novelty_score: 0.58,
      momentum_score: 0.72,
      composite_score: 0.66,
      confidence_level: 0.74,
      time_horizon: "medium_term",
      impact_domains: ["AI Safety", "Regulatory", "Industry Collaboration"],
      evidence_ids: ["ev-801", "ev-802"],
      first_detected: "2026-01-28T09:30:00Z",
      last_updated: "2026-03-20T12:00:00Z",
      status: "active",
    },
    relevance_score: 0.71,
    industry_relevance: 0.66,
    competitor_activity: 0.58,
    opportunity_score: 0.63,
    is_dismissed: false,
  },
];

const MOCK_SPARKLINES = [
  [{ value: 0.3 }, { value: 0.4 }, { value: 0.5 }, { value: 0.55 }, { value: 0.7 }, { value: 0.82 }, { value: 0.88 }],
  [{ value: 0.5 }, { value: 0.48 }, { value: 0.55 }, { value: 0.6 }, { value: 0.63 }, { value: 0.68 }, { value: 0.72 }],
  [{ value: 0.1 }, { value: 0.15 }, { value: 0.2 }, { value: 0.28 }, { value: 0.35 }, { value: 0.42 }, { value: 0.58 }],
  [{ value: 0.4 }, { value: 0.45 }, { value: 0.5 }, { value: 0.6 }, { value: 0.65 }, { value: 0.7 }, { value: 0.75 }],
  [{ value: 0.6 }, { value: 0.62 }, { value: 0.68 }, { value: 0.72 }, { value: 0.75 }, { value: 0.76 }, { value: 0.78 }],
];

interface StatCardProps {
  label: string;
  value: string | number;
  change?: string;
  changePositive?: boolean;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

function StatCard({ label, value, change, changePositive, icon: Icon, color }: StatCardProps) {
  return (
    <div className="card animate-slide-up">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</p>
          <p className="stat-number text-white">{value}</p>
          {change && (
            <p
              className={`text-xs mt-1 font-medium ${
                changePositive ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {change}
            </p>
          )}
        </div>
        <div className={`p-2.5 rounded-lg ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardOverview() {
  const [signals, setSignals] = useState<TenantSignal[]>(MOCK_SIGNALS);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchSignals() {
      try {
        setLoading(true);
        const data = await getSignals({ limit: 10 });
        if (data && data.length > 0) {
          setSignals(data);
        }
      } catch {
        // Use mock data on API failure
      } finally {
        setLoading(false);
      }
    }
    fetchSignals();
  }, []);

  const strongCount = signals.filter((s) => s.signal.signal_type === "strong_signal").length;
  const newThisWeek = signals.filter((s) => {
    const detected = new Date(s.signal.first_detected);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return detected >= weekAgo;
  }).length;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Weak Signals Monitor</h1>
          <p className="text-sm text-slate-500 mt-1">
            {format(new Date(), "EEEE, MMMM d, yyyy")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-slate-500">Live monitoring active</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Signals"
          value={signals.length}
          change="+12% vs last month"
          changePositive
          icon={Activity}
          color="bg-blue-500/10 text-blue-400"
        />
        <StatCard
          label="New This Week"
          value={newThisWeek || 3}
          change="+2 since yesterday"
          changePositive
          icon={TrendingUp}
          color="bg-emerald-500/10 text-emerald-400"
        />
        <StatCard
          label="Critical Alerts"
          value={strongCount || 2}
          change="Requires attention"
          changePositive={false}
          icon={AlertTriangle}
          color="bg-red-500/10 text-red-400"
        />
        <StatCard
          label="Watchlist Items"
          value={14}
          change="3 with new activity"
          changePositive
          icon={Bookmark}
          color="bg-amber-500/10 text-amber-400"
        />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Signal Radar - takes 2 cols */}
        <div className="xl:col-span-2 card">
          <h2 className="text-sm font-semibold text-slate-200 mb-4">Signal Radar</h2>
          <p className="text-xs text-slate-500 mb-2">
            Multi-dimensional view of top signals by relevance, novelty, momentum, and opportunity
          </p>
          <SignalRadar signals={signals.slice(0, 8)} />
        </div>

        {/* Alert Feed */}
        <div className="card h-[500px]">
          <AlertFeed />
        </div>
      </div>

      {/* Recent signals + mini map */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Recent signals */}
        <div className="xl:col-span-2 space-y-3">
          <h2 className="text-sm font-semibold text-slate-200">Recent Signals</h2>
          {signals.slice(0, 5).map((ts, idx) => (
            <SignalCard
              key={ts.signal.id}
              tenantSignal={ts}
              compact
              sparklineData={MOCK_SPARKLINES[idx % MOCK_SPARKLINES.length]}
            />
          ))}
        </div>

        {/* Mini knowledge map */}
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-200 mb-3">Knowledge Landscape</h2>
          <p className="text-xs text-slate-500 mb-3">
            AI technology concept map showing relationships and emerging clusters
          </p>
          <div className="h-[300px] rounded-lg overflow-hidden border border-slate-800">
            <KnowledgeMap height={300} />
          </div>
        </div>
      </div>
    </div>
  );
}
