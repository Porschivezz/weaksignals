"use client";

import { createContext, useContext, useState, useCallback, useRef, useEffect } from "react";
import type { PipelineProgress } from "./types";
import { triggerIngestion, getPipelineProgress } from "./api";

interface PipelineContextValue {
  progress: PipelineProgress | null;
  isRunning: boolean;
  showProgress: boolean;
  setShowProgress: (v: boolean) => void;
  toast: ToastData | null;
  dismissToast: () => void;
  startPipeline: () => Promise<void>;
}

interface ToastData {
  type: "success" | "error";
  title: string;
  message: string;
}

const PipelineContext = createContext<PipelineContextValue | null>(null);

export function usePipeline() {
  const ctx = useContext(PipelineContext);
  if (!ctx) throw new Error("usePipeline must be used within PipelineProvider");
  return ctx;
}

export function PipelineProvider({ children }: { children: React.ReactNode }) {
  const [progress, setProgress] = useState<PipelineProgress | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [toast, setToast] = useState<ToastData | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const dismissToast = useCallback(() => setToast(null), []);

  // Auto-dismiss toast after 15 seconds
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 15000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  const startPolling = useCallback((taskId: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const data = await getPipelineProgress(taskId);
        setProgress(data);

        if (data.status === "completed" || data.status === "failed") {
          stopPolling();
          setIsRunning(false);

          if (data.status === "completed") {
            const newDocs = data.ingestion?.total_new ?? 0;
            const created = data.analysis?.signals_created ?? 0;
            const updated = data.analysis?.signals_updated ?? 0;
            setToast({
              type: "success",
              title: "Пайплайн завершён",
              message: `Новых документов: ${newDocs}. Создано сигналов: ${created}, обновлено: ${updated}.`,
            });
          } else {
            setToast({
              type: "error",
              title: "Ошибка пайплайна",
              message: data.error || "Произошла неизвестная ошибка.",
            });
          }
        }
      } catch {
        // Ignore polling errors
      }
    }, 2000);
  }, [stopPolling]);

  const startPipeline = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);
    setShowProgress(true);
    setToast(null);
    try {
      const result = await triggerIngestion();
      const taskId = result.task_id;

      // Set initial progress
      setProgress({
        task_id: taskId,
        status: "running",
        stage: "ingestion",
        started_at: new Date().toISOString(),
        completed_at: null,
        error: null,
        ingestion: {
          status: "running",
          sources: { pubmed: 0, openalex: 0, clinicaltrials: 0, arxiv: 0, rss: 0 },
          total_fetched: { pubmed: 0, openalex: 0, clinicaltrials: 0, arxiv: 0, rss: 0 },
          total_new: 0,
          current_source: "Инициализация...",
        },
        analysis: { status: "pending", total_docs: 0, analyzed: 0, signals_created: 0, signals_updated: 0 },
        relevance: { status: "pending", scored: 0 },
      });

      startPolling(taskId);
    } catch {
      setIsRunning(false);
      setToast({
        type: "error",
        title: "Не удалось запустить",
        message: "Ошибка при запуске пайплайна. Проверьте соединение.",
      });
    }
  }, [isRunning, startPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  return (
    <PipelineContext.Provider
      value={{ progress, isRunning, showProgress, setShowProgress, toast, dismissToast, startPipeline }}
    >
      {children}
    </PipelineContext.Provider>
  );
}
