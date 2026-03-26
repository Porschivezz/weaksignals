"use client";

import { useState, useEffect } from "react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import { Download, Share2, TrendingUp, AlertTriangle, Radio, RefreshCw, Lightbulb, ShieldAlert, Target } from "lucide-react";
import type { WeeklyDigest, DigestSignalBrief } from "@/lib/types";
import { CLUSTER_NAMES } from "@/lib/types";
import { getWeeklyDigest } from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";

export default function DigestPage() {
  const [digest, setDigest] = useState<WeeklyDigest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDigest() {
      try {
        setLoading(true);
        const data = await getWeeklyDigest(15);
        setDigest(data);
      } catch (err) {
        setError("Не удалось загрузить дайджест");
      } finally {
        setLoading(false);
      }
    }
    fetchDigest();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
          <p className="text-slate-400 text-sm">Формирование дайджеста...</p>
        </div>
      </div>
    );
  }

  if (error || !digest) {
    return (
      <div className="text-center py-24">
        <p className="text-slate-500 text-sm">{error || "Нет данных для дайджеста"}</p>
      </div>
    );
  }

  const { summary, top_signals, new_signals, trending_signals, cluster_breakdown, ai_summary } = digest;

  const exportText = () => {
    const lines = [
      `Дайджест: ${digest.tenant_name}`,
      `Период: ${format(new Date(digest.period.start), "d MMM", { locale: ru })} - ${format(new Date(digest.period.end), "d MMM yyyy", { locale: ru })}`,
      "",
      `Всего активных сигналов: ${summary.total_active_signals}`,
      `Новых за неделю: ${summary.new_this_week}`,
      `В тренде: ${summary.trending}`,
      "",
    ];

    if (ai_summary) {
      lines.push("=== AI АНАЛИЗ ===", "");
      if (ai_summary.key_insights?.length) {
        lines.push("Ключевые инсайты:");
        ai_summary.key_insights.forEach((i) => lines.push(`  - ${i}`));
        lines.push("");
      }
      if (ai_summary.recommendations?.length) {
        lines.push("Рекомендации:");
        ai_summary.recommendations.forEach((r) => lines.push(`  - ${r}`));
        lines.push("");
      }
      if (ai_summary.risk_alerts?.length) {
        lines.push("Риски:");
        ai_summary.risk_alerts.forEach((r) => lines.push(`  - ${r}`));
        lines.push("");
      }
      if (ai_summary.opportunities?.length) {
        lines.push("Возможности:");
        ai_summary.opportunities.forEach((o) => lines.push(`  - ${o}`));
        lines.push("");
      }
    }

    lines.push("=== ТОП СИГНАЛЫ ===", "");
    top_signals.forEach((s, i) => {
      lines.push(`${i + 1}. ${s.title} (${(s.composite_score * 100).toFixed(0)}%) — ${s.cluster_name}`);
    });

    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `digest-${format(new Date(), "yyyy-MM-dd")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Еженедельный дайджест</h1>
          <p className="text-sm text-slate-500 mt-1">
            {digest.tenant_name} &mdash;{" "}
            {format(new Date(digest.period.start), "d MMM", { locale: ru })} &ndash;{" "}
            {format(new Date(digest.period.end), "d MMM yyyy", { locale: ru })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-secondary" onClick={exportText}>
            <Download className="w-4 h-4 mr-2" />
            Экспорт
          </button>
          <button
            className="btn-primary"
            onClick={async () => {
              const text = `Дайджест ${digest.tenant_name}: ${summary.total_active_signals} сигналов, ${summary.new_this_week} новых`;
              if (navigator.share) {
                await navigator.share({ title: "Дайджест", text });
              } else {
                await navigator.clipboard.writeText(text);
              }
            }}
          >
            <Share2 className="w-4 h-4 mr-2" />
            Поделиться
          </button>
        </div>
      </div>

      {/* Stats overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card-compact text-center">
          <span className="text-2xl font-bold text-white">{summary.total_active_signals}</span>
          <p className="text-xs text-slate-500 mt-1">Активных сигналов</p>
        </div>
        <div className="card-compact text-center">
          <span className="text-2xl font-bold text-emerald-400">{summary.new_this_week}</span>
          <p className="text-xs text-slate-500 mt-1">Новых за неделю</p>
        </div>
        <div className="card-compact text-center">
          <span className="text-2xl font-bold text-amber-400">{summary.trending}</span>
          <p className="text-xs text-slate-500 mt-1">В тренде</p>
        </div>
        <div className="card-compact text-center">
          <span className="text-2xl font-bold text-blue-400">
            {Object.keys(cluster_breakdown).length}
          </span>
          <p className="text-xs text-slate-500 mt-1">Кластеров</p>
        </div>
      </div>

      {/* Cluster breakdown */}
      {Object.keys(cluster_breakdown).length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-200 mb-4 uppercase tracking-wider">
            Распределение по кластерам
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(cluster_breakdown).map(([name, count]) => (
              <div key={name} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
                <span className="text-sm text-slate-300">{name}</span>
                <span className="text-lg font-bold text-white tabular-nums">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI Summary */}
      {ai_summary && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
            AI-анализ (Gemini)
          </h2>

          {ai_summary.key_insights && ai_summary.key_insights.length > 0 && (
            <div className="card border-l-4 border-l-blue-500">
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb className="w-4 h-4 text-blue-400" />
                <h3 className="text-sm font-semibold text-blue-400">Ключевые инсайты</h3>
              </div>
              <ul className="space-y-2">
                {ai_summary.key_insights.map((insight, i) => (
                  <li key={i} className="text-sm text-slate-300 leading-relaxed pl-4 border-l-2 border-slate-700">
                    {insight}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {ai_summary.risk_alerts && ai_summary.risk_alerts.length > 0 && (
            <div className="card border-l-4 border-l-red-500">
              <div className="flex items-center gap-2 mb-3">
                <ShieldAlert className="w-4 h-4 text-red-400" />
                <h3 className="text-sm font-semibold text-red-400">Риски и угрозы</h3>
              </div>
              <ul className="space-y-2">
                {ai_summary.risk_alerts.map((risk, i) => (
                  <li key={i} className="text-sm text-slate-300 leading-relaxed pl-4 border-l-2 border-red-900">
                    {risk}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {ai_summary.opportunities && ai_summary.opportunities.length > 0 && (
            <div className="card border-l-4 border-l-emerald-500">
              <div className="flex items-center gap-2 mb-3">
                <Target className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-emerald-400">Возможности</h3>
              </div>
              <ul className="space-y-2">
                {ai_summary.opportunities.map((opp, i) => (
                  <li key={i} className="text-sm text-slate-300 leading-relaxed pl-4 border-l-2 border-emerald-900">
                    {opp}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {ai_summary.recommendations && ai_summary.recommendations.length > 0 && (
            <div className="card border-l-4 border-l-amber-500">
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-amber-400">Рекомендации</h3>
              </div>
              <ul className="space-y-2">
                {ai_summary.recommendations.map((rec, i) => (
                  <li key={i} className="text-sm text-slate-300 leading-relaxed pl-4 border-l-2 border-amber-900">
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Top Signals */}
      <div>
        <h2 className="text-sm font-semibold text-slate-200 mb-4 uppercase tracking-wider">
          Топ сигналы
        </h2>
        <div className="space-y-4">
          {top_signals
            .sort((a, b) => b.composite_score - a.composite_score)
            .map((s, idx) => (
              <div key={s.id} className="animate-slide-up" style={{ animationDelay: `${idx * 60}ms` }}>
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 mt-2">
                    <span className="text-xs font-bold text-slate-400">#{idx + 1}</span>
                  </div>
                  <div className="flex-1 card">
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div>
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className={`badge ${
                            s.signal_type === "strong_signal" ? "badge-strong" :
                            s.signal_type === "emerging_trend" ? "badge-emerging" : "badge-weak"
                          }`}>
                            {s.signal_type === "strong_signal" ? "Сильный" :
                             s.signal_type === "emerging_trend" ? "Тренд" : "Слабый"}
                          </span>
                          <span className="text-[10px] text-slate-500">{s.cluster_name}</span>
                        </div>
                        <h3 className="text-base font-semibold text-white">{s.title}</h3>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-xl font-bold text-white tabular-nums">
                          {(s.composite_score * 100).toFixed(0)}
                        </div>
                        <div className="text-[10px] text-slate-500">Балл</div>
                      </div>
                    </div>
                    {s.description && (
                      <p className="text-sm text-slate-400 leading-relaxed mb-3 line-clamp-2">
                        {s.description}
                      </p>
                    )}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <ScoreBar label="Новизна" value={s.novelty_score} color="cyan" />
                      <ScoreBar label="Импульс" value={s.momentum_score} color="blue" />
                      <ScoreBar label="Релевантность" value={s.relevance_score} color="amber" />
                      <ScoreBar label="Конкуренты" value={s.competitor_activity} color="red" />
                    </div>
                  </div>
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* New signals this week */}
      {new_signals.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-emerald-400 mb-4 uppercase tracking-wider">
            Новые сигналы за неделю ({new_signals.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {new_signals.map((s) => (
              <div key={s.id} className="card-compact">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] text-slate-500">{s.cluster_name}</span>
                </div>
                <h3 className="text-sm font-medium text-white mb-1">{s.title}</h3>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  <span>Балл: {(s.composite_score * 100).toFixed(0)}%</span>
                  <span>Релевантность: {(s.relevance_score * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trending */}
      {trending_signals.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-amber-400 mb-4 uppercase tracking-wider">
            В тренде ({trending_signals.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {trending_signals.map((s) => (
              <div key={s.id} className="card-compact">
                <div className="flex items-center gap-2 mb-1">
                  <TrendingUp className="w-3 h-3 text-amber-400" />
                  <span className="text-[10px] text-slate-500">{s.cluster_name}</span>
                </div>
                <h3 className="text-sm font-medium text-white mb-1">{s.title}</h3>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  <span>Импульс: {(s.momentum_score * 100).toFixed(0)}%</span>
                  <span>Балл: {(s.composite_score * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="card flex items-center justify-between">
        <p className="text-xs text-slate-500">
          Дайджест сформирован {format(new Date(), "d MMMM yyyy, HH:mm", { locale: ru })}
        </p>
        <button className="btn-secondary text-xs" onClick={exportText}>
          <Download className="w-3 h-3 mr-1" />
          Скачать
        </button>
      </div>
    </div>
  );
}
