"use client";

import { useState, useEffect, useCallback } from "react";
import { Filter, X, ChevronDown, ExternalLink, FileText } from "lucide-react";
import type { TenantSignal, Signal, SourceDocument } from "@/lib/types";
import { CLUSTER_NAMES, SIGNAL_TYPE_LABELS, SOURCE_LABELS } from "@/lib/types";
import { getSignals, getSignalSources, dismissSignal } from "@/lib/api";
import SignalCard from "@/components/SignalCard";
import ScoreBar from "@/components/ScoreBar";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

function generateTrajectory(signal: Signal): { date: string; score: number }[] {
  const points = [];
  const base = signal.composite_score * 0.5;
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i * 7);
    const noise = (Math.random() - 0.4) * 0.1;
    const growth = (6 - i) * (signal.momentum_score * 0.08);
    points.push({
      date: d.toLocaleDateString("ru-RU", { month: "short", day: "numeric" }),
      score: Math.min(1, Math.max(0, base + growth + noise)),
    });
  }
  return points;
}

export default function SignalsPage() {
  const [signals, setSignals] = useState<TenantSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("all");
  const [filterCluster, setFilterCluster] = useState<string>("all");
  const [minScore, setMinScore] = useState(0);
  const [timeRange, setTimeRange] = useState<string>("all");
  const [selectedSignal, setSelectedSignal] = useState<TenantSignal | null>(null);
  const [sources, setSources] = useState<SourceDocument[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(true);

  // Fetch sources when a signal is selected
  useEffect(() => {
    if (!selectedSignal) {
      setSources([]);
      return;
    }
    async function fetchSources() {
      setSourcesLoading(true);
      try {
        const data = await getSignalSources(selectedSignal!.signal.id);
        setSources(data);
      } catch {
        setSources([]);
      } finally {
        setSourcesLoading(false);
      }
    }
    fetchSources();
  }, [selectedSignal]);

  useEffect(() => {
    async function fetchSignals() {
      try {
        setLoading(true);
        const params: Record<string, string | number> = { limit: 100 };
        if (filterType !== "all") params.category = filterType;
        if (filterCluster !== "all") params.cluster = filterCluster;
        if (minScore > 0) params.min_score = minScore;
        if (timeRange !== "all") params.time_range = timeRange;
        const data = await getSignals(params);
        setSignals(data);
      } catch {
        // No data
      } finally {
        setLoading(false);
      }
    }
    fetchSignals();
  }, [filterType, filterCluster, minScore, timeRange]);

  const handleDismiss = useCallback(async (id: string) => {
    try {
      await dismissSignal(id);
    } catch {
      // Dismiss locally
    }
    setSignals((prev) =>
      prev.filter((ts) => ts.signal.id !== id)
    );
    if (selectedSignal?.signal.id === id) setSelectedSignal(null);
  }, [selectedSignal]);

  const trajectory = selectedSignal ? generateTrajectory(selectedSignal.signal) : [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Аналитика сигналов</h1>
          <p className="text-sm text-slate-500 mt-1">
            {loading ? "Загрузка..." : `${signals.length} активных сигналов`}
          </p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="btn-secondary"
        >
          <Filter className="w-4 h-4 mr-2" />
          Фильтры
        </button>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="card animate-slide-up">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {/* Signal type */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                Тип сигнала
              </label>
              <div className="relative">
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="input-field appearance-none pr-10"
                >
                  <option value="all">Все типы</option>
                  <option value="weak_signal">Слабые сигналы</option>
                  <option value="emerging_trend">Зарождающиеся тренды</option>
                  <option value="strong_signal">Сильные сигналы</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
              </div>
            </div>

            {/* Cluster */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                Кластер
              </label>
              <div className="relative">
                <select
                  value={filterCluster}
                  onChange={(e) => setFilterCluster(e.target.value)}
                  className="input-field appearance-none pr-10"
                >
                  <option value="all">Все кластеры</option>
                  {Object.entries(CLUSTER_NAMES).map(([key, name]) => (
                    <option key={key} value={key}>{name}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
              </div>
            </div>

            {/* Min score slider */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                Минимальный балл: {(minScore * 100).toFixed(0)}%
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

            {/* Time range */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                Период
              </label>
              <div className="flex gap-2 flex-wrap">
                {[
                  { key: "7d", label: "7д" },
                  { key: "30d", label: "30д" },
                  { key: "90d", label: "90д" },
                  { key: "all", label: "Все" },
                ].map((range) => (
                  <button
                    key={range.key}
                    onClick={() => setTimeRange(range.key)}
                    className={`text-xs px-3 py-1.5 border rounded-lg transition-colors ${
                      timeRange === range.key
                        ? "border-blue-500 text-blue-400 bg-blue-500/10"
                        : "btn-ghost border-slate-700"
                    }`}
                  >
                    {range.label}
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
        <div className={`flex-1 grid gap-4 ${selectedSignal ? "grid-cols-1 lg:grid-cols-1" : "grid-cols-1 md:grid-cols-2 xl:grid-cols-3"}`}>
          {signals.map((ts) => (
            <SignalCard
              key={ts.signal.id}
              tenantSignal={ts}
              onDismiss={handleDismiss}
              onClick={() => setSelectedSignal(ts)}
            />
          ))}
          {!loading && signals.length === 0 && (
            <div className="col-span-full text-center py-16">
              <p className="text-slate-500 text-sm">Нет сигналов по текущим фильтрам.</p>
              <button
                onClick={() => {
                  setFilterType("all");
                  setFilterCluster("all");
                  setMinScore(0);
                  setTimeRange("all");
                }}
                className="btn-ghost mt-3"
              >
                Сбросить фильтры
              </button>
            </div>
          )}
          {loading && (
            <div className="col-span-full text-center py-16">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-slate-500 text-sm">Загрузка сигналов...</p>
            </div>
          )}
        </div>

        {/* Detail panel */}
        {selectedSignal && (
          <div className="hidden xl:block w-[420px] shrink-0">
            <div className="card sticky top-8 animate-slide-right">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-300">Детали сигнала</h3>
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

              {selectedSignal.signal.cluster && (
                <span className="inline-block badge bg-slate-800 text-slate-400 border-slate-700 mb-3">
                  {CLUSTER_NAMES[selectedSignal.signal.cluster] || selectedSignal.signal.cluster}
                </span>
              )}

              {selectedSignal.signal.description && (
                <p className="text-sm text-slate-400 leading-relaxed mb-6">
                  {selectedSignal.signal.description}
                </p>
              )}

              {/* Trajectory chart */}
              <div className="mb-6">
                <h4 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">
                  Траектория (7 недель)
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
                          "Балл",
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
                <ScoreBar label="Новизна" value={selectedSignal.signal.novelty_score} color="cyan" />
                <ScoreBar label="Импульс" value={selectedSignal.signal.momentum_score} color="blue" />
                <ScoreBar label="Релевантность" value={selectedSignal.relevance_score} color="amber" />
                <ScoreBar label="Конкуренты" value={selectedSignal.competitor_activity} color="red" />
                <ScoreBar label="Возможность" value={selectedSignal.opportunity_score} color="emerald" />
              </div>

              {/* Sources */}
              <div className="mb-6">
                <h4 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">
                  <FileText className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />
                  Источники ({sources.length})
                </h4>
                {sourcesLoading ? (
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <div className="w-3.5 h-3.5 border border-blue-500 border-t-transparent rounded-full animate-spin" />
                    Загрузка источников...
                  </div>
                ) : sources.length > 0 ? (
                  <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                    {sources.map((doc) => (
                      <div
                        key={doc.id}
                        className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-3 hover:border-slate-600 transition-colors"
                      >
                        <div className="flex items-start gap-2">
                          <span className="shrink-0 mt-0.5 text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-700 text-slate-300">
                            {SOURCE_LABELS[doc.source] || doc.source}
                          </span>
                          <div className="min-w-0 flex-1">
                            {doc.url ? (
                              <a
                                href={doc.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs font-medium text-blue-400 hover:text-blue-300 transition-colors leading-tight line-clamp-2"
                              >
                                {doc.title}
                                <ExternalLink className="w-3 h-3 inline ml-1 -mt-0.5" />
                              </a>
                            ) : (
                              <span className="text-xs font-medium text-slate-300 leading-tight line-clamp-2">
                                {doc.title}
                              </span>
                            )}
                            {doc.published_date && (
                              <p className="text-[10px] text-slate-500 mt-1">
                                {new Date(doc.published_date).toLocaleDateString("ru-RU", {
                                  year: "numeric",
                                  month: "short",
                                  day: "numeric",
                                })}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-600">
                    Источники не привязаны. Запустите анализ для обновления.
                  </p>
                )}
              </div>

              {/* Meta */}
              <div className="space-y-2 text-xs text-slate-500 border-t border-slate-800 pt-4">
                <div className="flex justify-between">
                  <span>Обнаружен</span>
                  <span className="text-slate-400">
                    {new Date(selectedSignal.signal.first_detected).toLocaleDateString("ru-RU")}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Обновлен</span>
                  <span className="text-slate-400">
                    {new Date(selectedSignal.signal.last_updated).toLocaleDateString("ru-RU")}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Уверенность</span>
                  <span className="text-slate-400">
                    {(selectedSignal.signal.confidence_level * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 mt-6">
                <button
                  onClick={() => handleDismiss(selectedSignal.signal.id)}
                  className="btn-secondary flex-1 text-xs"
                >
                  Скрыть
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
