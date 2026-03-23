"use client";

import { useEffect, useRef } from "react";
import { AlertTriangle, TrendingUp, Radio, Zap, Bell } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface AlertItem {
  id: string;
  timestamp: string;
  type: "weak_signal" | "emerging_trend" | "strong_signal" | "system";
  title: string;
  description: string;
  read?: boolean;
}

interface AlertFeedProps {
  alerts?: AlertItem[];
  maxItems?: number;
}

const MOCK_ALERTS: AlertItem[] = [
  {
    id: "a1",
    timestamp: new Date(Date.now() - 12 * 60000).toISOString(),
    type: "strong_signal",
    title: "Surge in enterprise AI agent adoption",
    description: "Multiple Fortune 500 companies announced AI agent deployment roadmaps this week, indicating accelerated market shift.",
    read: false,
  },
  {
    id: "a2",
    timestamp: new Date(Date.now() - 45 * 60000).toISOString(),
    type: "emerging_trend",
    title: "Open-weight model performance parity",
    description: "Latest benchmarks show open-weight models closing gap with proprietary offerings across reasoning tasks.",
    read: false,
  },
  {
    id: "a3",
    timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
    type: "weak_signal",
    title: "Novel hardware architecture for inference",
    description: "Research papers from two independent groups describe photonic computing approaches for transformer inference.",
    read: true,
  },
  {
    id: "a4",
    timestamp: new Date(Date.now() - 5 * 3600000).toISOString(),
    type: "emerging_trend",
    title: "Regulatory framework convergence",
    description: "EU AI Act implementation timelines align with emerging US executive order requirements, creating unified compliance landscape.",
    read: true,
  },
  {
    id: "a5",
    timestamp: new Date(Date.now() - 8 * 3600000).toISOString(),
    type: "weak_signal",
    title: "Decentralized training protocols gaining traction",
    description: "Three new startups funded this month working on distributed model training across heterogeneous compute.",
    read: true,
  },
  {
    id: "a6",
    timestamp: new Date(Date.now() - 14 * 3600000).toISOString(),
    type: "system",
    title: "Weekly intelligence digest generated",
    description: "Your personalized weak signals digest for this week is now available for review.",
    read: true,
  },
  {
    id: "a7",
    timestamp: new Date(Date.now() - 22 * 3600000).toISOString(),
    type: "strong_signal",
    title: "Major cloud provider launches model marketplace",
    description: "AWS announced general availability of its fine-tuned model marketplace, changing distribution dynamics.",
    read: true,
  },
];

const typeConfig = {
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
  system: {
    icon: Zap,
    color: "text-slate-400",
    bg: "bg-slate-500/10",
    border: "border-slate-500/20",
  },
};

export default function AlertFeed({ alerts: propAlerts, maxItems = 10 }: AlertFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const alerts = (propAlerts || MOCK_ALERTS).slice(0, maxItems);
  const unreadCount = alerts.filter((a) => !a.read).length;

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [alerts]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">Alert Feed</h3>
        </div>
        {unreadCount > 0 && (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/15 text-blue-400 border border-blue-500/25">
            {unreadCount} new
          </span>
        )}
      </div>

      {/* Feed */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 pr-1">
        {alerts.map((alert) => {
          const config = typeConfig[alert.type];
          const Icon = config.icon;
          return (
            <div
              key={alert.id}
              className={`flex gap-3 p-3 rounded-lg border transition-all duration-200 cursor-pointer hover:bg-slate-800/40 ${
                alert.read
                  ? "border-slate-800/50 bg-transparent"
                  : `${config.border} ${config.bg}`
              }`}
            >
              <div className={`shrink-0 mt-0.5 ${config.color}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <h4
                    className={`text-xs font-medium leading-tight ${
                      alert.read ? "text-slate-400" : "text-slate-200"
                    }`}
                  >
                    {alert.title}
                  </h4>
                  {!alert.read && (
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0 mt-1" />
                  )}
                </div>
                <p className="text-[11px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                  {alert.description}
                </p>
                <p className="text-[10px] text-slate-600 mt-1.5">
                  {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
