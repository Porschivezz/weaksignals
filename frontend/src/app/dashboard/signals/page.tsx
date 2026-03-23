"use client";

import { useState, useEffect, useCallback } from "react";
import { Filter, X, ChevronDown } from "lucide-react";
import type { TenantSignal, Signal } from "@/lib/types";
import { getSignals, dismissSignal } from "@/lib/api";
import SignalCard from "@/components/SignalCard";
import ScoreBar from "@/components/ScoreBar";
import TrendSparkline from "@/components/TrendSparkline";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

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
  {
    signal: {
      id: "sig-009",
      title: "Real-Time Multimodal Reasoning in Production",
      description:
        "Several production systems now demonstrate real-time multimodal reasoning combining vision, audio, and text understanding in unified inference passes. Latency improvements enable interactive applications previously considered impractical.",
      signal_type: "strong_signal",
      novelty_score: 0.72,
      momentum_score: 0.85,
      composite_score: 0.8,
      confidence_level: 0.78,
      time_horizon: "immediate",
      impact_domains: ["Computer Vision", "NLP", "Product Design"],
      evidence_ids: ["ev-901", "ev-902"],
      first_detected: "2026-02-10T08:00:00Z",
      last_updated: "2026-03-22T10:00:00Z",
      status: "active",
    },
    relevance_score: 0.87,
    industry_relevance: 0.81,
    competitor_activity: 0.76,
    opportunity_score: 0.84,
    is_dismissed: false,
  },
  {
    signal: {
      id: "sig-010",
      title: "Biological Neural Network Interfaces for AI Training",
      description:
        "University researchers demonstrated using organoid neural networks as co-processors for specific AI training tasks. While highly experimental, the approach shows unexpected efficiency gains in pattern recognition training.",
      signal_type: "weak_signal",
      novelty_score: 0.98,
      momentum_score: 0.15,
      composite_score: 0.45,
      confidence_level: 0.28,
      time_horizon: "long_term",
      impact_domains: ["Biotech", "AI Research", "Ethics"],
      evidence_ids: ["ev-1001"],
      first_detected: "2026-03-10T14:00:00Z",
      last_updated: "2026-03-18T16:30:00Z",
      status: "active",
    },
    relevance_score: 0.38,
    industry_relevance: 0.25,
    competitor_activity: 0.08,
    opportunity_score: 0.42,
    is_dismissed: false,
  },
];

function generateTrajectory(signal: Signal): { date: string; score: number }[] {
  const points = [];
  const base = signal.composite_score * 0.5;
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i * 7);
    const noise = (Math.random() - 0.4) * 0.1;
    const growth = (6 - i) * (signal.momentum_score * 0.08);
    points.push({
      date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      score: Math.min(1, Math.max(0, base + growth + noise)),
    });
  }
  return points;
}

export default function SignalsPage() {
  const [signals, setSignals] = useState<TenantSignal[]>(MOCK_SIGNALS);
  const [filterType, setFilterType] = useState<string>("all");
  const [minScore, setMinScore] = useState(0);
  const [selectedSignal, setSelectedSignal] = useState<TenantSignal | null>(null);
  const [showFilters, setShowFilters] = useState(true);

  useEffect(() => {
    async function fetchSignals() {
      try {
        const params: Record<string, string | number> = { limit: 50 };
        if (filterType !== "all") params.signal_type = filterType;
        if (minScore > 0) params.min_score = minScore;
        const data = await getSignals(params);
        if (data && data.length > 0) {
          setSignals(data);
        }
      } catch {
        // Use mock data
      }
    }
    fetchSignals();
  }, [filterType, minScore]);

  const filteredSignals = signals.filter((ts) => {
    if (filterType !== "all" && ts.signal.signal_type !== filterType) return false;
    if (ts.signal.composite_score < minScore) return false;
    if (ts.is_dismissed) return false;
    return true;
  });

  const handleDismiss = useCallback(async (id: string) => {
    try {
      await dismissSignal(id);
    } catch {
      // Dismiss locally on API failure
    }
    setSignals((prev) =>
      prev.map((ts) =>
        ts.signal.id === id ? { ...ts, is_dismissed: true } : ts
      )
    );
    if (selectedSignal?.signal.id === id) setSelectedSignal(null);
  }, [selectedSignal]);

  const trajectory = selectedSignal ? generateTrajectory(selectedSignal.signal) : [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Signal Intelligence</h1>
          <p className="text-sm text-slate-500 mt-1">
            {filteredSignals.length} active signals detected across monitored sources
          </p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="btn-secondary"
        >
          <Filter className="w-4 h-4 mr-2" />
          Filters
        </button>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="card animate-slide-up">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Signal type */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                Signal Type
              </label>
              <div className="relative">
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="input-field appearance-none pr-10"
                >
                  <option value="all">All Types</option>
                  <option value="weak_signal">Weak Signals</option>
                  <option value="emerging_trend">Emerging Trends</option>
                  <option value="strong_signal">Strong Signals</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
              </div>
            </div>

            {/* Min score slider */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                Minimum Score: {(minScore * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={minScore}
                onChange={(e) => setMinScore(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>

            {/* Time range presets */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                Time Range
              </label>
              <div className="flex gap-2">
                {["7d", "30d", "90d", "All"].map((range) => (
                  <button
                    key={range}
                    className="btn-ghost text-xs px-3 py-1.5 border border-slate-700 rounded-lg"
                  >
                    {range}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Content area */}
      <div className="flex gap-6">
        {/* Signal grid */}
        <div className={`flex-1 grid gap-4 ${selectedSignal ? "grid-cols-1 lg:grid-cols-2" : "grid-cols-1 md:grid-cols-2 xl:grid-cols-3"}`}>
          {filteredSignals.map((ts) => (
            <SignalCard
              key={ts.signal.id}
              tenantSignal={ts}
              onDismiss={handleDismiss}
              onClick={() => setSelectedSignal(ts)}
            />
          ))}
          {filteredSignals.length === 0 && (
            <div className="col-span-full text-center py-16">
              <p className="text-slate-500 text-sm">No signals match your current filters.</p>
              <button
                onClick={() => {
                  setFilterType("all");
                  setMinScore(0);
                }}
                className="btn-ghost mt-3"
              >
                Clear filters
              </button>
            </div>
          )}
        </div>

        {/* Detail panel */}
        {selectedSignal && (
          <div className="hidden xl:block w-[420px] shrink-0">
            <div className="card sticky top-8 animate-slide-right">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-300">Signal Detail</h3>
                <button
                  onClick={() => setSelectedSignal(null)}
                  className="text-slate-500 hover:text-slate-300 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <h2 className="text-lg font-bold text-white mb-3">
                {selectedSignal.signal.title}
              </h2>

              <p className="text-sm text-slate-400 leading-relaxed mb-6">
                {selectedSignal.signal.description}
              </p>

              {/* Trajectory chart */}
              <div className="mb-6">
                <h4 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">
                  Score Trajectory (7 weeks)
                </h4>
                <div className="h-48 bg-slate-800/50 rounded-lg p-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trajectory}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: "#64748b", fontSize: 10 }}
                        axisLine={{ stroke: "#334155" }}
                      />
                      <YAxis
                        domain={[0, 1]}
                        tick={{ fill: "#64748b", fontSize: 10 }}
                        axisLine={{ stroke: "#334155" }}
                        tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#1e293b",
                          border: "1px solid #334155",
                          borderRadius: "8px",
                          fontSize: "12px",
                          color: "#e2e8f0",
                        }}
                        formatter={(value: number) => [
                          `${(value * 100).toFixed(1)}%`,
                          "Score",
                        ]}
                      />
                      <Line
                        type="monotone"
                        dataKey="score"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={{ r: 3, fill: "#3b82f6" }}
                        activeDot={{ r: 5, fill: "#60a5fa" }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Scores */}
              <div className="space-y-3 mb-6">
                <ScoreBar label="Novelty" value={selectedSignal.signal.novelty_score} color="cyan" />
                <ScoreBar label="Momentum" value={selectedSignal.signal.momentum_score} color="blue" />
                <ScoreBar label="Relevance" value={selectedSignal.relevance_score} color="amber" />
                <ScoreBar label="Competitor Activity" value={selectedSignal.competitor_activity} color="red" />
                <ScoreBar label="Opportunity" value={selectedSignal.opportunity_score} color="emerald" />
              </div>

              {/* Meta */}
              <div className="space-y-2 text-xs text-slate-500 border-t border-slate-800 pt-4">
                <div className="flex justify-between">
                  <span>First detected</span>
                  <span className="text-slate-400">
                    {new Date(selectedSignal.signal.first_detected).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Last updated</span>
                  <span className="text-slate-400">
                    {new Date(selectedSignal.signal.last_updated).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Confidence</span>
                  <span className="text-slate-400">
                    {(selectedSignal.signal.confidence_level * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Evidence sources</span>
                  <span className="text-slate-400">
                    {selectedSignal.signal.evidence_ids.length}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 mt-6">
                <button
                  onClick={() => handleDismiss(selectedSignal.signal.id)}
                  className="btn-secondary flex-1 text-xs"
                >
                  Dismiss
                </button>
                <button className="btn-primary flex-1 text-xs">Add to Watchlist</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
