"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import Sidebar from "@/components/Sidebar";
import type { User } from "@/lib/types";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const token = Cookies.get("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    const userCookie = Cookies.get("user");
    if (userCookie) {
      try {
        setUser(JSON.parse(userCookie));
      } catch {
        setUser({ id: "1", email: "ceo@pharmasyntez.com", full_name: "Пользователь", role: "ceo" });
      }
    } else {
      setUser({ id: "1", email: "ceo@pharmasyntez.com", full_name: "Пользователь", role: "ceo" });
    }

    setLoading(false);
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-400 text-sm">Загрузка...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <Sidebar
        tenantName="ГК Фармасинтез"
        userName={user?.full_name || "Пользователь"}
        userRole={user?.role || "user"}
      />
      <main className="pl-60 min-h-screen">
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
