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

const statusConfig = {
  active: { label: "Активно", color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
  quiet: { label: "Тихо", color: "text-slate-400", bg: "bg-slate-500/10", border: "border-slate-500/20" },
  trending: { label: "В тренде", color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
};

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [newTech, setNewTech] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchWatchlist() {
      try {
        const data = await getWatchlist();
        if (data && data.length > 0) {
          const watchItems: WatchlistItem[] = data.map((name) => ({
            name,
            status: "active" as const,
            lastActivity: new Date().toISOString(),
            signalCount: 0,
          }));
          setItems(watchItems);
        }
      } catch {
        // No data
      } finally {
        setLoading(false);
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
      // Add locally
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
      // Remove locally
    }
    setItems((prev) => prev.filter((i) => i.name !== name));
  };

  const filtered = items.filter((i) =>
    i.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Вотчлист технологий</h1>
        <p className="text-sm text-slate-500 mt-1">
          Мониторинг ключевых технологий и направлений R&D
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="card-compact">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Отслеживаемых</p>
          <p className="text-2xl font-bold text-white mt-1">{items.length}</p>
        </div>
        <div className="card-compact">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Активных</p>
          <p className="text-2xl font-bold text-emerald-400 mt-1">
            {items.filter((i) => i.status !== "quiet").length}
          </p>
        </div>
      </div>

      {/* Add new technology */}
      <div className="card">
        <h3 className="text-sm font-semibold text-slate-200 mb-3">Добавить технологию</h3>
        <div className="flex gap-3">
          <input
            type="text"
            value={newTech}
            onChange={(e) => setNewTech(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="Название технологии (например, CAR-T терапия)"
            className="input-field flex-1"
          />
          <button onClick={handleAdd} className="btn-primary shrink-0">
            <Plus className="w-4 h-4 mr-1" />
            Добавить
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
          placeholder="Поиск..."
          className="input-field pl-10"
        />
      </div>

      {/* Watchlist items */}
      <div className="space-y-2">
        {loading ? (
          <div className="text-center py-12">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-slate-500 text-sm">Загрузка...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-slate-500 text-sm">
              {searchTerm
                ? "Ничего не найдено."
                : "Вотчлист пуст. Добавьте технологии для мониторинга."}
            </p>
          </div>
        ) : (
          filtered.map((item) => {
            const config = statusConfig[item.status];
            return (
              <div
                key={item.name}
                className="card-compact flex items-center justify-between group animate-fade-in"
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      item.status === "active"
                        ? "bg-emerald-400"
                        : item.status === "trending"
                        ? "bg-blue-400"
                        : "bg-slate-500"
                    }`}
                  />
                  <div className="min-w-0">
                    <h3 className="text-sm font-medium text-slate-200 truncate">
                      {item.name}
                    </h3>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span
                        className={`badge text-[10px] ${config.bg} ${config.color} border ${config.border}`}
                      >
                        {config.label}
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
          })
        )}
      </div>
    </div>
  );
}
