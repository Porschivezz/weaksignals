"use client";

import { useState, useEffect } from "react";
import { Plus, X, Activity, Clock, Search } from "lucide-react";
import { getWatchlist, addToWatchlist, removeFromWatchlist } from "@/lib/api";

interface WatchlistItem {
  name: string;
  status: "active" | "quiet" | "trending";
  lastActivity: string;
  signalCount: number;
}

const MOCK_WATCHLIST: WatchlistItem[] = [
  { name: "Transformer Architecture", status: "active", lastActivity: "2026-03-22T14:00:00Z", signalCount: 12 },
  { name: "Mixture of Experts", status: "trending", lastActivity: "2026-03-21T10:30:00Z", signalCount: 8 },
  { name: "AI Agents", status: "trending", lastActivity: "2026-03-22T16:00:00Z", signalCount: 15 },
  { name: "LoRA Fine-tuning", status: "active", lastActivity: "2026-03-20T09:00:00Z", signalCount: 5 },
  { name: "Retrieval Augmented Generation", status: "active", lastActivity: "2026-03-19T14:20:00Z", signalCount: 9 },
  { name: "Edge AI Inference", status: "active", lastActivity: "2026-03-18T11:00:00Z", signalCount: 6 },
  { name: "Photonic Computing", status: "quiet", lastActivity: "2026-03-15T08:00:00Z", signalCount: 2 },
  { name: "Neuromorphic Computing", status: "quiet", lastActivity: "2026-03-12T16:30:00Z", signalCount: 3 },
  { name: "AI Safety Standards", status: "active", lastActivity: "2026-03-21T12:00:00Z", signalCount: 7 },
  { name: "Synthetic Data Generation", status: "trending", lastActivity: "2026-03-22T08:45:00Z", signalCount: 11 },
  { name: "Quantization Methods", status: "active", lastActivity: "2026-03-17T10:15:00Z", signalCount: 4 },
  { name: "EU AI Act Compliance", status: "trending", lastActivity: "2026-03-22T16:30:00Z", signalCount: 14 },
  { name: "Multimodal Reasoning", status: "active", lastActivity: "2026-03-20T14:00:00Z", signalCount: 8 },
  { name: "Decentralized Training", status: "quiet", lastActivity: "2026-03-10T09:30:00Z", signalCount: 2 },
];

const statusConfig = {
  active: { label: "Active", color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
  quiet: { label: "Quiet", color: "text-slate-400", bg: "bg-slate-500/10", border: "border-slate-500/20" },
  trending: { label: "Trending", color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
};

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>(MOCK_WATCHLIST);
  const [newTech, setNewTech] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    async function fetchWatchlist() {
      try {
        const data = await getWatchlist();
        if (data && data.length > 0) {
          const watchItems: WatchlistItem[] = data.map((name) => ({
            name,
            status: "active" as const,
            lastActivity: new Date().toISOString(),
            signalCount: Math.floor(Math.random() * 10) + 1,
          }));
          setItems(watchItems);
        }
      } catch {
        // Use mock data
      }
    }
    fetchWatchlist();
  }, []);

  const handleAdd = async () => {
    const trimmed = newTech.trim();
    if (!trimmed) return;
    if (items.some((i) => i.name.toLowerCase() === trimmed.toLowerCase())) return;

    try {
      await addToWatchlist(trimmed);
    } catch {
      // Add locally on API failure
    }

    setItems((prev) => [
      {
        name: trimmed,
        status: "active",
        lastActivity: new Date().toISOString(),
        signalCount: 0,
      },
      ...prev,
    ]);
    setNewTech("");
  };

  const handleRemove = async (name: string) => {
    try {
      await removeFromWatchlist(name);
    } catch {
      // Remove locally on API failure
    }
    setItems((prev) => prev.filter((i) => i.name !== name));
  };

  const filtered = items.filter((i) =>
    i.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const trendingCount = items.filter((i) => i.status === "trending").length;
  const totalSignals = items.reduce((sum, i) => sum + i.signalCount, 0);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Technology Watchlist</h1>
        <p className="text-sm text-slate-500 mt-1">
          Monitor specific technologies and concepts for emerging signals
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card-compact">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Watched Technologies</p>
          <p className="text-2xl font-bold text-white mt-1">{items.length}</p>
        </div>
        <div className="card-compact">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Currently Trending</p>
          <p className="text-2xl font-bold text-blue-400 mt-1">{trendingCount}</p>
        </div>
        <div className="card-compact">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Related Signals</p>
          <p className="text-2xl font-bold text-amber-400 mt-1">{totalSignals}</p>
        </div>
      </div>

      {/* Add new technology */}
      <div className="card">
        <h3 className="text-sm font-semibold text-slate-200 mb-3">Add Technology to Watch</h3>
        <div className="flex gap-3">
          <input
            type="text"
            value={newTech}
            onChange={(e) => setNewTech(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="Enter technology name (e.g., Quantum Machine Learning)"
            className="input-field flex-1"
          />
          <button onClick={handleAdd} className="btn-primary shrink-0">
            <Plus className="w-4 h-4 mr-1" />
            Add
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search watchlist..."
          className="input-field pl-10"
        />
      </div>

      {/* Watchlist items */}
      <div className="space-y-2">
        {filtered.map((item) => {
          const config = statusConfig[item.status];
          return (
            <div
              key={item.name}
              className="card-compact flex items-center justify-between group animate-fade-in"
            >
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className={`w-2 h-2 rounded-full ${config.color === "text-emerald-400" ? "bg-emerald-400" : config.color === "text-blue-400" ? "bg-blue-400" : "bg-slate-500"}`} />
                <div className="min-w-0">
                  <h3 className="text-sm font-medium text-slate-200 truncate">
                    {item.name}
                  </h3>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className={`badge text-[10px] ${config.bg} ${config.color} border ${config.border}`}>
                      {config.label}
                    </span>
                    <span className="text-[10px] text-slate-600 flex items-center gap-1">
                      <Activity className="w-3 h-3" />
                      {item.signalCount} signals
                    </span>
                    <span className="text-[10px] text-slate-600 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(item.lastActivity).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleRemove(item.name)}
                className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-600 hover:text-red-400 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="text-center py-12">
            <p className="text-slate-500 text-sm">
              {searchTerm ? "No technologies match your search." : "Your watchlist is empty. Add technologies to monitor."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
