"use client";

import { useEffect, useState } from "react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import { Activity, AlertTriangle, TrendingUp, Beaker, Pill, Shield, Globe, Brain, Users } from "lucide-react";
import type { TenantSignal } from "@/lib/types";
import { CLUSTER_NAMES } from "@/lib/types";
import { getSignals } from "@/lib/api";
import SignalCard from "@/components/SignalCard";
import SignalRadar from "@/components/SignalRadar";
import AlertFeed from "@/components/AlertFeed";

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

const CLUSTER_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  ai_drug_discovery: Brain,
  oncology: Beaker,
  biosimilars: Pill,
  regulatory: Shield,
  competitors_ru: Users,
  export_markets: Globe,
};

const CLUSTER_COLORS: Record<string, string> = {
  ai_drug_discovery: "from-purple-500 to-blue-500",
  oncology: "from-red-500 to-pink-500",
  biosimilars: "from-emerald-500 to-teal-500",
  regulatory: "from-amber-500 to-orange-500",
  competitors_ru: "from-cyan-500 to-blue-500",
  export_markets: "from-indigo-500 to-violet-500",
};

export default function DashboardOverview() {
  const [signals, setSignals] = useState<TenantSignal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSignals() {
      try {
        const data = await getSignals({ limit: 20 });
        setSignals(data);
      } catch {
        // No data
      } finally {
        setLoading(false);
      }
    }
    fetchSignals();
  }, []);

  const strongCount = signals.filter((s) => s.signal.signal_type === "strong_signal").length;
  const emergingCount = signals.filter((s) => s.signal.signal_type === "emerging_trend").length;
  const weakCount = signals.filter((s) => s.signal.signal_type === "weak_signal").length;
  const newThisWeek = signals.filter((s) => {
    const detected = new Date(s.signal.first_detected);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return detected >= weekAgo;
  }).length;

  // Cluster breakdown
  const clusterCounts: Record<string, number> = {};
  signals.forEach((s) => {
    const cluster = s.signal.cluster || "other";
    clusterCounts[cluster] = (clusterCounts[cluster] || 0) + 1;
  });

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Мониторинг слабых сигналов</h1>
          <p className="text-sm text-slate-500 mt-1">
            ГК Фармасинтез &mdash; {format(new Date(), "d MMMM yyyy", { locale: ru })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-slate-500">Мониторинг активен</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Всего сигналов"
          value={signals.length}
          icon={Activity}
          color="bg-blue-500/10 text-blue-400"
        />
        <StatCard
          label="Новых за неделю"
          value={newThisWeek}
          icon={TrendingUp}
          color="bg-emerald-500/10 text-emerald-400"
        />
        <StatCard
          label="Сильных сигналов"
          value={strongCount}
          change={strongCount > 0 ? "Требуют внимания" : undefined}
          changePositive={false}
          icon={AlertTriangle}
          color="bg-red-500/10 text-red-400"
        />
        <StatCard
          label="Зарождающихся трендов"
          value={emergingCount}
          icon={TrendingUp}
          color="bg-amber-500/10 text-amber-400"
        />
      </div>

      {/* Cluster breakdown */}
      {Object.keys(clusterCounts).length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-200 mb-4">Кластеры мониторинга</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {Object.entries(CLUSTER_NAMES).map(([key, name]) => {
              const count = clusterCounts[key] || 0;
              const ClusterIcon = CLUSTER_ICONS[key] || Activity;
              const gradient = CLUSTER_COLORS[key] || "from-slate-500 to-slate-600";
              return (
                <div key={key} className="card-compact group hover:border-slate-600 transition-all cursor-default">
                  <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center mb-2 opacity-80`}>
                    <ClusterIcon className="w-4 h-4 text-white" />
                  </div>
                  <p className="text-xs font-medium text-slate-300 mb-0.5 line-clamp-1">{name}</p>
                  <p className="text-lg font-bold text-white tabular-nums">{count}</p>
                  <p className="text-[10px] text-slate-500">
                    {count === 1 ? "сигнал" : count >= 2 && count <= 4 ? "сигнала" : "сигналов"}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Main content grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Signal Radar - takes 2 cols */}
        <div className="xl:col-span-2 card">
          <h2 className="text-sm font-semibold text-slate-200 mb-4">Радар сигналов</h2>
          <p className="text-xs text-slate-500 mb-2">
            Многомерный анализ: новизна, импульс, релевантность, конкуренция, возможности
          </p>
          {signals.length > 0 ? (
            <SignalRadar signals={signals.slice(0, 8)} />
          ) : (
            <div className="h-[400px] flex items-center justify-center text-slate-500 text-sm">
              {loading ? "Загрузка данных..." : "Нет данных для отображения. Запустите сбор данных."}
            </div>
          )}
        </div>

        {/* Alert Feed */}
        <div className="card h-[500px]">
          <AlertFeed />
        </div>
      </div>

      {/* Recent signals */}
      <div>
        <h2 className="text-sm font-semibold text-slate-200 mb-3">Топ сигналы по релевантности</h2>
        {signals.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {signals.slice(0, 6).map((ts) => (
              <SignalCard key={ts.signal.id} tenantSignal={ts} />
            ))}
          </div>
        ) : (
          <div className="card text-center py-12">
            <p className="text-slate-500 text-sm">
              {loading ? "Загрузка сигналов..." : "Сигналы еще не обнаружены. Нажмите \"Запустить сбор\" в меню слева."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
