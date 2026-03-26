"use client";

import { useState } from "react";
import { Clock, XCircle, ChevronDown, ChevronUp } from "lucide-react";
import type { TenantSignal } from "@/lib/types";
import { CLUSTER_NAMES, SIGNAL_TYPE_LABELS } from "@/lib/types";
import ScoreBar from "./ScoreBar";
import TrendSparkline from "./TrendSparkline";

interface SignalCardProps {
  tenantSignal: TenantSignal;
  compact?: boolean;
  sparklineData?: { value: number }[];
  onDismiss?: (id: string) => void;
  onClick?: () => void;
}

const typeConfig: Record<string, { label: string; className: string; glow: string }> = {
  noise: { label: "Шум", className: "badge bg-slate-700 text-slate-400 border-slate-600", glow: "" },
  weak_signal: { label: "Слабый сигнал", className: "badge-weak", glow: "glow-amber" },
  emerging_trend: { label: "Зарождающийся тренд", className: "badge-emerging", glow: "glow-blue" },
  strong_signal: { label: "Сильный сигнал", className: "badge-strong", glow: "glow-red" },
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
  const config = typeConfig[signal.signal_type] || typeConfig.weak_signal;
  const clusterName = signal.cluster ? CLUSTER_NAMES[signal.cluster] || signal.cluster : null;

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
              {clusterName && (
                <span className="text-[10px] text-slate-500">{clusterName}</span>
              )}
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
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className={`badge ${config.className}`}>{config.label}</span>
            {clusterName && (
              <span className="badge bg-slate-800 text-slate-400 border-slate-700">
                {clusterName}
              </span>
            )}
          </div>
          <h3
            className="text-lg font-semibold text-white mb-1 cursor-pointer hover:text-blue-300 transition-colors"
            onClick={onClick}
          >
            {signal.title}
          </h3>
        </div>
        <div className="text-right shrink-0">
          <div className="text-2xl font-bold text-white tabular-nums">
            {(signal.composite_score * 100).toFixed(0)}
          </div>
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Балл</div>
        </div>
      </div>

      {/* Description */}
      {signal.description && (
        <p className="text-sm text-slate-400 mb-4 leading-relaxed line-clamp-2">
          {signal.description}
        </p>
      )}

      {/* Score bars */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 mb-4">
        <ScoreBar label="Новизна" value={signal.novelty_score} color="cyan" />
        <ScoreBar label="Импульс" value={signal.momentum_score} color="blue" />
        <ScoreBar label="Релевантность" value={tenantSignal.relevance_score} color="amber" />
        <ScoreBar label="Возможность" value={tenantSignal.opportunity_score} color="emerald" />
      </div>

      {/* Expandable detail */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors mb-2"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded ? "Свернуть" : "Подробнее"}
      </button>

      {expanded && (
        <div className="border-t border-slate-800 pt-4 mt-2 space-y-3 animate-fade-in">
          {signal.description && (
            <p className="text-sm text-slate-300 leading-relaxed">{signal.description}</p>
          )}
          <div className="grid grid-cols-2 gap-4 text-xs text-slate-400">
            <div>
              <span className="text-slate-500">Обнаружен:</span>{" "}
              {new Date(signal.first_detected).toLocaleDateString("ru-RU")}
            </div>
            <div>
              <span className="text-slate-500">Обновлен:</span>{" "}
              {new Date(signal.last_updated).toLocaleDateString("ru-RU")}
            </div>
            <div>
              <span className="text-slate-500">Уверенность:</span>{" "}
              {(signal.confidence_level * 100).toFixed(0)}%
            </div>
            <div>
              <span className="text-slate-500">Конкуренты:</span>{" "}
              {(tenantSignal.competitor_activity * 100).toFixed(0)}%
            </div>
          </div>
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
            Скрыть
          </button>
        )}
      </div>
    </div>
  );
}
