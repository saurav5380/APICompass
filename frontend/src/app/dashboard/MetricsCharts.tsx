'use client';

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { MetricsTrendPoint } from "@/hooks/useMetrics";

const SAMPLE_TREND: MetricsTrendPoint[] = [
  { day: "2024-06-01", calls: 18234, errors: 152, spend: 3250 },
  { day: "2024-06-02", calls: 17560, errors: 138, spend: 3420 },
  { day: "2024-06-03", calls: 19822, errors: 201, spend: 3680 },
  { day: "2024-06-04", calls: 21044, errors: 188, spend: 4120 },
  { day: "2024-06-05", calls: 19990, errors: 176, spend: 3870 },
  { day: "2024-06-06", calls: 20510, errors: 190, spend: 4010 },
  { day: "2024-06-07", calls: 21133, errors: 204, spend: 4280 },
];

const formatDayLabel = (value: string) => {
  const date = new Date(value);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

interface MetricsChartsProps {
  data?: MetricsTrendPoint[];
  loading: boolean;
  error: Error | null;
}

const ChartShell = ({ children, title }: { children: React.ReactNode; title: string }) => (
  <div className="rounded-3xl border border-white/10 bg-slate-950/60 p-4 text-white shadow-inner">
    <p className="mb-3 text-sm uppercase tracking-wide text-white/50">{title}</p>
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  </div>
);

export default function MetricsCharts({ data, loading, error }: MetricsChartsProps) {
  if (loading) {
    return <p className="text-sm text-white/70">Rendering charts…</p>;
  }

  if (error) {
    return <p className="text-sm text-rose-300">Charts unavailable: {error.message}</p>;
  }

  const resolved = data && data.length > 0 ? data : SAMPLE_TREND;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <ChartShell title="API calls per day">
        <LineChart data={resolved} margin={{ left: -20, right: 10 }}>
          <CartesianGrid strokeDasharray="4 4" stroke="#ffffff16" />
          <XAxis
            dataKey="day"
            stroke="#94a3b8"
            tickFormatter={formatDayLabel}
            fontSize={12}
          />
          <YAxis stroke="#94a3b8" fontSize={12} tickFormatter={(value) => `${(value / 1000).toFixed(1)}k`} />
          <Tooltip
            contentStyle={{ backgroundColor: "#0f172a", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)" }}
            labelFormatter={(value) => formatDayLabel(String(value))}
            formatter={(value: number) => [value.toLocaleString(), "calls"]}
          />
          <Legend />
          <Line type="monotone" dataKey="calls" stroke="#34d399" strokeWidth={3} dot={false} name="Calls" />
        </LineChart>
      </ChartShell>

      <ChartShell title="Errors per day">
        <LineChart data={resolved} margin={{ left: -20, right: 10 }}>
          <CartesianGrid strokeDasharray="4 4" stroke="#ffffff16" />
          <XAxis dataKey="day" stroke="#94a3b8" tickFormatter={formatDayLabel} fontSize={12} />
          <YAxis stroke="#94a3b8" fontSize={12} tickFormatter={(value) => value.toString()} />
          <Tooltip
            contentStyle={{ backgroundColor: "#0f172a", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)" }}
            labelFormatter={(value) => formatDayLabel(String(value))}
            formatter={(value: number) => [value.toLocaleString(), "errors"]}
          />
          <Legend />
          <Line type="monotone" dataKey="errors" stroke="#fb7185" strokeWidth={3} dot={false} name="Errors" />
        </LineChart>
      </ChartShell>

      <div className="lg:col-span-2">
        <ChartShell title="Daily cost trend">
          <AreaChart data={resolved} margin={{ left: -20, right: 10 }}>
            <defs>
              <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff16" />
            <XAxis dataKey="day" stroke="#94a3b8" tickFormatter={formatDayLabel} fontSize={12} />
            <YAxis
              stroke="#94a3b8"
              fontSize={12}
              tickFormatter={(value) => `$${(Number(value) / 1000).toFixed(1)}k`}
            />
            <Tooltip
              contentStyle={{ backgroundColor: "#0f172a", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)" }}
              labelFormatter={(value) => formatDayLabel(String(value))}
              formatter={(value: number) => [`$${value.toLocaleString()}`, "Spend"]}
            />
            <Area
              type="monotone"
              dataKey="spend"
              stroke="#60a5fa"
              fillOpacity={1}
              fill="url(#costGradient)"
              name="Spend"
            />
          </AreaChart>
        </ChartShell>
      </div>
    </div>
  );
}
