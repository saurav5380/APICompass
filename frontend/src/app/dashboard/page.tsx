'use client';

import { useMemo, useState } from "react";

type ThemeMode = "light" | "dark";
type ViewKey = "overview" | "providers" | "alerts" | "settings";
type ProviderId = "openai" | "twilio" | "sendgrid";

interface UsageProjectionRecord {
  provider: ProviderId;
  environment: string;
  currency: string;
  month_to_date_spend: number;
  projected_total: number;
  projected_min: number;
  projected_max: number;
  rolling_avg_7d: number | null;
  rolling_avg_14d: number | null;
  sample_days: number;
  tooltip: string;
  budget_limit?: number | null;
  budget_remaining?: number | null;
  budget_consumed_percent?: number | null;
}

interface UsageSeriesPoint {
  label: string;
  value: number;
}

interface ConnectionRecord {
  id: string;
  provider: ProviderId | string;
  environment: string;
  status: string;
  masked_key: string;
  display_name?: string | null;
  created_at: string;
  local_connector_enabled?: boolean;
  local_agent_last_seen_at?: string | null;
}

interface AlertRule {
  id: string;
  provider: ProviderId | "all";
  thresholdPercent: number;
  channel: "email" | "slack";
  frequency: "realtime" | "daily";
  enabled: boolean;
  createdAt: string;
}

interface UsageTipRecord {
  title: string;
  body: string;
  reason: string;
  link: string;
}

type ManifestMode = "json" | "yaml";

interface PricingTier {
  upto: number | null;
  rate: number;
}

interface ConnectorManifest {
  name: string;
  slug: string;
  environment: string;
  auth: {
    type: "header";
    headerName: string;
    prefix: string;
    placeholderKey: string;
  };
  endpoint: {
    url: string;
    method: "GET" | "POST";
    pagination: {
      strategy: "cursor" | "page" | "offset" | "none";
      cursorParam?: string;
      nextCursorPath?: string;
      pageParam?: string;
      pageSizeParam?: string;
    };
    jsonpath: string;
  };
  mapping: {
    recordsPath: string;
    idPath: string;
    usagePath: string;
    timestampPath: string;
    metadataPaths: Record<string, string>;
  };
  pricing: {
    template: "flat" | "tiered";
    currency: string;
    unitName: string;
    flatRate?: number;
    tiers?: PricingTier[];
  };
}

interface NormalizedRow {
  id: string;
  timestamp: string;
  units: number;
  cost: number;
  metadata: Record<string, string | number | null>;
}

interface DryRunStats {
  rows: NormalizedRow[];
  totalUnits: number;
  dailyCost: number;
  monthlyCost: number;
  currency: string;
  sampleCount: number;
}

const SAMPLE_USAGE_SERIES = createSyntheticSeries(30);

const SAMPLE_USAGE_PROJECTIONS: UsageProjectionRecord[] = [
  {
    provider: "openai",
    environment: "prod",
    currency: "USD",
    month_to_date_spend: 3600,
    projected_total: 4800,
    projected_min: 4300,
    projected_max: 5200,
    rolling_avg_7d: 132,
    rolling_avg_14d: 126,
    sample_days: 24,
    tooltip: "Synthetic projection for demo purposes.",
    budget_limit: 5000,
    budget_remaining: 1200,
    budget_consumed_percent: 72,
  },
  {
    provider: "twilio",
    environment: "prod",
    currency: "USD",
    month_to_date_spend: 1450,
    projected_total: 1900,
    projected_min: 1700,
    projected_max: 2200,
    rolling_avg_7d: 54,
    rolling_avg_14d: 52,
    sample_days: 24,
    tooltip: "Synthetic projection for demo purposes.",
    budget_limit: 2500,
    budget_remaining: 1050,
    budget_consumed_percent: 42,
  },
  {
    provider: "sendgrid",
    environment: "staging",
    currency: "USD",
    month_to_date_spend: 640,
    projected_total: 910,
    projected_min: 850,
    projected_max: 1080,
    rolling_avg_7d: 24,
    rolling_avg_14d: 21,
    sample_days: 24,
    tooltip: "Synthetic projection for demo purposes.",
    budget_limit: 1200,
    budget_remaining: 560,
    budget_consumed_percent: 46,
  },
];

const SAMPLE_CONNECTIONS: ConnectionRecord[] = [
  {
    id: "sample-openai",
    provider: "openai",
    environment: "prod",
    status: "active",
    masked_key: "sk-live-***xy12",
    display_name: "OpenAI . prod",
    created_at: new Date().toISOString(),
  },
  {
    id: "sample-twilio",
    provider: "twilio",
    environment: "prod",
    status: "active",
    masked_key: "twilio-***45ab",
    display_name: "Twilio . prod",
    created_at: new Date().toISOString(),
    local_connector_enabled: true,
    local_agent_last_seen_at: new Date().toISOString(),
  },
  {
    id: "sample-sendgrid",
    provider: "sendgrid",
    environment: "staging",
    status: "active",
    masked_key: "sg-***bb90",
    display_name: "SendGrid . staging",
    created_at: new Date().toISOString(),
  },
];

const SAMPLE_ALERTS: AlertRule[] = [
  {
    id: "sample-alert-openai",
    provider: "openai",
    thresholdPercent: 85,
    channel: "email",
    frequency: "realtime",
    enabled: true,
    createdAt: new Date().toISOString(),
  },
  {
    id: "sample-alert-all",
    provider: "all",
    thresholdPercent: 120,
    channel: "slack",
    frequency: "daily",
    enabled: true,
    createdAt: new Date().toISOString(),
  },
];

const SAMPLE_TIPS: UsageTipRecord[] = [
  {
    title: "Tighten OpenAI scopes",
    body: "The prod key still has write permissions. Rotate to a read-only key to reduce blast radius.",
    reason: "Scoped ingest detected write role",
    link: "https://platform.openai.com/account/api-keys",
  },
  {
    title: "Revisit Twilio SMS mix",
    body: "MMS usage dipped three days in a row. Confirm campaign targeting before the weekend push.",
    reason: "Messaging channel imbalance",
    link: "https://www.twilio.com/docs",
  },
  {
    title: "SendGrid warm-up",
    body: "Stage traffic is 25 percent below forecast. Keep warming before routing preview builds to prod.",
    reason: "Stage deliverability",
    link: "https://www.twilio.com/docs/sendgrid/api-reference/ip-warmup/start-warming-up-an-ip-address",
  },
];

const DEFAULT_MANIFEST: ConnectorManifest = {
  name: "Notion AI usage",
  slug: "notion-ai",
  environment: "prod",
  auth: {
    type: "header",
    headerName: "X-Notion-Key",
    prefix: "Bearer ",
    placeholderKey: "notion-sk-***",
  },
  endpoint: {
    url: "https://api.notion.com/v1/usage",
    method: "GET",
    pagination: {
      strategy: "cursor",
      cursorParam: "start_cursor",
      nextCursorPath: "$.next_cursor",
      pageSizeParam: "page_size",
    },
    jsonpath: "$.events",
  },
  mapping: {
    recordsPath: "$.events",
    idPath: "event_id",
    usagePath: "tokens",
    timestampPath: "timestamp",
    metadataPaths: {
      model: "model",
      project: "project",
    },
  },
  pricing: {
    template: "flat",
    currency: "USD",
    unitName: "1K tokens",
    flatRate: 0.002,
    tiers: [
      { upto: 500000, rate: 0.002 },
      { upto: null, rate: 0.0015 },
    ],
  },
};

const DEFAULT_SAMPLE_PAYLOAD = JSON.stringify(
  {
    next_cursor: "evt_004",
    events: [
      {
        event_id: "evt_001",
        timestamp: "2024-06-01T08:00:00Z",
        tokens: 2.1,
        model: "notion-gpt-small",
        project: "prod-docs",
      },
      {
        event_id: "evt_002",
        timestamp: "2024-06-01T09:00:00Z",
        tokens: 3.4,
        model: "notion-gpt-small",
        project: "prod-docs",
      },
      {
        event_id: "evt_003",
        timestamp: "2024-06-01T10:00:00Z",
        tokens: 4.8,
        model: "notion-gpt-large",
        project: "experiments",
      },
    ],
  },
  null,
  2,
);

const VIEW_OPTIONS: Array<{ id: ViewKey; label: string; description: string }> = [
  { id: "overview", label: "Overview", description: "Budget bar and forecast" },
  { id: "providers", label: "Providers", description: "Connections and usage" },
  { id: "alerts", label: "Alerts", description: "Rules and digests" },
  { id: "settings", label: "Settings", description: "Caps and policies" },
];

const PROVIDER_LABEL: Record<ProviderId, string> = {
  openai: "OpenAI",
  twilio: "Twilio",
  sendgrid: "SendGrid",
};

function formatNumber(value: number, digits = 2) {
  return Number(value).toFixed(digits);
}

function objectToYaml(value: unknown, indent = 0): string {
  const spacing = "  ".repeat(indent);
  if (Array.isArray(value)) {
    return value
      .map((entry) => {
        if (typeof entry === "object" && entry !== null) {
          const nested = objectToYaml(entry, indent + 1);
          return `${spacing}-\n${nested}`;
        }
        return `${spacing}- ${objectToYaml(entry, 0).trim()}`;
      })
      .join("\n");
  }
  if (typeof value === "object" && value !== null) {
    return Object.entries(value)
      .map(([key, entry]) => {
        const safeKey = key;
        if (typeof entry === "object" && entry !== null) {
          const nested = objectToYaml(entry, indent + 1);
          return `${spacing}${safeKey}:\n${nested}`;
        }
        return `${spacing}${safeKey}: ${objectToYaml(entry, 0).trim()}`;
      })
      .join("\n");
  }
  if (typeof value === "string") {
    if (value === "" || /[:#\-\n]/.test(value)) {
      return `"${value.replace(/"/g, '\\"')}"`;
    }
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "null";
}

function extractSegments(path: string) {
  const cleaned = path.replace(/^\$?\./, "").replace(/^\$/, "");
  const rawSegments = cleaned.split(".");
  const segments: string[] = [];
  rawSegments.forEach((segment) => {
    const parts = segment.split(/[\[\]]/).filter((part) => part !== "");
    segments.push(...parts);
  });
  return segments.filter(Boolean);
}

function extractValueFromPath(data: unknown, path: string): any {
  if (!path) return undefined;
  const segments = extractSegments(path);
  let current: any = data;
  for (const segment of segments) {
    if (current === null || current === undefined) return undefined;
    if (Array.isArray(current)) {
      const index = Number(segment);
      current = Number.isNaN(index) ? undefined : current[index];
    } else {
      current = current[segment];
    }
  }
  return current;
}

function extractRecords(payload: string, recordsPath: string): any[] {
  const parsed = JSON.parse(payload);
  const records = extractValueFromPath(parsed, recordsPath);
  if (!Array.isArray(records)) {
    throw new Error("Records path did not return an array.");
  }
  return records;
}

function calculateCost(units: number, pricing: ConnectorManifest["pricing"]): number {
  if (pricing.template === "flat") {
    const rate = pricing.flatRate ?? 0;
    return units * rate;
  }
  const tiers = pricing.tiers ?? [];
  if (tiers.length === 0) {
    return units * (pricing.flatRate ?? 0);
  }
  let remaining = units;
  let cost = 0;
  let previousCap = 0;
  for (const tier of tiers) {
    const cap = tier.upto ?? Infinity;
    const span = cap - previousCap;
    const eligible = Math.min(Math.max(remaining, 0), span);
    if (eligible > 0) {
      cost += eligible * tier.rate;
      remaining -= eligible;
    }
    previousCap = cap;
    if (remaining <= 0) break;
  }
  if (remaining > 0) {
    const lastRate = tiers[tiers.length - 1]?.rate ?? pricing.flatRate ?? 0;
    cost += remaining * lastRate;
  }
  return cost;
}

function formatCurrency(value: number, currency: string) {
  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency.toUpperCase(),
    maximumFractionDigits: 0,
  });
  return formatter.format(value);
}

function createSyntheticSeries(days: number): UsageSeriesPoint[] {
  return Array.from({ length: days }, (_, index) => {
    const drift = index * 15;
    const seasonal = Math.sin(index / 3) * 60;
    const base = 180 + drift + seasonal;
    return {
      label: `Day ${index + 1}`,
      value: Math.max(60, Math.round(base)),
    };
  });
}

function buildUsageSeriesFromProjection(summary: UsageProjectionRecord | undefined): UsageSeriesPoint[] {
  if (!summary) return SAMPLE_USAGE_SERIES;
  const days = 30;
  const baseSeries = SAMPLE_USAGE_SERIES.slice(0, days);
  const baseSum = baseSeries.reduce((total, point) => total + point.value, 0);
  const targetTotal = summary.month_to_date_spend || 1;
  const scale = targetTotal / (baseSum || 1);
  return baseSeries.map((point, index) => {
    const trendBoost = 0.9 + (index / days) * 0.35;
    return {
      label: point.label,
      value: Math.max(50, Math.round(point.value * scale * trendBoost)),
    };
  });
}

function UsageSparkline({ series, isDark }: { series: UsageSeriesPoint[]; isDark: boolean }) {
  if (series.length === 0) {
    return <p className={`text-sm ${isDark ? "text-slate-400" : "text-zinc-500"}`}>No usage samples yet.</p>;
  }
  const width = 360;
  const height = 140;
  const maxValue = Math.max(...series.map((point) => point.value), 1);
  const pathData = series
    .map((point, index) => {
      const x = (index / (series.length - 1 || 1)) * width;
      const y = height - (point.value / maxValue) * (height - 10);
      return `${index === 0 ? "M" : "L"}${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      role="img"
      aria-label="30 day usage trend"
      viewBox={`0 0 ${width} ${height}`}
      className="mt-4 w-full"
    >
      <defs>
        <linearGradient id="usage-gradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={isDark ? "#6366f1" : "#4338ca"} stopOpacity={isDark ? 0.35 : 0.25} />
          <stop offset="100%" stopColor={isDark ? "#6366f1" : "#4338ca"} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${pathData} L${width},${height} L0,${height} Z`} fill="url(#usage-gradient)" />
      <path
        d={pathData}
        fill="none"
        stroke={isDark ? "#c7d2fe" : "#4338ca"}
        strokeWidth={3}
        strokeLinecap="round"
      />
    </svg>
  );
}

function UsageForecastCard({
  series,
  summary,
  isDark,
}: {
  series: UsageSeriesPoint[];
  summary?: UsageProjectionRecord;
  isDark: boolean;
}) {
  const projectedLabel = summary
    ? formatCurrency(summary.projected_total, summary.currency)
    : "Sample forecast";
  return (
    <section
      className={`rounded-2xl border p-6 shadow-sm ${
        isDark ? "border-indigo-500/30 bg-slate-900" : "border-indigo-200 bg-white"
      }`}
    >
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div>
            <p className={`text-sm font-semibold uppercase tracking-wide ${isDark ? "text-indigo-300" : "text-indigo-600"}`}>
              Usage forecast
            </p>
            <h3 className={`text-2xl font-bold ${isDark ? "text-indigo-100" : "text-indigo-900"}`}>{projectedLabel}</h3>
            <p className={`text-xs ${isDark ? "text-indigo-200" : "text-indigo-600"}`}>
              30 day synthetic series scaled to month to date spend
            </p>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              isDark ? "bg-indigo-500/20 text-indigo-100" : "bg-indigo-100 text-indigo-700"
            }`}
          >
            {series.length}-day window
          </span>
        </div>
        <UsageSparkline series={series} isDark={isDark} />
      </div>
    </section>
  );
}

function ProviderBreakdown({ usage, isDark }: { usage: UsageProjectionRecord[]; isDark: boolean }) {
  if (usage.length === 0) {
    return (
      <section
        className={`rounded-2xl border border-dashed p-6 text-sm ${
          isDark ? "border-slate-600 bg-slate-900/60 text-slate-400" : "border-zinc-200 bg-white/70 text-zinc-500"
        }`}
      >
        Connect a provider or toggle sample data to see per provider projections.
      </section>
    );
  }
  const maxProjected = Math.max(...usage.map((entry) => entry.projected_total), 1);
  return (
    <section
      className={`rounded-2xl border p-6 shadow-sm ${
        isDark ? "border-slate-700 bg-slate-900 text-slate-100" : "border-zinc-200 bg-white"
      }`}
    >
      <h3 className="text-lg font-semibold">Provider breakdown</h3>
      <ul className="mt-4 space-y-4">
        {usage.map((entry) => {
          const percent = (entry.projected_total / maxProjected) * 100;
          const budgetPercent = entry.budget_consumed_percent ?? 0;
          return (
            <li key={`${entry.provider}-${entry.environment}`} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className={`font-semibold ${isDark ? "text-slate-100" : "text-zinc-900"}`}>
                  {PROVIDER_LABEL[entry.provider]} . {entry.environment.toUpperCase()}
                </span>
                <span className={isDark ? "text-slate-300" : "text-zinc-600"}>
                  {formatCurrency(entry.projected_total, entry.currency)} projected
                </span>
              </div>
              <div className={`h-2 rounded-full ${isDark ? "bg-slate-800" : "bg-zinc-100"}`}>
                <div
                  className={`h-full rounded-full ${isDark ? "bg-emerald-400" : "bg-zinc-900"}`}
                  style={{ width: `${percent}%` }}
                />
              </div>
              {entry.budget_limit && (
                <p className={`text-xs ${isDark ? "text-slate-400" : "text-zinc-500"}`}>
                  {budgetPercent.toFixed(0)} percent of {formatCurrency(entry.budget_limit, entry.currency)} cap
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function AlertsPanel({ alerts, isDark }: { alerts: AlertRule[]; isDark: boolean }) {
  return (
    <section
      className={`rounded-2xl border p-6 shadow-sm ${
        isDark ? "border-rose-500/40 bg-rose-950/30" : "border-rose-200 bg-rose-50/60"
      }`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className={`text-sm font-semibold uppercase tracking-wide ${isDark ? "text-rose-200" : "text-rose-600"}`}>
            Alert rules
          </p>
          <p className={`text-xs ${isDark ? "text-rose-100/80" : "text-rose-700"}`}>
            Email and Slack routes when spend crosses thresholds.
          </p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            isDark ? "bg-rose-500/20 text-rose-100" : "bg-rose-100 text-rose-700"
          }`}
        >
          {alerts.length} active
        </span>
      </div>
      <ul className="mt-4 space-y-3 text-sm">
        {alerts.map((alert) => (
          <li
            key={alert.id}
            className={`rounded-xl border px-4 py-3 ${
              isDark ? "border-rose-500/20 bg-slate-950/60" : "border-rose-100 bg-white"
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold">
                  {alert.thresholdPercent}% burn | {alert.frequency}
                </p>
                <p className={isDark ? "text-rose-100/80" : "text-rose-700"}>
                  {alert.provider === "all" ? "All providers" : PROVIDER_LABEL[alert.provider]} via {alert.channel}
                </p>
              </div>
              <span className={`text-xs font-semibold ${isDark ? "text-rose-200" : "text-rose-600"}`}>
                {alert.enabled ? "Enabled" : "Paused"}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ConnectionsPanel({ connections, isDark }: { connections: ConnectionRecord[]; isDark: boolean }) {
  const formatCheckIn = (timestamp?: string | null) => {
    if (!timestamp) return "Awaiting first check-in";
    try {
      return `Last check-in ${new Date(timestamp).toLocaleString()}`;
    } catch {
      return "Last check-in updating";
    }
  };

  return (
    <section
      className={`rounded-2xl border p-6 shadow-sm ${
        isDark ? "border-slate-700 bg-slate-900 text-slate-100" : "border-zinc-200 bg-white"
      }`}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Connections</h3>
        <span className="text-sm text-emerald-400">Simulated data</span>
      </div>
      <ul className="mt-4 space-y-3">
        {connections.map((connection) => (
          <li
            key={connection.id}
            className={`rounded-xl border px-4 py-3 text-sm ${
              isDark ? "border-slate-800 bg-slate-950/60" : "border-zinc-100 bg-zinc-50"
            }`}
          >
            <div className="flex items-center justify-between gap-4">
              <div className="space-y-1">
                <p className="font-semibold">{connection.display_name}</p>
                <p className={`flex items-center gap-2 ${isDark ? "text-slate-400" : "text-zinc-500"}`}>
                  {connection.masked_key}
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                      connection.local_connector_enabled
                        ? isDark
                          ? "bg-emerald-500/20 text-emerald-200"
                          : "bg-emerald-100 text-emerald-700"
                        : isDark
                          ? "bg-slate-800 text-slate-200"
                          : "bg-zinc-100 text-zinc-600"
                    }`}
                  >
                    {connection.local_connector_enabled ? "Local Connector" : "Cloud vault"}
                  </span>
                </p>
                <p className={`text-xs ${isDark ? "text-slate-400" : "text-zinc-500"}`}>
                  {connection.local_connector_enabled
                    ? formatCheckIn(connection.local_agent_last_seen_at)
                    : "Keys encrypted in server-side vault"}
                </p>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  connection.status === "active"
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-yellow-500/10 text-yellow-500"
                }`}
              >
                {connection.status}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function TipsPanel({ tips, isDark }: { tips: UsageTipRecord[]; isDark: boolean }) {
  if (tips.length === 0) return null;
  return (
    <section
      className={`rounded-2xl border p-6 shadow-sm ${
        isDark ? "border-emerald-500/30 bg-emerald-950/30" : "border-emerald-200 bg-emerald-50/60"
      }`}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className={`text-sm font-semibold uppercase tracking-wide ${isDark ? "text-emerald-200" : "text-emerald-600"}`}>
            Actionable tips
          </p>
          <h2 className={`text-xl font-semibold ${isDark ? "text-emerald-100" : "text-emerald-900"}`}>
            What surfaced this
          </h2>
        </div>
        <p className={`text-sm ${isDark ? "text-emerald-100/80" : "text-emerald-700"}`}>
          Suggestions refresh with every usage poll and budget update.
        </p>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {tips.map((tip) => (
          <article
            key={`${tip.title}-${tip.reason}`}
            className={`rounded-xl border p-4 ${
              isDark ? "border-emerald-500/20 bg-slate-900/70" : "border-emerald-200 bg-white/90"
            }`}
          >
            <p className={`text-sm font-semibold ${isDark ? "text-emerald-200" : "text-emerald-800"}`}>{tip.title}</p>
            <p className={`mt-1 text-sm ${isDark ? "text-emerald-100" : "text-emerald-700"}`}>{tip.body}</p>
            <p className={`mt-2 text-xs ${isDark ? "text-emerald-200/80" : "text-emerald-600"}`}>Why: {tip.reason}</p>
            <a
              className={`mt-3 inline-flex items-center text-xs font-semibold underline ${
                isDark ? "text-emerald-200" : "text-emerald-800"
              }`}
              href={tip.link}
              target="_blank"
              rel="noreferrer"
            >
              Learn more
            </a>
          </article>
        ))}
      </div>
    </section>
  );
}

function UniversalConnectorLab({ onAddConnection }: { onAddConnection: (connection: ConnectionRecord) => void }) {
  const [manifest, setManifest] = useState<ConnectorManifest>(DEFAULT_MANIFEST);
  const [manifestMode, setManifestMode] = useState<ManifestMode>("json");
  const [samplePayload, setSamplePayload] = useState<string>(DEFAULT_SAMPLE_PAYLOAD);
  const [dryRunStats, setDryRunStats] = useState<DryRunStats | null>(null);
  const [dryRunError, setDryRunError] = useState<string | null>(null);
  const [metadataKey, setMetadataKey] = useState("");
  const [metadataPath, setMetadataPath] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [providerAdded, setProviderAdded] = useState(false);

  const manifestText = manifestMode === "json" ? JSON.stringify(manifest, null, 2) : objectToYaml(manifest);
  const manifestCurrency = manifest.pricing.currency.toUpperCase();

  const handleDryRun = () => {
    setIsRunning(true);
    setDryRunError(null);
    try {
      const records = extractRecords(samplePayload, manifest.mapping.recordsPath);
      if (records.length === 0) {
        throw new Error("No events found at the records path.");
      }
      const normalized = records.map((record: Record<string, unknown>, index: number) => {
        const id = extractValueFromPath(record, manifest.mapping.idPath) ?? `row-${index + 1}`;
        const timestamp = String(
          extractValueFromPath(record, manifest.mapping.timestampPath) ?? new Date().toISOString(),
        );
        const rawUnits = extractValueFromPath(record, manifest.mapping.usagePath);
        const units = Number(rawUnits ?? 0);
        const metadataEntries = Object.entries(manifest.mapping.metadataPaths).map(([key, path]) => [
          key,
          extractValueFromPath(record, path) ?? null,
        ]);
        const metadata = Object.fromEntries(metadataEntries);
        const cost = calculateCost(units, manifest.pricing);
        return { id: String(id), timestamp, units, cost, metadata };
      });
      const totalUnits = normalized.reduce((acc, row) => acc + row.units, 0);
      const dailyCost = normalized.reduce((acc, row) => acc + row.cost, 0);
      const monthlyCost = dailyCost * 30;
      const previewRows = normalized.slice(0, 5);
      setDryRunStats({
        rows: previewRows,
        totalUnits,
        dailyCost,
        monthlyCost,
        currency: manifestCurrency,
        sampleCount: normalized.length,
      });
      setProviderAdded(false);
    } catch (error) {
      setDryRunError(error instanceof Error ? error.message : "Dry-run failed. Check manifest and payload.");
      setDryRunStats(null);
    } finally {
      setIsRunning(false);
    }
  };

  const handleAddMetadata = () => {
    if (!metadataKey.trim() || !metadataPath.trim()) return;
    setManifest((prev) => ({
      ...prev,
      mapping: {
        ...prev.mapping,
        metadataPaths: {
          ...prev.mapping.metadataPaths,
          [metadataKey.trim()]: metadataPath.trim(),
        },
      },
    }));
    setMetadataKey("");
    setMetadataPath("");
  };

  const handleRemoveMetadata = (key: string) => {
    setManifest((prev) => {
      const next = { ...prev.mapping.metadataPaths };
      delete next[key];
      return {
        ...prev,
        mapping: {
          ...prev.mapping,
          metadataPaths: next,
        },
      };
    });
  };

  const handlePricingTemplateChange = (template: "flat" | "tiered") => {
    setManifest((prev) => ({
      ...prev,
      pricing: {
        ...prev.pricing,
        template,
      },
    }));
  };

  const handleUpdateTier = (index: number, field: keyof PricingTier, value: string) => {
    setManifest((prev) => {
      const tiers = [...(prev.pricing.tiers ?? [])];
      if (!tiers[index]) {
        return prev;
      }
      if (field === "upto") {
        const numeric = value === "" ? null : Number(value);
        tiers[index] = {
          ...tiers[index],
          upto: numeric === null || Number.isNaN(numeric) ? null : numeric,
        };
      } else {
        const rateValue = Number(value);
        tiers[index] = {
          ...tiers[index],
          rate: Number.isNaN(rateValue) ? tiers[index].rate : rateValue,
        };
      }
      return {
        ...prev,
        pricing: {
          ...prev.pricing,
          tiers,
        },
      };
    });
  };

  const handleAddProvider = () => {
    const maskedKey = `${manifest.auth.headerName}: ${manifest.auth.prefix || ""}***`;
    onAddConnection({
      id: `connector-${manifest.slug}-${Date.now()}`,
      provider: manifest.slug,
      environment: manifest.environment,
      status: "active",
      masked_key: maskedKey,
      display_name: `${manifest.name} . ${manifest.environment}`,
      created_at: new Date().toISOString(),
    });
    setProviderAdded(true);
  };

  return (
    <section className="mt-8 rounded-3xl border border-white/10 bg-white/5 p-8 text-white">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-emerald-300">Universal Connector v1.1</p>
          <h2 className="text-3xl font-semibold">Declarative manifest + pricing templates + dry-run preview.</h2>
          <p className="text-white/70">
            Add any API beyond OpenAI/Twilio/SendGrid. Describe auth, endpoint, pagination, JSONPath mappings, and pricing.
            Dry-run shows normalized rows plus a monthly cost estimate—no backend help required.
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-2 text-sm text-white/80">
          Accept criteria: Add provider, run dry-run, see normalized rows + monthly estimate.
        </div>
      </div>

      <div className="mt-8 grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          <section className="rounded-2xl border border-white/10 p-6">
            <h3 className="text-lg font-semibold">Provider + auth</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="text-sm text-white/70">
                Display name
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.name}
                  onChange={(event) => setManifest((prev) => ({ ...prev, name: event.target.value }))}
                />
              </label>
              <label className="text-sm text-white/70">
                Slug
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.slug}
                  onChange={(event) => setManifest((prev) => ({ ...prev, slug: event.target.value }))}
                />
              </label>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <label className="text-sm text-white/70">
                Environment
                <select
                  className="mt-1 w-full rounded-xl border border-white/20 bg-slate-950 px-3 py-2"
                  value={manifest.environment}
                  onChange={(event) => setManifest((prev) => ({ ...prev, environment: event.target.value }))}
                >
                  <option value="prod">prod</option>
                  <option value="staging">staging</option>
                  <option value="dev">dev</option>
                </select>
              </label>
              <label className="text-sm text-white/70">
                Auth header
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.auth.headerName}
                  onChange={(event) =>
                    setManifest((prev) => ({ ...prev, auth: { ...prev.auth, headerName: event.target.value } }))
                  }
                />
              </label>
              <label className="text-sm text-white/70">
                Prefix
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.auth.prefix}
                  onChange={(event) =>
                    setManifest((prev) => ({ ...prev, auth: { ...prev.auth, prefix: event.target.value } }))
                  }
                />
              </label>
            </div>
          </section>

          <section className="rounded-2xl border border-white/10 p-6">
            <h3 className="text-lg font-semibold">Endpoint + pagination</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="text-sm text-white/70 md:col-span-2">
                Endpoint URL
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.endpoint.url}
                  onChange={(event) =>
                    setManifest((prev) => ({ ...prev, endpoint: { ...prev.endpoint, url: event.target.value } }))
                  }
                />
              </label>
              <label className="text-sm text-white/70">
                Method
                <select
                  className="mt-1 w-full rounded-xl border border-white/20 bg-slate-950 px-3 py-2"
                  value={manifest.endpoint.method}
                  onChange={(event) =>
                    setManifest((prev) => ({
                      ...prev,
                      endpoint: { ...prev.endpoint, method: event.target.value as "GET" | "POST" },
                    }))
                  }
                >
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                </select>
              </label>
              <label className="text-sm text-white/70">
                Pagination
                <select
                  className="mt-1 w-full rounded-xl border border-white/20 bg-slate-950 px-3 py-2"
                  value={manifest.endpoint.pagination.strategy}
                  onChange={(event) =>
                    setManifest((prev) => ({
                      ...prev,
                      endpoint: {
                        ...prev.endpoint,
                        pagination: { ...prev.endpoint.pagination, strategy: event.target.value as ConnectorManifest["endpoint"]["pagination"]["strategy"] },
                      },
                    }))
                  }
                >
                  <option value="cursor">cursor</option>
                  <option value="page">page</option>
                  <option value="offset">offset</option>
                  <option value="none">none</option>
                </select>
              </label>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <label className="text-sm text-white/70">
                Cursor param
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.endpoint.pagination.cursorParam ?? ""}
                  onChange={(event) =>
                    setManifest((prev) => ({
                      ...prev,
                      endpoint: {
                        ...prev.endpoint,
                        pagination: { ...prev.endpoint.pagination, cursorParam: event.target.value },
                      },
                    }))
                  }
                />
              </label>
              <label className="text-sm text-white/70">
                Next cursor JSONPath
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.endpoint.pagination.nextCursorPath ?? ""}
                  onChange={(event) =>
                    setManifest((prev) => ({
                      ...prev,
                      endpoint: {
                        ...prev.endpoint,
                        pagination: { ...prev.endpoint.pagination, nextCursorPath: event.target.value },
                      },
                    }))
                  }
                />
              </label>
              <label className="text-sm text-white/70">
                Page size param
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.endpoint.pagination.pageSizeParam ?? ""}
                  onChange={(event) =>
                    setManifest((prev) => ({
                      ...prev,
                      endpoint: {
                        ...prev.endpoint,
                        pagination: { ...prev.endpoint.pagination, pageSizeParam: event.target.value },
                      },
                    }))
                  }
                />
              </label>
            </div>
          </section>

          <section className="rounded-2xl border border-white/10 p-6">
            <h3 className="text-lg font-semibold">JSONPath mapping</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="text-sm text-white/70">
                Records path
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.mapping.recordsPath}
                  onChange={(event) =>
                    setManifest((prev) => ({ ...prev, mapping: { ...prev.mapping, recordsPath: event.target.value } }))
                  }
                />
              </label>
              <label className="text-sm text-white/70">
                ID path
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.mapping.idPath}
                  onChange={(event) =>
                    setManifest((prev) => ({ ...prev, mapping: { ...prev.mapping, idPath: event.target.value } }))
                  }
                />
              </label>
              <label className="text-sm text-white/70">
                Usage path
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.mapping.usagePath}
                  onChange={(event) =>
                    setManifest((prev) => ({ ...prev, mapping: { ...prev.mapping, usagePath: event.target.value } }))
                  }
                />
              </label>
              <label className="text-sm text-white/70">
                Timestamp path
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.mapping.timestampPath}
                  onChange={(event) =>
                    setManifest((prev) => ({ ...prev, mapping: { ...prev.mapping, timestampPath: event.target.value } }))
                  }
                />
              </label>
            </div>
            <div className="mt-4">
              <p className="text-sm font-semibold text-white/80">Metadata fields</p>
              <div className="mt-2 space-y-2">
                {Object.entries(manifest.mapping.metadataPaths).map(([key, path]) => (
                  <div key={key} className="flex items-center gap-2 text-sm">
                    <span className="min-w-[100px] rounded-full bg-white/10 px-3 py-1 font-semibold capitalize">{key}</span>
                    <input
                      className="flex-1 rounded-xl border border-white/20 bg-transparent px-3 py-2"
                      value={path}
                      onChange={(event) =>
                        setManifest((prev) => ({
                          ...prev,
                          mapping: {
                            ...prev.mapping,
                            metadataPaths: {
                              ...prev.mapping.metadataPaths,
                              [key]: event.target.value,
                            },
                          },
                        }))
                      }
                    />
                    <button
                      type="button"
                      className="rounded-full border border-white/20 px-3 py-1 text-xs text-white/80"
                      onClick={() => handleRemoveMetadata(key)}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <input
                  className="flex-1 rounded-xl border border-white/20 bg-transparent px-3 py-2 text-sm"
                  placeholder="metadata key"
                  value={metadataKey}
                  onChange={(event) => setMetadataKey(event.target.value)}
                />
                <input
                  className="flex-1 rounded-xl border border-white/20 bg-transparent px-3 py-2 text-sm"
                  placeholder="JSONPath"
                  value={metadataPath}
                  onChange={(event) => setMetadataPath(event.target.value)}
                />
                <button
                  type="button"
                  className="rounded-full border border-white/20 px-4 py-2 text-sm"
                  onClick={handleAddMetadata}
                >
                  Add
                </button>
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-white/10 p-6">
            <h3 className="text-lg font-semibold">Pricing templates</h3>
            <div className="mt-4 flex flex-wrap gap-4 text-sm">
              <label className="inline-flex items-center gap-2">
                <input
                  type="radio"
                  name="pricing-template"
                  value="flat"
                  checked={manifest.pricing.template === "flat"}
                  onChange={() => handlePricingTemplateChange("flat")}
                />
                Flat rate
              </label>
              <label className="inline-flex items-center gap-2">
                <input
                  type="radio"
                  name="pricing-template"
                  value="tiered"
                  checked={manifest.pricing.template === "tiered"}
                  onChange={() => handlePricingTemplateChange("tiered")}
                />
                Tiered
              </label>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <label className="text-sm text-white/70">
                Currency
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2 uppercase"
                  value={manifest.pricing.currency}
                  onChange={(event) =>
                    setManifest((prev) => ({ ...prev, pricing: { ...prev.pricing, currency: event.target.value } }))
                  }
                />
              </label>
              <label className="text-sm text-white/70">
                Unit name
                <input
                  className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                  value={manifest.pricing.unitName}
                  onChange={(event) =>
                    setManifest((prev) => ({ ...prev, pricing: { ...prev.pricing, unitName: event.target.value } }))
                  }
                />
              </label>
              {manifest.pricing.template === "flat" && (
                <label className="text-sm text-white/70">
                  Flat rate
                  <input
                    type="number"
                    step="0.0001"
                    className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                    value={manifest.pricing.flatRate ?? 0}
                    onChange={(event) =>
                      setManifest((prev) => ({
                        ...prev,
                        pricing: { ...prev.pricing, flatRate: Number(event.target.value) },
                      }))
                    }
                  />
                </label>
              )}
            </div>
            {manifest.pricing.template === "tiered" && (
              <div className="mt-4 space-y-3">
                {(manifest.pricing.tiers ?? []).map((tier, index) => (
                  <div key={`${tier.upto ?? "infinite"}-${index}`} className="grid gap-3 md:grid-cols-2">
                    <label className="text-sm text-white/70">
                      Upto units (blank = unlimited)
                      <input
                        className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                        value={tier.upto ?? ""}
                        onChange={(event) => handleUpdateTier(index, "upto", event.target.value)}
                      />
                    </label>
                    <label className="text-sm text-white/70">
                      Rate
                      <input
                        type="number"
                        step="0.0001"
                        className="mt-1 w-full rounded-xl border border-white/20 bg-transparent px-3 py-2"
                        value={tier.rate}
                        onChange={(event) => handleUpdateTier(index, "rate", event.target.value)}
                      />
                    </label>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <div className="space-y-6">
          <section className="rounded-2xl border border-white/10 p-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Manifest ({manifestMode.toUpperCase()})</h3>
              <div className="rounded-full border border-white/10 bg-white/10 p-1 text-xs">
                <button
                  type="button"
                  className={`rounded-full px-3 py-1 font-semibold ${manifestMode === "json" ? "bg-white text-slate-900" : "text-white/80"}`}
                  onClick={() => setManifestMode("json")}
                >
                  JSON
                </button>
                <button
                  type="button"
                  className={`rounded-full px-3 py-1 font-semibold ${manifestMode === "yaml" ? "bg-white text-slate-900" : "text-white/80"}`}
                  onClick={() => setManifestMode("yaml")}
                >
                  YAML
                </button>
              </div>
            </div>
            <p className="mt-2 text-xs text-white/60">
              Use the structured editor to change fields; copy the schema here when needed.
            </p>
            <textarea
              className="mt-4 h-64 w-full rounded-2xl border border-white/20 bg-slate-950 p-3 font-mono text-xs text-emerald-200"
              value={manifestText}
              readOnly
            />
          </section>

          <section className="rounded-2xl border border-white/10 p-6">
            <h3 className="text-lg font-semibold">Sample payload (JSON)</h3>
            <textarea
              className="mt-3 h-56 w-full rounded-2xl border border-white/20 bg-slate-950 p-3 font-mono text-xs text-emerald-200"
              value={samplePayload}
              onChange={(event) => setSamplePayload(event.target.value)}
            />
            <button
              type="button"
              className="mt-4 w-full rounded-full bg-emerald-400/90 px-4 py-3 text-base font-semibold text-slate-950"
              onClick={handleDryRun}
              disabled={isRunning}
            >
              {isRunning ? "Running dry-run..." : "Dry-run connector"}
            </button>
            {dryRunError && <p className="mt-2 text-sm text-rose-300">{dryRunError}</p>}
          </section>

          {dryRunStats && (
            <section className="rounded-2xl border border-emerald-400/40 bg-emerald-500/10 p-6 text-sm text-emerald-50">
              <h3 className="text-lg font-semibold text-white">Dry-run preview</h3>
              <p className="mt-2 text-emerald-100">
                {dryRunStats.sampleCount} rows normalized · {manifest.pricing.unitName} | {manifestCurrency}
              </p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div>
                  <p className="text-xs uppercase tracking-wide text-emerald-200">Total units in payload</p>
                  <p className="text-2xl font-semibold text-white">{formatNumber(dryRunStats.totalUnits)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-emerald-200">Monthly estimate</p>
                  <p className="text-2xl font-semibold text-white">
                    {formatCurrency(dryRunStats.monthlyCost, dryRunStats.currency)}
                  </p>
                  <p className="text-xs text-emerald-100">~₹{(dryRunStats.monthlyCost * 83).toFixed(0)}</p>
                </div>
              </div>
              <div className="mt-4 overflow-auto rounded-2xl border border-white/20 bg-slate-950">
                <table className="min-w-full text-left text-xs">
                  <thead className="bg-white/10 text-emerald-200">
                    <tr>
                      <th className="px-3 py-2">ID</th>
                      <th className="px-3 py-2">Timestamp</th>
                      <th className="px-3 py-2">Units</th>
                      <th className="px-3 py-2">Cost ({manifestCurrency})</th>
                      <th className="px-3 py-2">Metadata</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dryRunStats.rows.map((row) => (
                      <tr key={row.id} className="border-t border-white/10">
                        <td className="px-3 py-2 font-mono">{row.id}</td>
                        <td className="px-3 py-2">{row.timestamp}</td>
                        <td className="px-3 py-2">{formatNumber(row.units, 3)}</td>
                        <td className="px-3 py-2">{formatNumber(row.cost, 4)}</td>
                        <td className="px-3 py-2">
                          {Object.entries(row.metadata)
                            .map(([key, value]) => `${key}: ${value ?? "-"}`)
                            .join(", ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  className="flex-1 rounded-full bg-white px-4 py-2 text-base font-semibold text-slate-900"
                  onClick={handleAddProvider}
                >
                  {providerAdded ? "Provider added to demo" : "Add provider to demo"}
                </button>
                <button
                  type="button"
                  className="flex-1 rounded-full border border-white/40 px-4 py-2 text-base font-semibold text-white"
                  onClick={() => setProviderAdded(false)}
                >
                  Reset
                </button>
              </div>
            </section>
          )}
        </div>
      </div>
    </section>
  );
}

export default function DashboardPage() {
  const [theme, setTheme] = useState<ThemeMode>("dark");
  const [activeView, setActiveView] = useState<ViewKey>("overview");
  const [connections, setConnections] = useState<ConnectionRecord[]>(SAMPLE_CONNECTIONS);
  const isDark = theme === "dark";

  const aggregated = useMemo(() => {
    const totals = SAMPLE_USAGE_PROJECTIONS.reduce(
      (acc, entry) => {
        acc.month_to_date += entry.month_to_date_spend;
        acc.projected += entry.projected_total;
        return acc;
      },
      { month_to_date: 0, projected: 0 },
    );
    const coverage = Math.round((totals.month_to_date / (totals.projected || 1)) * 100);
    return {
      ...totals,
      coverage,
      label: formatCurrency(totals.projected, "usd"),
    };
  }, []);

  const primarySeries = useMemo(() => buildUsageSeriesFromProjection(SAMPLE_USAGE_PROJECTIONS[0]), []);

  const pageClasses = isDark ? "bg-slate-950 text-white" : "bg-slate-50 text-slate-900";

  return (
    <main className={`${pageClasses} min-h-screen`}>
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-wide text-emerald-400">Simulated dashboard</p>
            <h1 className="text-3xl font-semibold">APICompass sample admin</h1>
            <p className="text-sm text-white/70">
              Use this page to preview the dashboard experience with sample data. Switch the theme and explore each view below.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setTheme(isDark ? "light" : "dark")}
            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold ${
              isDark ? "border-slate-700 bg-slate-900 text-slate-100" : "border-zinc-200 bg-white text-zinc-700"
            }`}
          >
            Theme: {isDark ? "Dark" : "Light"}
          </button>
        </header>

        <nav
          aria-label="Dashboard views"
          className={`mt-8 rounded-2xl border p-2 shadow-sm ${
            isDark ? "border-slate-700 bg-slate-900/80" : "border-zinc-200 bg-white"
          }`}
        >
          <div
            className={`grid grid-cols-2 gap-2 text-sm font-semibold sm:grid-cols-4 ${
              isDark ? "text-slate-300" : "text-zinc-600"
            }`}
          >
            {VIEW_OPTIONS.map((option) => {
              const isActive = option.id === activeView;
              return (
                <button
                  key={option.id}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`rounded-xl border px-3 py-2 text-left transition ${
                    isActive
                      ? isDark
                        ? "border-emerald-400/60 bg-emerald-400/10 text-emerald-100"
                        : "border-zinc-900 bg-zinc-900 text-white"
                      : isDark
                        ? "border-slate-800 bg-slate-800 hover:border-slate-700"
                        : "border-transparent bg-zinc-50 hover:border-zinc-200"
                  }`}
                  onClick={() => setActiveView(option.id)}
                >
                  <span className="block text-base">{option.label}</span>
                  <span
                    className={`text-xs font-normal opacity-80 ${
                      isDark ? "text-slate-400" : "text-zinc-500"
                    }`}
                  >
                    {option.description}
                  </span>
                </button>
              );
            })}
          </div>
        </nav>

        <section className="mt-8 grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <UsageForecastCard series={primarySeries} summary={SAMPLE_USAGE_PROJECTIONS[0]} isDark={isDark} />
            <ProviderBreakdown usage={SAMPLE_USAGE_PROJECTIONS} isDark={isDark} />
          </div>
          <div className="space-y-6">
            <section
              className={`rounded-2xl border p-6 shadow-sm ${
                isDark ? "border-emerald-500/30 bg-slate-900" : "border-emerald-200 bg-white"
              }`}
            >
              <p className={`text-sm font-semibold uppercase tracking-wide ${isDark ? "text-emerald-200" : "text-emerald-600"}`}>
                Budget bar
              </p>
              <h3 className="text-3xl font-bold">{aggregated.label}</h3>
              <p className={isDark ? "text-slate-300" : "text-zinc-600"}>Across OpenAI, Twilio, SendGrid</p>
              <div className={`mt-4 h-3 rounded-full ${isDark ? "bg-slate-800" : "bg-zinc-100"}`}>
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-blue-400 to-cyan-400"
                  style={{ width: `${Math.min(aggregated.coverage, 100)}%` }}
                />
              </div>
              <p className="mt-2 text-sm">
                Month to date {formatCurrency(aggregated.month_to_date, "usd")} (coverage {aggregated.coverage}%).
              </p>
            </section>
            <AlertsPanel alerts={SAMPLE_ALERTS} isDark={isDark} />
          </div>
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-2">
          <ConnectionsPanel connections={connections} isDark={isDark} />
          <TipsPanel tips={SAMPLE_TIPS} isDark={isDark} />
        </section>

        <UniversalConnectorLab
          onAddConnection={(connection) =>
            setConnections((prev) => [connection, ...prev.filter((item) => item.id !== connection.id)])
          }
        />

        <section className="mt-8 rounded-2xl border border-dashed border-white/10 p-6 text-sm text-white/70">
          <p className="text-base font-semibold text-white">Need real data?</p>
          <p>
            Connect a provider inside the product and this dashboard will swap from simulated data to your connected accounts instantly.
          </p>
        </section>
      </div>
    </main>
  );
}
