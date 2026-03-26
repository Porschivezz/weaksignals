"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, TrendingUp, Radio, Bell, RefreshCw } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ru } from "date-fns/locale";
import type { TenantSignal } from "@/lib/types";
import { getSignals } from "@/lib/api";
import { CLUSTER_NAMES, SIGNAL_TYPE_LABELS } from "@/lib/types";

interface AlertFeedProps {
  maxItems?: number;
}

const typeConfig: Record<string, { icon: typeof Radio; color: string; bg: string; border: string }> = {
  weak_signal: {
    icon: Radio,
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
  },
  emerging_trend: {
    icon: TrendingUp,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/20",
  },
  strong_signal: {
    icon: AlertTriangle,
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/20",
  },
  noise: {
    icon: Radio,
    color: "text-slate-400",
    bg: "bg-slate-500/10",
    border: "border-slate-500/20",
  },
};

export default function AlertFeed({ maxItems = 10 }: AlertFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [signals, setSignals] = useState<TenantSignal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetch() {
      try {
        const data = await getSignals({ limit: maxItems });
        setSignals(data);
      } catch {
        // No data available
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, [maxItems]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">Последние сигналы</h3>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/15 text-blue-400 border border-blue-500/25">
          {signals.length} активных
        </span>
      </div>

      {/* Feed */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 pr-1">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-5 h-5 text-slate-500 animate-spin" />
          </div>
        ) : signals.length === 0 ? (
          <p className="text-xs text-slate-500 text-center py-8">Нет активных сигналов</p>
        ) : (
          signals.map((ts) => {
            const config = typeConfig[ts.signal.signal_type] || typeConfig.noise;
            const Icon = config.icon;
            const clusterName = ts.signal.cluster
              ? CLUSTER_NAMES[ts.signal.cluster] || ts.signal.cluster
              : null;
            return (
              <div
                key={ts.signal.id}
                className={`flex gap-3 p-3 rounded-lg border transition-all duration-200 cursor-pointer hover:bg-slate-800/40 ${config.border} ${config.bg}`}
              >
                <div className={`shrink-0 mt-0.5 ${config.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-xs font-medium leading-tight text-slate-200">
                      {ts.signal.title}
                    </h4>
                    <span className="text-xs font-bold text-slate-400 tabular-nums shrink-0">
                      {(ts.signal.composite_score * 100).toFixed(0)}
                    </span>
                  </div>
                  {clusterName && (
                    <p className="text-[10px] text-slate-500 mt-0.5">{clusterName}</p>
                  )}
                  <p className="text-[10px] text-slate-600 mt-1">
                    {formatDistanceToNow(new Date(ts.signal.first_detected), {
                      addSuffix: true,
                      locale: ru,
                    })}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
