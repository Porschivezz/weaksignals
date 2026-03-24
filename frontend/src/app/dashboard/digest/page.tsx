"use client";

import { useState, useEffect } from "react";
import { format, subDays } from "date-fns";
import { Download, Share2, Calendar, ChevronDown, TrendingUp, AlertTriangle, Radio } from "lucide-react";
import type { TenantSignal } from "@/lib/types";
import { getDigest } from "@/lib/api";
import SignalCard from "@/components/SignalCard";
import ScoreBar from "@/components/ScoreBar";

const MOCK_DIGEST_SIGNALS: TenantSignal[] = [
  {
    signal: {
      id: "d-001",
      title: "Autonomous AI Agent Frameworks Proliferating",
      description:
        "Multiple open-source frameworks for building autonomous AI agents have emerged in the past quarter. Major tech companies and well-funded startups are building persistent, goal-oriented AI systems with multi-step reasoning and tool use capabilities. This represents a fundamental shift in how enterprises will interact with AI systems.",
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
      id: "d-002",
      title: "EU AI Act Compliance Tooling Market Explosion",
      description:
        "The approaching enforcement deadlines for the EU AI Act have triggered a surge of compliance tooling startups. Over 40 new tools launched in Q1 2026, creating both a crowded market and significant enterprise demand for integrated governance solutions. Companies without compliance strategies face significant regulatory risk.",
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
      id: "d-003",
      title: "Synthetic Data Quality Surpassing Real-World Datasets",
      description:
        "Leading AI labs report that models trained on carefully curated synthetic datasets are outperforming those trained on equivalent real-world data for specific domains. This trend reduces data acquisition costs and addresses privacy concerns, potentially disrupting the data marketplace.",
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
      id: "d-004",
      title: "Edge AI Inference Costs Dropping Below Cloud Threshold",
      description:
        "New custom silicon and optimized model architectures are making on-device AI inference cost-competitive with cloud-based solutions for an expanding range of use cases. This could reshape deployment economics and data sovereignty strategies.",
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
      id: "d-005",
      title: "Photonic Computing for Transformer Inference",
      description:
        "Two independent research groups published promising results using photonic processors for transformer model inference, achieving 10x energy efficiency improvements. While still at lab stage, this could disrupt the GPU-dominated AI infrastructure market within 3-5 years.",
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
];

const MOCK_SUMMARY = `This week's intelligence scan identified 8 active signals across your monitored domains. Two signals have been elevated to strong signal status: the continued proliferation of autonomous AI agent frameworks and the rapid expansion of EU AI Act compliance tooling.

Key highlights for executive attention:
- AI agent frameworks are reaching production maturity faster than anticipated, with three major enterprise deployments announced this week alone. Your competitor landscape shows 79% activity in this space.
- Regulatory compliance tooling is now a crowded market with 40+ new entrants. Early mover advantage in integrated governance solutions presents a significant opportunity.
- Synthetic data quality improvements are accelerating, with potential to reduce your data acquisition costs by 30-50% within the next two quarters.
- A weak but highly novel signal around photonic computing warrants long-term monitoring, as it could fundamentally alter infrastructure economics.

Recommended actions: Prioritize evaluation of AI agent integration strategies, initiate EU AI Act compliance assessment, and explore synthetic data pilots for non-critical training workloads.`;

const DATE_RANGES = [
  { label: "This Week", days: 7 },
  { label: "Last 2 Weeks", days: 14 },
  { label: "This Month", days: 30 },
  { label: "Last Quarter", days: 90 },
];

export default function DigestPage() {
  const [signals, setSignals] = useState<TenantSignal[]>(MOCK_DIGEST_SIGNALS);
  const [summary, setSummary] = useState(MOCK_SUMMARY);
  const [dateRange, setDateRange] = useState(0);
  const [showDatePicker, setShowDatePicker] = useState(false);

  const range = DATE_RANGES[dateRange];
  const endDate = new Date();
  const startDate = subDays(endDate, range.days);

  useEffect(() => {
    async function fetchDigest() {
      try {
        const data = await getDigest({
          start_date: startDate.toISOString().split("T")[0],
          end_date: endDate.toISOString().split("T")[0],
        });
        if (data && data.signals.length > 0) {
          setSignals(data.signals);
          setSummary(data.summary);
        }
      } catch {
        // Use mock data
      }
    }
    fetchDigest();
  }, [dateRange]);

  const strongCount = signals.filter((s) => s.signal.signal_type === "strong_signal").length;
  const emergingCount = signals.filter((s) => s.signal.signal_type === "emerging_trend").length;
  const weakCount = signals.filter((s) => s.signal.signal_type === "weak_signal").length;
  const avgScore = signals.reduce((sum, s) => sum + s.signal.composite_score, 0) / signals.length;

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Intelligence Digest</h1>
          <p className="text-sm text-slate-500 mt-1">
            {format(startDate, "MMM d")} - {format(endDate, "MMM d, yyyy")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Date range selector */}
          <div className="relative">
            <button
              onClick={() => setShowDatePicker(!showDatePicker)}
              className="btn-secondary"
            >
              <Calendar className="w-4 h-4 mr-2" />
              {range.label}
              <ChevronDown className="w-3 h-3 ml-2" />
            </button>
            {showDatePicker && (
              <div className="absolute right-0 top-full mt-2 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-20 py-1 w-40 animate-fade-in">
                {DATE_RANGES.map((r, idx) => (
                  <button
                    key={r.label}
                    onClick={() => {
                      setDateRange(idx);
                      setShowDatePicker(false);
                    }}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-slate-700 transition-colors ${
                      idx === dateRange ? "text-blue-400" : "text-slate-300"
                    }`}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            className="btn-secondary"
            onClick={() => {
              const text = `Intelligence Digest: ${format(startDate, "MMM d")} - ${format(endDate, "MMM d, yyyy")}\n\n${summary}\n\nSignals:\n${signals.map((s, i) => `${i + 1}. ${s.signal.title} (Score: ${(s.signal.composite_score * 100).toFixed(0)}%)`).join("\n")}`;
              const blob = new Blob([text], { type: "text/plain" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `digest-${format(endDate, "yyyy-MM-dd")}.txt`;
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </button>
          <button
            className="btn-primary"
            onClick={async () => {
              const text = `Intelligence Digest: ${format(startDate, "MMM d")} - ${format(endDate, "MMM d, yyyy")}\n\n${summary}`;
              if (navigator.share) {
                await navigator.share({ title: "Intelligence Digest", text });
              } else {
                await navigator.clipboard.writeText(text);
                alert("Digest copied to clipboard");
              }
            }}
          >
            <Share2 className="w-4 h-4 mr-2" />
            Share
          </button>
        </div>
      </div>

      {/* Stats overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card-compact text-center">
          <div className="flex items-center justify-center gap-2 mb-1">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span className="text-2xl font-bold text-white">{strongCount}</span>
          </div>
          <p className="text-xs text-slate-500">Strong Signals</p>
        </div>
        <div className="card-compact text-center">
          <div className="flex items-center justify-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-blue-400" />
            <span className="text-2xl font-bold text-white">{emergingCount}</span>
          </div>
          <p className="text-xs text-slate-500">Emerging Trends</p>
        </div>
        <div className="card-compact text-center">
          <div className="flex items-center justify-center gap-2 mb-1">
            <Radio className="w-4 h-4 text-amber-400" />
            <span className="text-2xl font-bold text-white">{weakCount}</span>
          </div>
          <p className="text-xs text-slate-500">Weak Signals</p>
        </div>
        <div className="card-compact text-center">
          <div className="mb-1">
            <span className="text-2xl font-bold text-white">{(avgScore * 100).toFixed(0)}%</span>
          </div>
          <p className="text-xs text-slate-500">Avg Composite Score</p>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="card">
        <h2 className="text-sm font-semibold text-slate-200 mb-4 uppercase tracking-wider">
          Executive Summary
        </h2>
        <div className="prose prose-sm prose-invert max-w-none">
          {summary.split("\n\n").map((paragraph, i) => (
            <p key={i} className="text-sm text-slate-300 leading-relaxed mb-4 last:mb-0">
              {paragraph.startsWith("- ") ? (
                <span className="block pl-4 border-l-2 border-blue-500/30 ml-1">
                  {paragraph}
                </span>
              ) : (
                paragraph
              )}
            </p>
          ))}
        </div>
      </div>

      {/* Signal breakdown */}
      <div>
        <h2 className="text-sm font-semibold text-slate-200 mb-4 uppercase tracking-wider">
          Ranked Signal Analysis
        </h2>
        <div className="space-y-4">
          {signals
            .sort((a, b) => b.signal.composite_score - a.signal.composite_score)
            .map((ts, idx) => (
              <div key={ts.signal.id} className="animate-slide-up" style={{ animationDelay: `${idx * 80}ms` }}>
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 mt-2">
                    <span className="text-xs font-bold text-slate-400">#{idx + 1}</span>
                  </div>
                  <div className="flex-1">
                    <SignalCard tenantSignal={ts} onDismiss={() => {}} />
                  </div>
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Footer actions */}
      <div className="card flex items-center justify-between">
        <p className="text-xs text-slate-500">
          Digest generated on {format(new Date(), "MMMM d, yyyy 'at' h:mm a")}
        </p>
        <div className="flex gap-2">
          <button
            className="btn-secondary text-xs"
            onClick={() => {
              const text = `Intelligence Digest: ${format(startDate, "MMM d")} - ${format(endDate, "MMM d, yyyy")}\n\n${summary}\n\nSignals:\n${signals.map((s, i) => `${i + 1}. ${s.signal.title} (Score: ${(s.signal.composite_score * 100).toFixed(0)}%)`).join("\n")}`;
              const blob = new Blob([text], { type: "text/plain" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `digest-${format(endDate, "yyyy-MM-dd")}.txt`;
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            <Download className="w-3 h-3 mr-1" />
            Download PDF
          </button>
          <button
            className="btn-primary text-xs"
            onClick={async () => {
              const text = `Intelligence Digest: ${format(startDate, "MMM d")} - ${format(endDate, "MMM d, yyyy")}\n\n${summary}`;
              if (navigator.share) {
                await navigator.share({ title: "Intelligence Digest", text });
              } else {
                await navigator.clipboard.writeText(text);
                alert("Digest copied to clipboard");
              }
            }}
          >
            <Share2 className="w-3 h-3 mr-1" />
            Share with Team
          </button>
        </div>
      </div>
    </div>
  );
}
