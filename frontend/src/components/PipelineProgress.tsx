"use client";

import { X, CheckCircle2, Loader2, Clock, AlertCircle, Database, Brain, Users, ChevronDown, ChevronUp } from "lucide-react";
import { usePipeline } from "@/lib/pipeline-context";
import { useState } from "react";

const SOURCE_NAMES: Record<string, string> = {
  pubmed: "PubMed",
  openalex: "OpenAlex",
  clinicaltrials: "ClinicalTrials.gov",
  arxiv: "arXiv",
  rss: "RSS-ленты",
};

function StageIcon({ status }: { status: string }) {
  if (status === "running") return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
  if (status === "completed") return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
  if (status === "skipped") return <AlertCircle className="w-4 h-4 text-amber-400" />;
  return <Clock className="w-4 h-4 text-slate-600" />;
}

export default function PipelineProgress() {
  const { progress, isRunning, showProgress, setShowProgress } = usePipeline();
  const [expanded, setExpanded] = useState(true);

  if (!showProgress || !progress) return null;

  const isDone = progress.status === "completed" || progress.status === "failed";

  // Calculate overall progress percentage
  let pct = 0;
  if (progress.stage === "ingestion") {
    const fetched = Object.values(progress.ingestion.total_fetched);
    const done = fetched.filter((v) => v > 0).length;
    pct = Math.round((done / 5) * 33);
  } else if (progress.stage === "analysis") {
    const total = progress.analysis.total_docs || 1;
    const analyzed = progress.analysis.analyzed;
    pct = 33 + Math.round((analyzed / total) * 34);
  } else if (progress.stage === "relevance") {
    pct = 80;
  } else if (progress.stage === "done") {
    pct = 100;
  }

  const stageLabel =
    progress.stage === "ingestion" ? "Сбор данных" :
    progress.stage === "analysis" ? "LLM-анализ" :
    progress.stage === "relevance" ? "Оценка релевантности" :
    progress.stage === "done" ? "Завершено" : "...";

  return (
    <div className="fixed bottom-4 right-4 z-50 w-[380px] animate-slide-up">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl shadow-black/40 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            {isRunning ? (
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
            ) : progress.status === "completed" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-400" />
            )}
            <span className="text-sm font-semibold text-white">
              {isRunning ? "Пайплайн работает" : progress.status === "completed" ? "Пайплайн завершён" : "Ошибка"}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
            >
              {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setShowProgress(false)}
              className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
              title="Свернуть (вы получите уведомление по завершении)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {expanded && (
          <div className="px-4 py-3 space-y-3">
            {/* Overall progress bar */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-slate-400">{stageLabel}</span>
                <span className="text-xs font-mono text-slate-500">{pct}%</span>
              </div>
              <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    progress.status === "failed" ? "bg-red-500" :
                    pct === 100 ? "bg-emerald-500" : "bg-blue-500"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>

            {/* Stage 1: Ingestion */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <StageIcon status={progress.ingestion.status} />
                <Database className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-xs font-medium text-slate-300">Сбор данных</span>
                {progress.ingestion.current_source && progress.ingestion.status === "running" && (
                  <span className="text-[10px] text-blue-400 ml-auto">
                    {progress.ingestion.current_source}...
                  </span>
                )}
              </div>
              {(progress.stage === "ingestion" || isDone) && (
                <div className="ml-6 grid grid-cols-2 gap-x-3 gap-y-0.5">
                  {Object.entries(SOURCE_NAMES).map(([key, name]) => {
                    const fetched = progress.ingestion.total_fetched[key] || 0;
                    const newDocs = progress.ingestion.sources[key] || 0;
                    const isActive = progress.ingestion.current_source === name && progress.ingestion.status === "running";
                    return (
                      <div key={key} className="flex items-center gap-1.5">
                        {fetched > 0 ? (
                          <CheckCircle2 className="w-2.5 h-2.5 text-emerald-500" />
                        ) : isActive ? (
                          <Loader2 className="w-2.5 h-2.5 text-blue-400 animate-spin" />
                        ) : (
                          <div className="w-2.5 h-2.5 rounded-full bg-slate-700" />
                        )}
                        <span className={`text-[10px] ${isActive ? "text-blue-300" : "text-slate-500"}`}>
                          {name}
                        </span>
                        {fetched > 0 && (
                          <span className="text-[10px] text-slate-600 ml-auto tabular-nums">
                            {fetched}{newDocs > 0 && <span className="text-emerald-500"> +{newDocs}</span>}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
              {progress.ingestion.status === "completed" && (
                <p className="ml-6 text-[10px] text-slate-500">
                  Итого новых: <span className="text-emerald-400 font-medium">{progress.ingestion.total_new}</span>
                </p>
              )}
            </div>

            {/* Stage 2: Analysis */}
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <StageIcon status={progress.analysis.status} />
                <Brain className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-xs font-medium text-slate-300">LLM-анализ</span>
              </div>
              {(progress.stage === "analysis" || (isDone && progress.analysis.status !== "pending")) && (
                <div className="ml-6 space-y-0.5">
                  {progress.analysis.status === "skipped" ? (
                    <p className="text-[10px] text-amber-400">{progress.analysis.error || "Пропущен"}</p>
                  ) : (
                    <>
                      <p className="text-[10px] text-slate-500">
                        Документов: <span className="text-slate-400">{progress.analysis.analyzed}</span> / {progress.analysis.total_docs}
                      </p>
                      <p className="text-[10px] text-slate-500">
                        Сигналов создано: <span className="text-emerald-400 font-medium">{progress.analysis.signals_created}</span>
                        {progress.analysis.signals_updated > 0 && (
                          <>, обновлено: <span className="text-blue-400 font-medium">{progress.analysis.signals_updated}</span></>
                        )}
                      </p>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Stage 3: Relevance */}
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <StageIcon status={progress.relevance.status} />
                <Users className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-xs font-medium text-slate-300">Оценка релевантности</span>
              </div>
              {(progress.stage === "relevance" || (isDone && progress.relevance.status !== "pending")) && (
                <p className="ml-6 text-[10px] text-slate-500">
                  Оценено пар: <span className="text-slate-400">{progress.relevance.scored}</span>
                </p>
              )}
            </div>

            {/* Error */}
            {progress.error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                <p className="text-xs text-red-400">{progress.error}</p>
              </div>
            )}

            {/* Hint about closing */}
            {isRunning && (
              <p className="text-[10px] text-slate-600 text-center pt-1">
                Можете закрыть это окно — уведомим по завершении
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
