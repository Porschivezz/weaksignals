"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import type { TenantSignal } from "@/lib/types";

interface SignalRadarProps {
  signals: TenantSignal[];
  onSignalClick?: (signal: TenantSignal) => void;
}

const COLORS = [
  "#3b82f6",
  "#f59e0b",
  "#10b981",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#f97316",
  "#14b8a6",
  "#6366f1",
];

export default function SignalRadar({ signals, onSignalClick }: SignalRadarProps) {
  const displaySignals = signals.slice(0, 8);

  const radarData = [
    {
      axis: "Новизна",
      ...Object.fromEntries(
        displaySignals.map((s, i) => [`signal_${i}`, s.signal.novelty_score * 100])
      ),
    },
    {
      axis: "Импульс",
      ...Object.fromEntries(
        displaySignals.map((s, i) => [`signal_${i}`, s.signal.momentum_score * 100])
      ),
    },
    {
      axis: "Релевантность",
      ...Object.fromEntries(
        displaySignals.map((s, i) => [`signal_${i}`, s.relevance_score * 100])
      ),
    },
    {
      axis: "Конкуренция",
      ...Object.fromEntries(
        displaySignals.map((s, i) => [`signal_${i}`, s.competitor_activity * 100])
      ),
    },
    {
      axis: "Возможности",
      ...Object.fromEntries(
        displaySignals.map((s, i) => [`signal_${i}`, s.opportunity_score * 100])
      ),
    },
  ];

  return (
    <div className="w-full h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
          <PolarGrid stroke="#334155" strokeDasharray="3 3" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fill: "#94a3b8", fontSize: 12 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: "#475569", fontSize: 10 }}
            tickCount={5}
          />
          {displaySignals.map((signal, i) => (
            <Radar
              key={signal.signal.id}
              name={signal.signal.title.length > 25 ? signal.signal.title.slice(0, 22) + "..." : signal.signal.title}
              dataKey={`signal_${i}`}
              stroke={COLORS[i % COLORS.length]}
              fill={COLORS[i % COLORS.length]}
              fillOpacity={0.08}
              strokeWidth={1.5}
              onClick={() => onSignalClick?.(signal)}
              style={{ cursor: onSignalClick ? "pointer" : "default" }}
            />
          ))}
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              fontSize: "12px",
              color: "#e2e8f0",
            }}
            formatter={(value: number) => `${value.toFixed(0)}%`}
          />
          <Legend
            wrapperStyle={{ fontSize: "11px", color: "#94a3b8" }}
            onClick={(e) => {
              const idx = displaySignals.findIndex(
                (s) =>
                  (s.signal.title.length > 25
                    ? s.signal.title.slice(0, 22) + "..."
                    : s.signal.title) === e.value
              );
              if (idx >= 0 && onSignalClick) {
                onSignalClick(displaySignals[idx]);
              }
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
