'use client';

import { FormEvent, useEffect, useMemo, useState } from "react";

type RoleOption = "solo" | "team";
type LeadMagnetMode = "llm" | "twilio";

interface HeadlineVariant {
  id: string;
  title: string;
  explainer: string;
}

interface ValuePillar {
  id: string;
  title: string;
  body: string;
}

interface Step {
  id: string;
  title: string;
  body: string;
}

interface FeatureDetail {
  id: string;
  label: string;
  body: string;
  highlight: string;
}

interface TipCardContent {
  id: string;
  front: { title: string; subtitle: string };
  back: { insight: string; savings: string };
}

interface Testimonial {
  id: string;
  quote: string;
  author: string;
  role: string;
}

interface PricingTier {
  id: string;
  name: string;
  priceINR: string;
  priceUSD: string;
  bullets: string[];
  cta: string;
  highlight?: boolean;
}

interface Faq {
  id: string;
  question: string;
  answer: string;
}

const HEADLINE_VARIANTS: HeadlineVariant[] = [
  {
    id: "stop-surprise",
    title: "Stop surprise API bills.",
    explainer: "Know your API bill before it hits and ship with confidence.",
  },
  {
    id: "know-before",
    title: "Know your API bill before it hits.",
    explainer: "For indie devs and lean teams watching OpenAI, Twilio, SendGrid, Stripe & more.",
  },
  {
    id: "realtime-spend",
    title: "Real-time API spend for indie devs--OpenAI, Twilio, SendGrid & more.",
    explainer: "Connect in minutes, see forecasts instantly, and keep the budget bar in the green.",
  },
];

const VALUE_PILLARS: ValuePillar[] = [
  {
    id: "forecast",
    title: "Forecasts you can trust",
    body: "Simple, explainable projections with confidence bands--no black box math.",
  },
  {
    id: "alerts",
    title: "Alerts before it's expensive",
    body: "Email or Slack pings when you're on track to exceed a budget or cross a plan tier.",
  },
  {
    id: "savings",
    title: "Actionable savings",
    body: "Concrete tips--batching, caching, model swaps--based on your usage patterns.",
  },
];

const HOW_IT_WORKS: Step[] = [
  {
    id: "connect",
    title: "Connect providers",
    body: "Paste a key or run the Local Connector. Works with OpenAI, Twilio, SendGrid, Stripe--and any API via our Universal Connector.",
  },
  {
    id: "forecast",
    title: "See live forecast",
    body: "Budget bar + explainable confidence bands so you know the low, mid, and high ranges instantly.",
  },
  {
    id: "alerts",
    title: "Get alerts & tips",
    body: "Cross-provider policies trigger alerts, and savings tips refresh with every usage ingest.",
  },
];

const FEATURE_DETAILS: FeatureDetail[] = [
  {
    id: "connector",
    label: "Universal Connector",
    body: "Add any API via a declarative manifest. Map fields, set pricing rules, dry-run, and go.",
    highlight: "No vendor lock-in--bring your own data warehouse or connector.",
  },
  {
    id: "privacy",
    label: "Privacy modes",
    body: "Cloud: paste restricted keys and you're done. Local Connector: keep keys on your machine--signed aggregates hit /ingest so nothing sensitive lands on the server.",
    highlight: "Privacy-first mode keeps secrets local.",
  },
  {
    id: "budgets",
    label: "Budget & policies",
    body: "Create org, provider, or environment caps. Layer policies for regions, tenants, or sandboxes.",
    highlight: "Forecast vs. policy drift is called out automatically.",
  },
  {
    id: "explainable",
    label: "Explainable forecasts",
    body: "Confidence bands, attribution, and natural-language explanations you can forward to finance.",
    highlight: "Every chart links back to the queries it used--no black box.",
  },
];

const TIP_DECK: TipCardContent[] = [
  {
    id: "batching",
    front: { title: "Save with batching", subtitle: "Combine chat completions to cut OpenAI spend." },
    back: { insight: "Batch 5 calls -> 12% average savings.", savings: "Expected savings: ~12%" },
  },
  {
    id: "twilio",
    front: { title: "Route SMS smarter", subtitle: "Shift high-A2P traffic to lower-cost pools." },
    back: { insight: "Switching 30% of send to auth pool reduces cost.", savings: "Expected savings: ~9%" },
  },
  {
    id: "sendgrid",
    front: { title: "Warm IPs automatically", subtitle: "Automate SendGrid warm-up before promos." },
    back: { insight: "Keep stage traffic 20% above baseline.", savings: "Expected savings: ~6%" },
  },
];

const TESTIMONIALS: Testimonial[] = [
  {
    id: "maker",
    quote: "I'm building APICompass so solo founders don't have to guess what next month's AI bill looks like.",
    author: "Saurav Banerjee",
    role: "Maker @ APICompass",
  },
  {
    id: "beta1",
    quote: "We caught a Twilio tier jump 4 days early and rerouted traffic. That paid for the beta instantly.",
    author: "Lena Q.",
    role: "Founder, SMS-first SaaS",
  },
  {
    id: "beta2",
    quote: "The Local Connector let us keep restricted OpenAI keys on-device. Finance finally trusts our numbers.",
    author: "Ravi M.",
    role: "Staff Engineer, ML platform",
  },
];

const PRICING_TIERS: PricingTier[] = [
  {
    id: "free",
    name: "Free",
    priceINR: "₹0",
    priceUSD: "$0",
    bullets: [
      "2 providers | 1 environment",
      "Budget bar + explainable forecast",
      "Email alerts + estimator tool",
    ],
    cta: "Start free",
  },
  {
    id: "pro",
    name: "Pro",
    priceINR: "₹329-₹649",
    priceUSD: "$3.99-$7.99",
    bullets: [
      "Unlimited providers & policies",
      "Slack + webhook alerts",
      "Local Connector + Universal Connector",
      "Savings playbooks & audit trail",
    ],
    cta: "Join the beta",
    highlight: true,
  },
];

const FAQS: Faq[] = [
  {
    id: "security",
    question: "How does APICompass keep keys secure?",
    answer:
      "Use Cloud mode to paste restricted keys (stored encrypted) or run the Local Connector so keys never leave your machine--only usage aggregates sync back.",
  },
  {
    id: "providers",
    question: "Which providers are supported today?",
    answer:
      "Native connectors cover OpenAI, Anthropic, Twilio, SendGrid, Stripe, and AWS Bedrock. Anything else plugs in via the Universal Connector manifest in under 5 minutes.",
  },
  {
    id: "alerts",
    question: "How do alerts avoid noise?",
    answer:
      "Choose realtime or daily digest, set burn-rate thresholds, and scope by provider or environment. Alerts pause automatically after acknowledgement.",
  },
  {
    id: "cancel",
    question: "Can I cancel anytime?",
    answer:
      "Yes. Downgrade or cancel inside Settings with one click. We'll keep read-only dashboards for 30 days so finance can export the data.",
  },
];

const PROVIDER_FLOW = ["OpenAI", "Twilio", "SendGrid", "Stripe"];

const PROVIDER_OPTIONS = ["OpenAI", "Twilio", "SendGrid", "Stripe", "Other"];

const LEAD_MAGNET_MODES: Record<
  LeadMagnetMode,
  { label: string; volumeLabel: string; unitLabel: string; defaultUnit: number; description: string }
> = {
  llm: {
    label: "LLM Cost Estimator",
    volumeLabel: "Tokens / day",
    unitLabel: "Cost per 1K tokens (USD)",
    defaultUnit: 0.002,
    description: "Estimate GPT-style workloads and share a lightweight forecast.",
  },
  twilio: {
    label: "Twilio Tier Calculator",
    volumeLabel: "Messages / day",
    unitLabel: "Cost per SMS (USD)",
    defaultUnit: 0.0075,
    description: "Model tier jumps before campaigns go live.",
  },
};

const VALIDATION_METRICS = [
  "Hero CTA -> signup conversion (target 25-40% for qualified traffic).",
  "Signup -> survey completion (target >=10%).",
  "Scroll depth on Feature + Lead Magnet sections.",
  "Hero animation engagement vs. provider bubbles (A/B).",
];

const LEAD_SURVEY_QUESTIONS = [
  "Monthly API spend band?",
  "Providers you watch the most?",
  "Biggest pain today?",
];

function usePrefersReducedMotion(): boolean {
  const [prefers, setPrefers] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handleChange = () => setPrefers(media.matches);
    handleChange();
    if (media.addEventListener) {
      media.addEventListener("change", handleChange);
    } else {
      media.addListener(handleChange);
    }
    return () => {
      if (media.removeEventListener) {
        media.removeEventListener("change", handleChange);
      } else {
        media.removeListener(handleChange);
      }
    };
  }, []);
  return prefers;
}

function BudgetBarAnimation({ prefersReducedMotion }: { prefersReducedMotion: boolean }) {
  const [progress, setProgress] = useState(42);
  const [forecast, setForecast] = useState(2430);
  const targetProgress = 76;
  const targetForecast = 2720;

  useEffect(() => {
    if (prefersReducedMotion) {
      setProgress(targetProgress);
      setForecast(targetForecast);
      return;
    }
    let frame: number;
    const duration = 260;
    const startTime = performance.now();
    const animate = (now: number) => {
      const elapsed = now - startTime;
      const t = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setProgress(42 + (targetProgress - 42) * eased);
      setForecast(Math.round(2430 + (targetForecast - 2430) * eased));
      if (t < 1) {
        frame = requestAnimationFrame(animate);
      }
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [prefersReducedMotion, targetForecast, targetProgress]);

  return (
    <div
      className="rounded-3xl border border-white/10 bg-slate-900/60 p-6 text-white shadow-2xl shadow-emerald-500/10"
      aria-live="polite"
    >
      <div className="flex items-center justify-between text-sm uppercase tracking-wide text-emerald-200">
        <span>Live budget bar</span>
        <span>Forecast {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(forecast)}</span>
      </div>
      <div className="mt-3 h-4 rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-blue-400 to-cyan-400 transition-[width] duration-200 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-sm text-white/80">
        <span>Coverage {progress.toFixed(0)}%</span>
        <span>Forecast: ₹2,430-₹2,720</span>
      </div>
      <p className="mt-4 text-xs text-white/70">
        Confidence band = 68% | pulls OpenAI, Twilio, SendGrid spend every 90 seconds.
      </p>
    </div>
  );
}

function ProviderFlow({ prefersReducedMotion }: { prefersReducedMotion: boolean }) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion) return;
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % PROVIDER_FLOW.length);
    }, 1600);
    return () => clearInterval(interval);
  }, [prefersReducedMotion]);

  return (
    <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 p-6 text-white">
      <p className="text-sm uppercase tracking-wide text-white/70">Provider bubbles</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {PROVIDER_FLOW.map((provider, index) => {
          const isActive = index === activeIndex;
          return (
            <div
              key={provider}
              className={`flex items-center justify-between rounded-2xl border px-4 py-3 transition ${
                isActive
                  ? "border-emerald-400 bg-emerald-400/10 text-emerald-100"
                  : "border-white/10 bg-white/5 text-white/80"
              }`}
            >
              <span className="text-base font-semibold">{provider}</span>
              <span className={`text-xs font-semibold ${isActive ? "text-emerald-100" : "text-white/60"}`}>
                {(index + 1) * 12}% of spend
              </span>
            </div>
          );
        })}
      </div>
      <div className="mt-5 rounded-2xl border border-dashed border-white/15 px-4 py-5 text-sm text-white/80">
        <p className="font-semibold text-white">Unified chart</p>
        <p>Provider bubbles stream into a single forecast and alert timeline.</p>
      </div>
    </div>
  );
}

interface SignupFormProps {
  compact?: boolean;
}

function SignupForm({ compact = false }: SignupFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<RoleOption>("solo");
  const [provider, setProvider] = useState(PROVIDER_OPTIONS[0]);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const emailRegex = /\S+@\S+\.\S+/;
    if (!emailRegex.test(email.trim())) {
      setError("Add a valid email so we can confirm your invite.");
      return;
    }
    setError(null);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="rounded-2xl border border-emerald-400/50 bg-emerald-500/10 p-4 text-sm text-emerald-50">
        <p className="font-semibold">You're on the list!</p>
        <p className="mt-1">
          Expect an invite window soon. We'll send a 3-question pulse next ({LEAD_SURVEY_QUESTIONS.join(", ")}). The estimator widget below is now unlocked.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={`rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur ${
        compact ? "grid gap-3 md:grid-cols-2" : "space-y-4"
      }`}
    >
      <div className={compact ? "" : "space-y-3"}>
        <label className="text-sm text-white/70">
          Name <span className="text-white/40">(optional)</span>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mt-1 w-full rounded-lg border border-white/20 bg-transparent px-3 py-2 text-white placeholder:text-white/40 focus:border-emerald-400 focus:outline-none"
            placeholder="Indie dev, revops lead..."
          />
        </label>
        {!compact && (
          <label className="text-sm text-white/70">
            Role
            <select
              className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950 px-3 py-2 text-white focus:border-emerald-400 focus:outline-none"
              value={role}
              onChange={(event) => setRole(event.target.value as RoleOption)}
            >
              <option value="solo">Solo builder</option>
              <option value="team">Team / org admin</option>
            </select>
          </label>
        )}
      </div>
      <div className={compact ? "" : "space-y-3"}>
        <label className="text-sm text-white/70">
          Work email <span className="text-rose-300">*</span>
          <input
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-1 w-full rounded-lg border border-white/20 bg-transparent px-3 py-2 text-white placeholder:text-white/40 focus:border-emerald-400 focus:outline-none"
            placeholder="you@studio.dev"
            aria-describedby={error ? "signup-error" : undefined}
          />
        </label>
        <label className="text-sm text-white/70">
          Top provider you watch
          <select
            className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950 px-3 py-2 text-white focus:border-emerald-400 focus:outline-none"
            value={provider}
            onChange={(event) => setProvider(event.target.value)}
          >
            {PROVIDER_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className={compact ? "md:col-span-2" : ""}>
        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            className="inline-flex flex-1 items-center justify-center rounded-full bg-emerald-400/90 px-4 py-3 text-base font-semibold text-slate-950 transition hover:bg-emerald-300"
          >
            Join the beta - it's free
          </button>
          <button
            type="button"
            className="inline-flex flex-1 items-center justify-center rounded-full border border-white/20 px-4 py-3 text-base font-semibold text-white transition hover:border-emerald-400"
          >
            View demo
          </button>
        </div>
        <div className="mt-2 text-xs text-white/60">
          Prefer GitHub? <button type="button" className="underline">Continue with GitHub OAuth</button>
        </div>
        <p className="mt-1 text-xs text-white/60">
          Prefer to keep keys local? Use our Local Connector. Your keys never leave your machine.
        </p>
        {error && (
          <p id="signup-error" className="mt-1 text-sm text-rose-300">
            {error}
          </p>
        )}
      </div>
    </form>
  );
}

function LeadMagnetEstimator() {
  const [mode, setMode] = useState<LeadMagnetMode>("llm");
  const [volume, setVolume] = useState(125000);
  const [unitCost, setUnitCost] = useState(LEAD_MAGNET_MODES[mode].defaultUnit);
  const [days, setDays] = useState(30);

  useEffect(() => {
    setUnitCost(LEAD_MAGNET_MODES[mode].defaultUnit);
  }, [mode]);

  const result = useMemo(() => {
    const daily = (volume / 1000) * unitCost;
    const forecast = daily * days;
    const confidenceBand = [forecast * 0.9, forecast * 1.15] as const;
    return {
      forecast,
      confidenceBand,
      forecastINR: forecast * 83,
    };
  }, [volume, unitCost, days]);

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-8 text-white shadow-lg shadow-emerald-500/5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-emerald-200">Lead magnet</p>
          <h3 className="text-2xl font-semibold">{LEAD_MAGNET_MODES[mode].label}</h3>
          <p className="text-white/70">{LEAD_MAGNET_MODES[mode].description}</p>
        </div>
        <div className="flex rounded-full border border-white/10 bg-white/5 p-1 text-sm">
          {(Object.keys(LEAD_MAGNET_MODES) as LeadMagnetMode[]).map((option) => (
            <button
              key={option}
              type="button"
              className={`rounded-full px-4 py-1 font-semibold ${
                mode === option ? "bg-emerald-400 text-slate-950" : "text-white/70"
              }`}
              onClick={() => setMode(option)}
            >
              {LEAD_MAGNET_MODES[option].label.split(" ")[0]}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-4">
        <label className="text-sm text-white/70">
          {LEAD_MAGNET_MODES[mode].volumeLabel}
          <input
            type="number"
            min={1}
            value={volume}
            onChange={(event) => setVolume(Number(event.target.value) || 0)}
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-white focus:border-emerald-400 focus:outline-none"
          />
        </label>
        <label className="text-sm text-white/70">
          {LEAD_MAGNET_MODES[mode].unitLabel}
          <input
            type="number"
            min={0}
            step="0.0001"
            value={unitCost}
            onChange={(event) => setUnitCost(Number(event.target.value) || 0)}
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-white focus:border-emerald-400 focus:outline-none"
          />
        </label>
        <label className="text-sm text-white/70">
          Days this month
          <input
            type="number"
            min={7}
            value={days}
            onChange={(event) => setDays(Number(event.target.value) || 0)}
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-white focus:border-emerald-400 focus:outline-none"
          />
        </label>
        <div className="rounded-2xl border border-emerald-400/30 bg-emerald-500/5 p-4 text-sm text-white/80">
          <p className="text-xs uppercase tracking-wide text-emerald-200">Projected spend</p>
          <p className="text-2xl font-semibold text-white">
            ${result.forecast.toFixed(2)}
            <span className="ml-2 text-sm text-white/70">/ mo</span>
          </p>
          <p className="text-xs text-white/60">₹{result.forecastINR.toFixed(0)}</p>
          <p className="mt-1 text-xs text-white/60">
            Confidence {result.confidenceBand[0].toFixed(2)}-{result.confidenceBand[1].toFixed(2)} USD
          </p>
        </div>
      </div>
      <p className="mt-4 text-sm text-white/70">
        Drop this output straight into finance updates or compare against our automated forecast for accuracy drift.
      </p>
    </section>
  );
}

function TipDeck({ prefersReducedMotion }: { prefersReducedMotion: boolean }) {
  const flipEnabled = !prefersReducedMotion;
  return (
    <div className="grid gap-6 md:grid-cols-3">
      {TIP_DECK.map((tip) => (
        <div
          key={tip.id}
          className={`group relative h-56 rounded-2xl border border-emerald-400/20 bg-white/5 p-0 text-white ${
            flipEnabled ? "[perspective:1200px]" : ""
          }`}
        >
          <div
            className={`relative h-full w-full rounded-2xl p-6 transition duration-300 ${
              flipEnabled ? "[transform-style:preserve-3d] motion-safe:group-hover:[transform:rotateY(180deg)]" : ""
            }`}
          >
            <div
              className="absolute inset-0 flex flex-col justify-between rounded-2xl border border-white/10 bg-slate-950/70 p-6 text-left"
              style={{ backfaceVisibility: "hidden" }}
            >
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-emerald-200">Actionable tip</p>
                <h4 className="mt-2 text-lg font-semibold">{tip.front.title}</h4>
                <p className="text-sm text-white/70">{tip.front.subtitle}</p>
              </div>
              {!flipEnabled && (
                <p className="text-xs text-emerald-200">{tip.back.savings}</p>
              )}
            </div>
            {flipEnabled && (
              <div
                className="absolute inset-0 flex flex-col justify-between rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-6 text-left text-white"
                style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)" }}
              >
                <div>
                  <p className="text-xs uppercase tracking-wide text-emerald-200">Why it matters</p>
                  <p className="mt-2 text-base">{tip.back.insight}</p>
                </div>
                <p className="text-sm font-semibold text-emerald-200">{tip.back.savings}</p>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function LandingPage() {s
  const prefersReducedMotion = usePrefersReducedMotion();
  const [headlineIndex, setHeadlineIndex] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion) return;
    const timer = setInterval(() => {
      setHeadlineIndex((prev) => (prev + 1) % HEADLINE_VARIANTS.length);
    }, 6000);
    return () => clearInterval(timer);
  }, [prefersReducedMotion]);

  const activeHeadline = HEADLINE_VARIANTS[headlineIndex];

  return (
    <main className="bg-slate-950 text-white">
      <header className="relative overflow-hidden border-b border-white/10 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
        <div className="absolute inset-y-0 right-0 hidden w-1/3 bg-emerald-400/5 blur-3xl lg:block" aria-hidden="true" />
        <div className="mx-auto flex max-w-6xl flex-col gap-12 px-6 py-20 lg:flex-row lg:items-center">
          <div className="flex-1 space-y-6">
            <div className="inline-flex items-center gap-3 rounded-full border border-white/15 px-4 py-1 text-xs uppercase tracking-wide text-white/70">
              Seeking 50 beta users
              <span className="text-emerald-300">SOC2-in-progress</span>
            </div>
            <h1 className="text-4xl font-semibold leading-tight sm:text-5xl lg:text-6xl">{activeHeadline.title}</h1>
            <p className="text-lg text-white/80">{activeHeadline.explainer}</p>
            <p className="text-lg text-white/80">
              Connect your providers, see a live budget bar, get alerted before tier jumps, and cut waste with actionable tips. Works with OpenAI, Twilio, SendGrid, Stripe--and any API via our Universal Connector.
            </p>
            <div className="flex flex-wrap gap-3 text-sm text-white/70">
              <span className="rounded-full border border-white/20 px-3 py-1">No vendor lock-in</span>
              <span className="rounded-full border border-white/20 px-3 py-1">Privacy-first Local Connector</span>
              <span className="rounded-full border border-white/20 px-3 py-1">Forecast | alerts | savings tips</span>
            </div>
            <SignupForm />
            <div className="text-sm text-white/60">
              <p>What is it? API cost forecasts + controls. For whom? Indie devs to lean FinOps teams. Why now? AI workloads spike monthly--don't wait for the invoice.</p>
            </div>
            <div className="text-xs text-white/50">
              Tracking hero CTR, signup conversion, and scroll depth to validate copy. A/B idea: headline variant ("Stop surprise API bills" vs "Know your API bill before it hits").
            </div>
          </div>
          <div className="flex flex-1 flex-col gap-6 rounded-[32px] border border-white/10 bg-white/5 p-6 backdrop-blur">
            <BudgetBarAnimation prefersReducedMotion={prefersReducedMotion} />
            <ProviderFlow prefersReducedMotion={prefersReducedMotion} />
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 py-16" id="pillars">
        <p className="text-sm uppercase tracking-wide text-emerald-300">API cost pillars</p>
        <h2 className="mt-2 text-3xl font-semibold text-white">Forecast, alert, and save--faster than spreadsheets.</h2>
        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {VALUE_PILLARS.map((pillar) => (
            <article key={pillar.id} className="rounded-3xl border border-white/10 bg-white/5 p-6 text-white">
              <div className="mb-4 h-12 w-12 rounded-2xl border border-white/15 bg-gradient-to-br from-emerald-400/40 to-cyan-400/40" />
              <h3 className="text-xl font-semibold">{pillar.title}</h3>
              <p className="mt-2 text-white/70">{pillar.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-slate-900/60">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <p className="text-sm uppercase tracking-wide text-emerald-300">How it works</p>
          <h2 className="mt-2 text-3xl font-semibold text-white">Connect &gt; see forecast &gt; get alerts & tips</h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {HOW_IT_WORKS.map((step, index) => (
              <article key={step.id} className="rounded-3xl border border-white/10 bg-white/5 p-6">
                <span className="text-sm font-semibold text-emerald-300">Step {index + 1}</span>
                <h3 className="mt-2 text-2xl font-semibold">{step.title}</h3>
                <p className="mt-3 text-white/70">{step.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16" id="features">
        <p className="text-sm uppercase tracking-wide text-emerald-300">Feature deep dive</p>
        <h2 className="mt-2 text-3xl font-semibold text-white">Universal connector, privacy modes, budgets, explainable forecasts.</h2>
        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {FEATURE_DETAILS.map((feature) => (
            <article key={feature.id} className="rounded-3xl border border-white/10 bg-white/5 p-6">
              <div className="text-sm font-semibold uppercase tracking-wide text-white/60">{feature.label}</div>
              <p className="mt-2 text-lg font-semibold text-white">{feature.body}</p>
              <p className="mt-3 text-sm text-emerald-300">{feature.highlight}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-slate-900/60" id="tips">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm uppercase tracking-wide text-emerald-300">Actionable savings tips</p>
              <h2 className="text-3xl font-semibold text-white">Stop guesswork with explainable recommendations.</h2>
            </div>
            <p className="text-sm text-white/70">motion-safe hover &gt; flip reveals savings impact. Respects reduced-motion settings.</p>
          </div>
          <TipDeck prefersReducedMotion={prefersReducedMotion} />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16" id="social-proof">
        <div className="grid gap-8 md:grid-cols-2">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-8">
            <p className="text-sm uppercase tracking-wide text-emerald-300">Maker's note</p>
            <p className="mt-4 text-2xl font-semibold text-white">{TESTIMONIALS[0].quote}</p>
            <p className="mt-4 text-sm text-white/70">
              {TESTIMONIALS[0].author} | {TESTIMONIALS[0].role}
            </p>
            <div className="mt-6 rounded-2xl border border-white/10 bg-slate-900/80 p-4 text-sm text-white/70">
              Privacy-first mode--keep keys local with our connector. No vendor lock-in.
            </div>
          </div>
          <div className="space-y-6">
            {TESTIMONIALS.slice(1).map((testimonial) => (
              <blockquote key={testimonial.id} className="rounded-3xl border border-white/10 bg-white/5 p-6 text-white/80">
                <p className="text-lg">"{testimonial.quote.replace(/(^"|"$)/g, "")}"</p>
                <footer className="mt-3 text-sm text-white/60">
                  {testimonial.author} | {testimonial.role}
                </footer>
              </blockquote>
            ))}
            <div className="rounded-3xl border border-dashed border-emerald-400/40 p-6 text-sm text-white/70">
              <p className="font-semibold text-white">Seeking 50 beta users</p>
              <p>Get early access, drop feedback, and you'll keep Pro pricing at ₹329 / $3.99 for year one.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-slate-900/60" id="lead-magnet">
        <div className="mx-auto max-w-6xl px-6 py-16 space-y-8">
          <LeadMagnetEstimator />
          <div className="rounded-3xl border border-white/10 bg-white/5 p-8 text-sm text-white/70">
            <p className="text-base font-semibold text-white">Validation & experiments</p>
            <ul className="mt-3 list-disc space-y-2 pl-5">
              {VALIDATION_METRICS.map((metric) => (
                <li key={metric}>{metric}</li>
              ))}
            </ul>
            <p className="mt-4">
              Success proxy (week one): 25-40% hero &gt; signup conversion, &g;=10% survey completion. Tracking via lightweight analytics--no cookies required.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16" id="pricing">
        <p className="text-sm uppercase tracking-wide text-emerald-300">Pricing teaser</p>
        <h2 className="mt-2 text-3xl font-semibold text-white">Free vs Pro. Pay only when you&apos;re confident.</h2>
        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {PRICING_TIERS.map((tier) => (
            <article
              key={tier.id}
              className={`rounded-3xl border p-6 ${tier.highlight ? "border-emerald-400 bg-emerald-500/5" : "border-white/10 bg-white/5"}`}
            >
              <p className="text-sm uppercase tracking-wide text-white/70">{tier.name}</p>
              <div className="mt-4 text-3xl font-semibold text-white">
                {tier.priceINR} <span className="text-base text-white/60">({tier.priceUSD})</span>
              </div>
              <ul className="mt-4 space-y-2 text-sm text-white/80">
                {tier.bullets.map((bullet) => (
                  <li key={bullet}>• {bullet}</li>
                ))}
              </ul>
              <button
                type="button"
                className={`mt-6 w-full rounded-full px-4 py-3 text-base font-semibold transition ${
                  tier.highlight ? "bg-emerald-400 text-slate-950 hover:bg-emerald-300" : "bg-white/10 text-white hover:bg-white/20"
                }`}
              >
                {tier.cta}
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-slate-900/60" id="faq">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <p className="text-sm uppercase tracking-wide text-emerald-300">FAQ</p>
          <h2 className="mt-2 text-3xl font-semibold text-white">Security, supported providers, alerts, cancellation.</h2>
          <div className="mt-8 space-y-4">
            {FAQS.map((faq) => (
              <details key={faq.id} className="rounded-2xl border border-white/10 bg-white/5 p-4" open={faq.id === "security"}>
                <summary className="cursor-pointer text-lg font-semibold text-white">{faq.question}</summary>
                <p className="mt-2 text-white/70">{faq.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-6 py-16">
        <div className="rounded-3xl border border-emerald-400/30 bg-gradient-to-br from-emerald-500/20 via-slate-900 to-slate-950 p-8">
          <p className="text-sm uppercase tracking-wide text-emerald-200">Final CTA</p>
          <h2 className="mt-2 text-3xl font-semibold text-white">Join the beta, stay ahead of every API cost spike.</h2>
          <p className="mt-3 text-white/80">
            Drop your email, pick your primary provider, and we&apos;ll send the budget template + estimator instantly.
          </p>
          <div className="mt-6">
            <SignupForm compact />
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 bg-slate-950">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-10 text-sm text-white/60 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="font-semibold text-white">APICompass</p>
            <p>Security & Privacy | <a href="mailto:hello@apicompass.dev" className="underline">hello@apicompass.dev</a></p>
          </div>
          <div className="flex flex-wrap gap-4">
            <a href="https://status.apicompass.dev" className="underline">
              Status page
            </a>
            <a href="#features" className="underline">
              Features
            </a>
            <a href="#pricing" className="underline">
              Pricing
            </a>
            <a href="#lead-magnet" className="underline">
              LLM estimator
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}
