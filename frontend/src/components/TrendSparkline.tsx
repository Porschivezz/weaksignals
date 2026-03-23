"use client";

import {
  AreaChart,
  Area,
  ResponsiveContainer,
} from "recharts";

interface TrendSparklineProps {
  data: { value: number }[];
  width?: number;
  height?: number;
}

export default function TrendSparkline({
  data,
  width = 80,
  height = 30,
}: TrendSparklineProps) {
  if (!data || data.length < 2) return null;

  const firstVal = data[0].value;
  const lastVal = data[data.length - 1].value;
  const trendUp = lastVal >= firstVal;
  const color = trendUp ? "#10b981" : "#ef4444";

  return (
    <div style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <defs>
            <linearGradient id={`sparkGrad-${trendUp}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#sparkGrad-${trendUp})`}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
