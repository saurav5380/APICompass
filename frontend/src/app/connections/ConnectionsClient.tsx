'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type ProviderId = "openai" | "twilio" | "sendgrid" | "stripe" | "generic";
type EnvironmentId = "prod" | "staging" | "dev";

interface ProviderOption {
  id: ProviderId;
  label: string;
  description: string;
  docs: string;
  defaultScopes: string[];
}

interface ApiConnection {
  id: string;
  provider: string;
  environment: string;
  status: string;
  display_name: string | null;
  masked_key: string;
  scopes?: string[];
  created_at: string;
  last_synced_at: string | null;
  local_connector_enabled: boolean;
  local_agent_last_seen_at: string | null;
  local_agent_token?: string | null;
}

interface ConnectionRecord {
  id: string;
  provider: string;
  environment: string;
  status: string;
  displayName: string | null;
  maskedKey: string;
  scopes: string[];
  createdAt: string;
  lastSyncedAt: string | null;
  localConnectorEnabled: boolean;
  localAgentLastSeenAt: string | null;
}

interface ConnectionsClientProps {
  orgId: string;
  orgName: string;
  userName: string;
  userEmail: string;
}

interface FormState {
  provider: ProviderId;
  environment: EnvironmentId;
  displayName: string;
  apiKey: string;
  scopes: string;
  localConnectorEnabled: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const PROVIDER_OPTIONS: ProviderOption[] = [
  {
    id: "openai",
    label: "OpenAI",
    description: "Models, moderation, embeddings, assistants",
    docs: "https://platform.openai.com/account/api-keys",
    defaultScopes: ["completions:read"],
  },
  {
    id: "twilio",
    label: "Twilio",
    description: "Programmable SMS, voice, WhatsApp, Verify",
    docs: "https://www.twilio.com/docs/glossary/what-is-an-api-key",
    defaultScopes: ["messages:read"],
  },
  {
    id: "sendgrid",
    label: "SendGrid",
    description: "Transactional email + marketing campaigns",
    docs: "https://docs.sendgrid.com/ui/account-and-settings/api-keys",
    defaultScopes: ["mail.send", "marketing.contacts.read"],
  },
  {
    id: "stripe",
    label: "Stripe",
    description: "Billing + cost coverage (beta)",
    docs: "https://stripe.com/docs/keys",
    defaultScopes: ["balance.read"],
  },
  {
    id: "generic",
    label: "Generic HTTP",
    description: "Bring any REST provider via local connector",
    docs: "https://docs.apicompass.dev/connectors",
    defaultScopes: ["usage.read"],
  },
];

const ENVIRONMENT_OPTIONS: Array<{ id: EnvironmentId; label: string }> = [
  { id: "prod", label: "Production" },
  { id: "staging", label: "Staging" },
  { id: "dev", label: "Development" },
];

const STATUS_STYLES: Record<string, string> = {
  active: "border-emerald-400/40 bg-emerald-500/10 text-emerald-100",
  pending: "border-amber-400/40 bg-amber-500/10 text-amber-100",
  error: "border-red-500/40 bg-red-500/10 text-red-100",
  disabled: "border-slate-500/40 bg-slate-500/10 text-slate-200",
};

const formatDateTime = (value: string | null) => {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
};

const normalizeConnection = (entry: ApiConnection): ConnectionRecord => ({
  id: entry.id,
  provider: entry.provider,
  environment: entry.environment,
  status: entry.status,
  displayName: entry.display_name ?? null,
  maskedKey: entry.masked_key,
  scopes: Array.isArray(entry.scopes) ? entry.scopes : [],
  createdAt: entry.created_at,
  lastSyncedAt: entry.last_synced_at,
  localConnectorEnabled: Boolean(entry.local_connector_enabled),
  localAgentLastSeenAt: entry.local_agent_last_seen_at,
});

const defaultProvider = PROVIDER_OPTIONS[0];

const buildInitialFormState = (): FormState => {
  const fallbackScopes = defaultProvider?.defaultScopes.join(", ") ?? "";
  return {
    provider: defaultProvider?.id ?? "openai",
    environment: "prod",
    displayName: "",
    apiKey: "",
    scopes: fallbackScopes,
    localConnectorEnabled: false,
  };
};

export default function ConnectionsClient({ orgId, orgName, userEmail, userName }: ConnectionsClientProps) {
  const [connections, setConnections] = useState<ConnectionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(() => buildInitialFormState());
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [issuedToken, setIssuedToken] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const providerMap = useMemo<Record<string, ProviderOption>>(() => {
    return Object.fromEntries(PROVIDER_OPTIONS.map((provider) => [provider.id, provider]));
  }, []);

  const loadConnections = useCallback(async () => {
    setLoading(true);
    setPageError(null);
    try {
      const response = await fetch(`${API_BASE}/connections`, {
        headers: {
          "X-Org-Id": orgId,
        },
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload: ApiConnection[] = await response.json();
      const normalized = payload.map(normalizeConnection).sort((a, b) => {
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      });
      setConnections(normalized);
    } catch (error) {
      console.error("[connections] load failed", error);
      setPageError("Unable to load connections. Confirm your org access or entitlements.");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    void loadConnections();
  }, [loadConnections]);

  const handleProviderChange = (providerId: ProviderId) => {
    const provider = PROVIDER_OPTIONS.find((option) => option.id === providerId);
    setForm((prev) => ({
      ...prev,
      provider: providerId,
      scopes: provider ? provider.defaultScopes.join(", ") : prev.scopes,
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    setBusy(true);
    setStatusMessage(null);
    setIssuedToken(null);

    if (!form.localConnectorEnabled && !form.apiKey.trim()) {
      setFormError("Provide an API key or enable Local Connector mode.");
      setBusy(false);
      return;
    }

    const scopes = form.scopes
      .split(",")
      .map((scope) => scope.trim())
      .filter(Boolean);

    const payload = {
      provider: form.provider,
      environment: form.environment,
      display_name: form.displayName || null,
      api_key: form.localConnectorEnabled ? null : form.apiKey.trim(),
      scopes,
      local_connector_enabled: form.localConnectorEnabled,
    };

    try {
      const response = await fetch(`${API_BASE}/connections`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Org-Id": orgId,
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const created: ApiConnection = await response.json();
      setConnections((prev) => {
        const normalized = normalizeConnection(created);
        return [normalized, ...prev.filter((item) => item.id !== normalized.id)];
      });
      setStatusMessage("Provider connected successfully.");
      setIssuedToken(created.local_agent_token ?? null);
      const defaults = PROVIDER_OPTIONS.find((option) => option.id === form.provider) ?? defaultProvider;
      setForm({
        provider: defaults.id,
        environment: form.environment,
        displayName: "",
        apiKey: "",
        scopes: defaults.defaultScopes.join(", "),
        localConnectorEnabled: false,
      });
    } catch (error) {
      console.error("[connections] create failed", error);
      setFormError("Unable to save connection. Review the payload and try again.");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (connectionId: string) => {
    const connection = connections.find((item) => item.id === connectionId);
    const label = connection?.displayName ?? connection?.provider ?? "provider";
    const confirmed = window.confirm(`Remove ${label}? Ingest jobs will stop immediately.`);
    if (!confirmed) {
      return;
    }
    setDeletingId(connectionId);
    setPageError(null);
    try {
      const response = await fetch(`${API_BASE}/connections/${connectionId}`, {
        method: "DELETE",
        headers: {
          "X-Org-Id": orgId,
        },
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setConnections((prev) => prev.filter((item) => item.id !== connectionId));
    } catch (error) {
      console.error("[connections] delete failed", error);
      setPageError("Unable to remove the connection. Try again in a moment.");
    } finally {
      setDeletingId(null);
    }
  };

  const providerDetail = providerMap[form.provider];

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-5xl space-y-8 px-6 py-12">
        <header className="rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950 p-8">
          <p className="text-sm uppercase tracking-wide text-white/70">Authenticated control center</p>
          <h1 className="mt-2 text-3xl font-semibold">API connections for {orgName}</h1>
          <p className="mt-3 text-white/80">
            Signed in as {userName} ({userEmail}). Every change is scoped to your org and audited in the background.
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-white/60">Org identifier</p>
              <p className="font-mono text-base text-white">{orgId}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-white/60">Current connections</p>
              <p className="text-2xl font-semibold">{connections.length}</p>
            </div>
          </div>
        </header>

        {issuedToken && (
          <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 px-4 py-4 text-sm text-amber-100">
            Local Connector token (copy now, it will not be shown again):{" "}
            <span className="font-mono text-base">{issuedToken}</span>
          </div>
        )}

        {statusMessage && (
          <div className="rounded-2xl border border-emerald-400/40 bg-emerald-500/10 px-4 py-4 text-sm text-emerald-100">
            {statusMessage}
          </div>
        )}

        <section className="rounded-3xl border border-white/10 bg-slate-900/60 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-2xl font-semibold">Active API connections</h2>
              <p className="text-sm text-white/70">Every provider inherits org-wide guardrails and alerting.</p>
            </div>
            <button
              type="button"
              className="rounded-full border border-white/20 bg-white/5 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              onClick={() => void loadConnections()}
              disabled={loading}
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
          </div>
          {pageError && (
            <div className="mt-4 rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
              {pageError}
            </div>
          )}
          {loading ? (
            <p className="mt-8 text-sm text-white/70">Loading connections…</p>
          ) : connections.length === 0 ? (
            <p className="mt-8 text-sm text-white/70">
              No providers connected yet. Use the form below to register your first API key.
            </p>
          ) : (
            <ul className="mt-6 space-y-4">
              {connections.map((connection) => {
                const providerLabel = providerMap[connection.provider as ProviderId]?.label ?? connection.provider;
                const environment = ENVIRONMENT_OPTIONS.find((env) => env.id === connection.environment)?.label ?? connection.environment;
                const statusKey = connection.status.toLowerCase();
                const statusStyles = STATUS_STYLES[statusKey] ?? "border-white/20 bg-white/5 text-white/80";
                return (
                  <li key={connection.id} className="rounded-2xl border border-white/10 bg-black/20 p-5">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-lg font-semibold">
                          {connection.displayName || providerLabel} · {environment}
                        </p>
                        <p className="text-sm text-white/70">Masked key: {connection.maskedKey}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${statusStyles}`}>
                          {connection.status}
                        </span>
                        <button
                          type="button"
                          className="text-sm text-red-300 hover:text-red-100 disabled:opacity-50"
                          onClick={() => void handleDelete(connection.id)}
                          disabled={deletingId === connection.id}
                        >
                          {deletingId === connection.id ? "Removing…" : "Remove"}
                        </button>
                      </div>
                    </div>
                    <dl className="mt-4 grid gap-4 text-sm text-white/70 sm:grid-cols-2">
                      <div>
                        <dt className="text-xs uppercase tracking-wide">Created</dt>
                        <dd className="text-white">{formatDateTime(connection.createdAt)}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide">Last synced</dt>
                        <dd className="text-white">{formatDateTime(connection.lastSyncedAt)}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide">Scopes</dt>
                        <dd className="text-white">{connection.scopes.length ? connection.scopes.join(", ") : "—"}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide">Local connector</dt>
                        <dd className="text-white">
                          {connection.localConnectorEnabled
                            ? `Enabled${connection.localAgentLastSeenAt ? ` · agent ping ${formatDateTime(connection.localAgentLastSeenAt)}` : ""}`
                            : "Disabled"}
                        </dd>
                      </div>
                    </dl>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section className="rounded-3xl border border-white/10 bg-slate-900/80 p-6">
          <h2 className="text-2xl font-semibold">Connect a new provider</h2>
          <p className="mt-2 text-sm text-white/70">
            Paste a scoped API key or switch on Local Connector mode to keep secrets on your hardware. We redact keys immediately.
          </p>
          <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-sm text-white/80">
                Provider
                <select
                  className="mt-1 w-full rounded-2xl border border-white/20 bg-black/40 px-4 py-2 text-base"
                  value={form.provider}
                  onChange={(event) => handleProviderChange(event.target.value as ProviderId)}
                >
                  {PROVIDER_OPTIONS.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-white/80">
                Environment
                <select
                  className="mt-1 w-full rounded-2xl border border-white/20 bg-black/40 px-4 py-2 text-base"
                  value={form.environment}
                  onChange={(event) => setForm((prev) => ({ ...prev, environment: event.target.value as EnvironmentId }))}
                >
                  {ENVIRONMENT_OPTIONS.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {providerDetail && (
              <div className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white/80">
                <p className="font-medium">{providerDetail.label}</p>
                <p>{providerDetail.description}</p>
                <a className="mt-1 inline-flex text-xs font-semibold text-emerald-200 underline" href={providerDetail.docs} target="_blank" rel="noreferrer">
                  Provider docs
                </a>
              </div>
            )}
            <label className="text-sm text-white/80">
              Display name (optional)
              <input
                className="mt-1 w-full rounded-2xl border border-white/20 bg-black/40 px-4 py-2 text-base"
                value={form.displayName}
                onChange={(event) => setForm((prev) => ({ ...prev, displayName: event.target.value }))}
                placeholder="OpenAI · prod"
              />
            </label>
            <label className="text-sm text-white/80">
              API key
              <textarea
                className="mt-1 w-full rounded-2xl border border-white/20 bg-black/40 px-4 py-2 text-base"
                rows={3}
                value={form.apiKey}
                onChange={(event) => setForm((prev) => ({ ...prev, apiKey: event.target.value }))}
                placeholder="sk-live-..."
                disabled={form.localConnectorEnabled}
              />
            </label>
            <label className="text-sm text-white/80">
              Minimal scopes (comma separated)
              <input
                className="mt-1 w-full rounded-2xl border border-white/20 bg-black/40 px-4 py-2 text-base"
                value={form.scopes}
                onChange={(event) => setForm((prev) => ({ ...prev, scopes: event.target.value }))}
              />
            </label>
            <label className="flex items-center gap-3 text-sm text-white/80">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border border-white/30"
                checked={form.localConnectorEnabled}
                onChange={(event) => setForm((prev) => ({ ...prev, localConnectorEnabled: event.target.checked }))}
              />
              Enable Local Connector (API key stays on your device)
            </label>
            {formError && (
              <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{formError}</div>
            )}
            <button
              type="submit"
              className="w-full rounded-full bg-emerald-500 px-5 py-3 text-base font-semibold text-slate-900 transition hover:bg-emerald-400 disabled:opacity-60"
              disabled={busy}
            >
              {busy ? "Connecting…" : "Save connection"}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}
