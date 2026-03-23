"use client";

import { useState } from "react";
import { Clock, ExternalLink, XCircle, ChevronDown, ChevronUp } from "lucide-react";
import type { TenantSignal } from "@/lib/types";
import ScoreBar from "./ScoreBar";
import TrendSparkline from "./TrendSparkline";

interface SignalCardProps {
  tenantSignal: TenantSignal;
  compact?: boolean;
  sparklineData?: { value: number }[];
  onDismiss?: (id: string) => void;
  onClick?: () => void;
}

const typeConfig = {
  weak_signal: { label: "Weak Signal", className: "badge-weak", glow: "glow-amber" },
  emerging_trend: { label: "Emerging Trend", className: "badge-emerging", glow: "glow-blue" },
  strong_signal: { label: "Strong Signal", className: "badge-strong", glow: "glow-red" },
};

const horizonLabels: Record<string, string> = {
  immediate: "Immediate",
  short_term: "Short Term",
  medium_term: "Medium Term",
  long_term: "Long Term",
};

export default function SignalCard({
  tenantSignal,
  compact = false,
  sparklineData,
  onDismiss,
  onClick,
}: SignalCardProps) {
  const [expanded, setExpanded] = useState(false);
  const { signal } = tenantSignal;
  const config = typeConfig[signal.signal_type];

  if (compact) {
    return (
      <div
        className="card-compact cursor-pointer group animate-fade-in"
        onClick={onClick}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5">
              <span className={`badge ${config.className}`}>{config.label}</span>
              <span className="text-[10px] text-slate-500">
                {horizonLabels[signal.time_horizon]}
              </span>
            </div>
            <h3 className="text-sm font-medium text-slate-200 truncate group-hover:text-white transition-colors">
              {signal.title}
            </h3>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {sparklineData && <TrendSparkline data={sparklineData} width={64} height={24} />}
            <span className="text-lg font-bold text-slate-300 tabular-nums">
              {(signal.composite_score * 100).toFixed(0)}
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`card animate-slide-up ${config.glow}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className={`badge ${config.className}`}>{config.label}</span>
            <span className="badge bg-slate-800 text-slate-400 border-slate-700">
              <Clock className="w-3 h-3 mr-1" />
              {horizonLabels[signal.time_horizon]}
            </span>
          </div>
          <h3 className="text-lg font-semibold text-white mb-1">{signal.title}</h3>
        </div>
        <div className="text-right shrink-0">
          <div className="text-2xl font-bold text-white tabular-nums">
            {(signal.composite_score * 100).toFixed(0)}
          </div>
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Score</div>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-slate-400 mb-4 leading-relaxed line-clamp-2">
        {signal.description}
      </p>

      {/* Score bars */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 mb-4">
        <ScoreBar label="Novelty" value={signal.novelty_score} color="cyan" />
        <ScoreBar label="Momentum" value={signal.momentum_score} color="blue" />
        <ScoreBar label="Relevance" value={tenantSignal.relevance_score} color="amber" />
        <ScoreBar label="Opportunity" value={tenantSignal.opportunity_score} color="emerald" />
      </div>

      {/* Impact domains */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {signal.impact_domains.map((domain) => (
          <span
            key={domain}
            className="px-2 py-0.5 rounded-md bg-slate-800/80 text-[11px] text-slate-400 border border-slate-700/50"
          >
            {domain}
          </span>
        ))}
      </div>

      {/* Expandable detail */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors mb-2"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded ? "Show less" : "Show details"}
      </button>

      {expanded && (
        <div className="border-t border-slate-800 pt-4 mt-2 space-y-3 animate-fade-in">
          <p className="text-sm text-slate-300 leading-relaxed">{signal.description}</p>
          <div className="grid grid-cols-2 gap-4 text-xs text-slate-400">
            <div>
              <span className="text-slate-500">First detected:</span>{" "}
              {new Date(signal.first_detected).toLocaleDateString()}
            </div>
            <div>
              <span className="text-slate-500">Last updated:</span>{" "}
              {new Date(signal.last_updated).toLocaleDateString()}
            </div>
            <div>
              <span className="text-slate-500">Confidence:</span>{" "}
              {(signal.confidence_level * 100).toFixed(0)}%
            </div>
            <div>
              <span className="text-slate-500">Competitor activity:</span>{" "}
              {(tenantSignal.competitor_activity * 100).toFixed(0)}%
            </div>
          </div>
          {signal.evidence_ids.length > 0 && (
            <div className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 cursor-pointer">
              <ExternalLink className="w-3 h-3" />
              {signal.evidence_ids.length} evidence source{signal.evidence_ids.length > 1 ? "s" : ""}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 mt-3 pt-3 border-t border-slate-800/50">
        {onDismiss && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDismiss(signal.id);
            }}
            className="btn-ghost text-xs text-slate-500 hover:text-red-400"
          >
            <XCircle className="w-3.5 h-3.5 mr-1" />
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
}
