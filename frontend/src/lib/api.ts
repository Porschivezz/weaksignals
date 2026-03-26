import axios from "axios";
import Cookies from "js-cookie";
import type {
  TenantSignal,
  SignalTrajectoryPoint,
  LandscapeData,
  WeeklyDigest,
  Tenant,
  User,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = Cookies.get("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove("access_token");
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export async function login(
  email: string,
  password: string
): Promise<{ access_token: string; user: User }> {
  const response = await api.post("/auth/login", { email, password });
  return response.data;
}

export async function getSignals(params?: {
  category?: string;
  cluster?: string;
  min_score?: number;
  time_range?: string;
  limit?: number;
  offset?: number;
}): Promise<TenantSignal[]> {
  const response = await api.get("/signals", { params });
  return response.data;
}

export async function getSignal(id: string): Promise<TenantSignal> {
  const response = await api.get(`/signals/${id}`);
  return response.data;
}

export async function getSignalTrajectory(
  id: string
): Promise<SignalTrajectoryPoint[]> {
  const response = await api.get(`/signals/${id}/trajectory`);
  return response.data;
}

export async function getLandscape(): Promise<LandscapeData> {
  const response = await api.get("/landscape");
  return response.data;
}

export async function getWeeklyDigest(top_n?: number): Promise<WeeklyDigest> {
  const response = await api.get("/digest/weekly", { params: top_n ? { top_n } : {} });
  return response.data;
}

export async function getWatchlist(): Promise<string[]> {
  const response = await api.get("/tenant/watchlist");
  return response.data;
}

export async function addToWatchlist(technology: string): Promise<void> {
  await api.post("/tenant/watchlist", { technology });
}

export async function removeFromWatchlist(technology: string): Promise<void> {
  await api.delete(`/tenant/watchlist/${encodeURIComponent(technology)}`);
}

export async function dismissSignal(signalId: string): Promise<void> {
  await api.post(`/signals/${signalId}/dismiss`);
}

export async function getTenant(): Promise<Tenant> {
  const response = await api.get("/tenant");
  return response.data;
}

export async function updateTenant(
  data: Partial<Pick<Tenant, "industry_verticals" | "technology_watchlist">>
): Promise<Tenant> {
  const response = await api.patch("/tenant", data);
  return response.data;
}

export async function triggerIngestion(): Promise<{ status: string; task_id: string; message: string }> {
  const response = await api.post("/pipeline/trigger-ingestion");
  return response.data;
}

export async function triggerAnalysis(): Promise<{ status: string; task_id: string; message: string }> {
  const response = await api.post("/pipeline/trigger-analysis");
  return response.data;
}

export default api;
