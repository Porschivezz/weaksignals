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
} from "lucide-react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/signals", label: "Signals", icon: Radio },
  { href: "/dashboard/landscape", label: "Landscape", icon: Globe2 },
  { href: "/dashboard/watchlist", label: "Watchlist", icon: Bookmark },
  { href: "/dashboard/digest", label: "Digest", icon: FileText },
];

interface SidebarProps {
  tenantName?: string;
  userName?: string;
}

export default function Sidebar({ tenantName = "Acme Corp", userName = "CEO" }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
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
            <h1 className="text-sm font-bold text-white truncate">Huginn &amp; Muninn</h1>
            <p className="text-[10px] text-slate-500 truncate">Weak Signals Monitor</p>
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
          {!collapsed && <span>Sign Out</span>}
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
