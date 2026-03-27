"use client";

import { CheckCircle2, AlertCircle, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { usePipeline } from "@/lib/pipeline-context";

export default function Toast() {
  const { toast, dismissToast } = usePipeline();
  const router = useRouter();

  if (!toast) return null;

  const isSuccess = toast.type === "success";

  return (
    <div
      className="fixed top-4 right-4 z-[60] w-[360px] animate-slide-down cursor-pointer"
      onClick={() => {
        if (isSuccess) {
          router.push("/dashboard/signals");
        }
        dismissToast();
      }}
    >
      <div
        className={`bg-slate-900 border rounded-xl shadow-2xl shadow-black/40 px-4 py-3 flex items-start gap-3 ${
          isSuccess ? "border-emerald-500/30" : "border-red-500/30"
        }`}
      >
        {isSuccess ? (
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        ) : (
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
        )}
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-semibold ${isSuccess ? "text-emerald-300" : "text-red-300"}`}>
            {toast.title}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">{toast.message}</p>
          {isSuccess && (
            <p className="text-[10px] text-slate-600 mt-1">Нажмите, чтобы перейти к сигналам</p>
          )}
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            dismissToast();
          }}
          className="p-1 text-slate-500 hover:text-slate-300 transition-colors shrink-0"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
