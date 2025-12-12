'use client';

import { useQuery } from "@tanstack/react-query";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface MetricsOverviewResponse {
  start_date: string;
  end_date: string;
  provider?: string | null;
  total_calls: number;
  total_errors: number;
  total_spend: number;
}

interface MetricsTrendPoint {
  day: string;
  calls: number;
  errors: number;
  spend: number;
}

export interface MetricsFilters {
  provider: string;
  service: string;
  start: string;
  end: string;
}

const fetchJson = async <T,>(url: string) => {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as T;
};

const buildQuery = (path: string, filters: MetricsFilters) => {
  const url = new URL(path, API_BASE);
  if (filters.start) {
    url.searchParams.set("start_date", filters.start);
  }
  if (filters.end) {
    url.searchParams.set("end_date", filters.end);
  }
  if (filters.provider && filters.provider !== "all") {
    url.searchParams.set("provider", filters.provider);
  }
  return url.toString();
};

export const useMetricsOverview = (filters: MetricsFilters) =>
  useQuery({
    queryKey: ["metrics", "overview", filters],
    queryFn: () =>
      fetchJson<MetricsOverviewResponse>(buildQuery("/metrics/overview", filters)),
  });

export const useMetricsTrends = (filters: MetricsFilters) =>
  useQuery({
    queryKey: ["metrics", "trends", filters],
    queryFn: () => fetchJson<MetricsTrendPoint[]>(buildQuery("/metrics/trends", filters)),
  });
