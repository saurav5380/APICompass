'use client';

import { useMemo, useState } from "react";

import { Select, SelectOption } from "@/components/ui/select";
import { DateRangePicker, type DateRange } from "@/components/ui/date-range-picker";
import { useMetricsOverview, useMetricsTrends } from "@/hooks/useMetrics";
import MetricsCharts from "./MetricsCharts";

const PROVIDER_OPTIONS = [
  { label: "All providers", value: "all" },
  { label: "OpenAI", value: "openai" },
  { label: "Twilio", value: "twilio" },
  { label: "SendGrid", value: "sendgrid" },
  { label: "Stripe", value: "stripe" },
];

const SERVICE_OPTIONS = [
  { label: "All services", value: "all" },
  { label: "Completions", value: "completions" },
  { label: "SMS", value: "sms" },
  { label: "Email", value: "email" },
  { label: "Billing", value: "billing" },
];

export default function DashboardClient() {
  const [provider, setProvider] = useState("all");
  const [service, setService] = useState("all");
  const [range, setRange] = useState<DateRange>({ from: "2024-06-01", to: "2024-06-07" });

  const filters = useMemo(
    () => ({
      provider,
      service,
      start: range.from,
      end: range.to,
    }),
    [provider, range.from, range.to, service],
  );

  const overviewQuery = useMetricsOverview(filters);
  const trendsQuery = useMetricsTrends(filters);

  return (
    <div className="space-y-8 px-4 pb-10 pt-6 md:px-8">
      <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-6 text-white shadow-xl">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-emerald-300">Filters</p>
            <h1 className="text-2xl font-semibold">Usage pulse</h1>
            <p className="text-sm text-white/70">
              Slice your API traffic by provider, service, and a time window. Charts update instantly as you refine the
              scope.
            </p>
          </div>
        </div>
        <div className="mt-6 grid gap-4 lg:grid-cols-4">
          <div className="flex flex-col gap-2">
            <p className="text-xs uppercase tracking-wide text-white/50">Provider</p>
            <Select value={provider} onValueChange={setProvider}>
              {PROVIDER_OPTIONS.map((option) => (
                <SelectOption key={option.value} value={option.value}>
                  {option.label}
                </SelectOption>
              ))}
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <p className="text-xs uppercase tracking-wide text-white/50">Service</p>
            <Select value={service} onValueChange={setService}>
              {SERVICE_OPTIONS.map((option) => (
                <SelectOption key={option.value} value={option.value}>
                  {option.label}
                </SelectOption>
              ))}
            </Select>
          </div>
          <div className="lg:col-span-2">
            <DateRangePicker value={range} onChange={setRange} />
          </div>
        </div>
      </section>

      <section className="grid gap-4 text-white sm:grid-cols-2 xl:grid-cols-3">
        {overviewQuery.isLoading ? (
          <p className="text-sm text-white/70">Loading overview…</p>
        ) : overviewQuery.isError ? (
          <p className="text-sm text-rose-300">
            Unable to load overview: {(overviewQuery.error as Error).message}
          </p>
        ) : (
          <>
            <article className="rounded-3xl border border-white/10 bg-gradient-to-br from-emerald-500/15 to-slate-900/70 p-6">
              <p className="text-xs uppercase tracking-wide text-white/60">Total calls</p>
              <div className="mt-3 flex items-end justify-between">
                <h3 className="text-3xl font-semibold">
                  {overviewQuery.data?.total_calls.toLocaleString() ?? "—"}
                </h3>
              </div>
              <p className="mt-2 text-sm text-white/70">Across all providers during the selected window.</p>
            </article>
            <article className="rounded-3xl border border-white/10 bg-gradient-to-br from-rose-500/15 to-slate-900/70 p-6">
              <p className="text-xs uppercase tracking-wide text-white/60">Error volume</p>
              <div className="mt-3 flex items-end justify-between">
                <h3 className="text-3xl font-semibold">
                  {overviewQuery.data?.total_errors.toLocaleString() ?? "—"}
                </h3>
              </div>
              <p className="mt-2 text-sm text-white/70">Client + provider errors bubbled up from the ingest pipeline.</p>
            </article>
            <article className="rounded-3xl border border-white/10 bg-gradient-to-br from-blue-500/15 to-slate-900/70 p-6">
              <p className="text-xs uppercase tracking-wide text-white/60">Cost trend</p>
              <div className="mt-3 flex items-end justify-between">
                <h3 className="text-3xl font-semibold">
                  $
                  {(Number(overviewQuery.data?.total_spend ?? 0) / 1000).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                  })}
                  k
                </h3>
              </div>
              <p className="mt-2 text-sm text-white/70">Rolling cost estimate based on normalized usage.</p>
            </article>
          </>
        )}
      </section>

      <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 text-white">
        <div className="mb-6 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-white/50">Cost trends</p>
            <h2 className="text-xl font-semibold">Time series</h2>
          </div>
          <p className="text-sm text-white/60">
            Showing <span className="font-semibold text-white">{range.from}</span> →{" "}
            <span className="font-semibold text-white">{range.to}</span>
          </p>
        </div>
        <MetricsCharts
          data={trendsQuery.data}
          loading={trendsQuery.isLoading}
          error={trendsQuery.isError ? (trendsQuery.error as Error) : null}
        />
      </section>
    </div>
  );
}
