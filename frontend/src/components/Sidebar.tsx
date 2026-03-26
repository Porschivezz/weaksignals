"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Radio,
  Globe2,
  Bookmark,
  FileText,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Radar,
  Play,
} from "lucide-react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";
import { triggerIngestion } from "@/lib/api";

const navItems = [
  { href: "/dashboard", label: "Обзор", icon: LayoutDashboard },
  { href: "/dashboard/signals", label: "Сигналы", icon: Radio },
  { href: "/dashboard/landscape", label: "Ландшафт", icon: Globe2 },
  { href: "/dashboard/watchlist", label: "Вотчлист", icon: Bookmark },
  { href: "/dashboard/digest", label: "Дайджест", icon: FileText },
];

interface SidebarProps {
  tenantName?: string;
  userName?: string;
  userRole?: string;
}

export default function Sidebar({
  tenantName = "Фармасинтез",
  userName = "CEO",
  userRole = "user",
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  const handleLogout = () => {
    Cookies.remove("access_token");
    Cookies.remove("user");
    router.push("/login");
  };

  const handleTriggerPipeline = async () => {
    setPipelineLoading(true);
    try {
      await triggerIngestion();
    } catch {
      // Pipeline trigger may fail silently
    } finally {
      setPipelineLoading(false);
    }
  };

  const canTrigger = userRole === "ceo" || userRole === "admin";

  return (
    <aside
      className={`fixed left-0 top-0 h-full bg-slate-900/95 border-r border-slate-800 backdrop-blur-sm z-40 flex flex-col transition-all duration-300 ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-slate-800 shrink-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 shrink-0">
          <Radar className="w-4 h-4 text-white" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <h1 className="text-sm font-bold text-white truncate">Huginn & Muninn</h1>
            <p className="text-[10px] text-slate-500 truncate">Мониторинг слабых сигналов</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group ${
                active
                  ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
              }`}
            >
              <Icon
                className={`w-5 h-5 shrink-0 transition-colors ${
                  active ? "text-blue-400" : "text-slate-500 group-hover:text-slate-300"
                }`}
              />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}

        {/* Pipeline trigger button */}
        {canTrigger && (
          <button
            onClick={handleTriggerPipeline}
            disabled={pipelineLoading}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 text-emerald-400 hover:bg-emerald-500/10 border border-transparent hover:border-emerald-500/20 disabled:opacity-50"
          >
            <Play className={`w-5 h-5 shrink-0 ${pipelineLoading ? "animate-pulse" : ""}`} />
            {!collapsed && (
              <span className="truncate">
                {pipelineLoading ? "Запуск..." : "Запустить сбор"}
              </span>
            )}
          </button>
        )}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-slate-800 p-3 space-y-2 shrink-0">
        {!collapsed && (
          <div className="px-2 py-1.5">
            <p className="text-xs font-medium text-slate-300 truncate">{userName}</p>
            <p className="text-[10px] text-slate-500 truncate">{tenantName}</p>
          </div>
        )}

        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
        >
          <LogOut className="w-4 h-4 shrink-0" />
          {!collapsed && <span>Выйти</span>}
        </button>

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center w-full py-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
}
