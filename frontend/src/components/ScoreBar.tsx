"use client";

import { useEffect, useState } from "react";

interface ScoreBarProps {
  label: string;
  value: number;
  color?: "amber" | "blue" | "red" | "cyan" | "emerald";
  showValue?: boolean;
}

const colorMap = {
  amber: "bg-amber-500",
  blue: "bg-blue-500",
  red: "bg-red-500",
  cyan: "bg-cyan-500",
  emerald: "bg-emerald-500",
};

const bgMap = {
  amber: "bg-amber-500/10",
  blue: "bg-blue-500/10",
  red: "bg-red-500/10",
  cyan: "bg-cyan-500/10",
  emerald: "bg-emerald-500/10",
};

export default function ScoreBar({
  label,
  value,
  color = "blue",
  showValue = true,
}: ScoreBarProps) {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setWidth(Math.min(Math.max(value, 0), 1) * 100);
    }, 100);
    return () => clearTimeout(timer);
  }, [value]);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        {showValue && (
          <span className="text-slate-300 font-medium tabular-nums">
            {(value * 100).toFixed(0)}%
          </span>
        )}
      </div>
      <div className={`h-1.5 rounded-full ${bgMap[color]} overflow-hidden`}>
        <div
          className={`h-full rounded-full ${colorMap[color]} transition-all duration-1000 ease-out`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}
