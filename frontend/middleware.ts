import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { auth } from "./src/lib/auth/server";

const SIGN_IN_PATH = "/api/auth/signin";
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX_REQUESTS = 30;

type RateLimitStore = Map<string, number[]>;

declare global {
  // eslint-disable-next-line no-var
  var __apicAuthRateLimit?: RateLimitStore;
}

const globalRateStore = globalThis.__apicAuthRateLimit ?? new Map<string, number[]>();
if (!globalThis.__apicAuthRateLimit) {
  globalThis.__apicAuthRateLimit = globalRateStore;
}

const identifyRequest = (req: NextRequest) =>
  req.ip || req.headers.get("x-forwarded-for") || req.headers.get("cf-connecting-ip") || "anonymous";

const enforceAuthRateLimit = (req: NextRequest) => {
  const key = identifyRequest(req);
  const now = Date.now();
  const events = globalRateStore.get(key) ?? [];
  const recent = events.filter((ts) => now - ts < RATE_LIMIT_WINDOW_MS);
  recent.push(now);
  globalRateStore.set(key, recent);

  if (recent.length > RATE_LIMIT_MAX_REQUESTS) {
    const retryAfter = Math.ceil(RATE_LIMIT_WINDOW_MS / 1000).toString();
    const response = NextResponse.json({ error: "Too many auth attempts. Slow down." }, { status: 429 });
    response.headers.set("Retry-After", retryAfter);
    return response;
  }

  return null;
};

export default auth((req) => {
  const pathname = req.nextUrl.pathname;

  if (pathname.startsWith("/api/auth")) {
    const limited = enforceAuthRateLimit(req);
    if (limited) {
      return limited;
    }
    return NextResponse.next();
  }

  if (!req.auth) {
    const redirectUrl = new URL(SIGN_IN_PATH, req.nextUrl.origin);
    redirectUrl.searchParams.set("callbackUrl", req.nextUrl.pathname + req.nextUrl.search);
    return NextResponse.redirect(redirectUrl);
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/dashboard/:path*", "/connections/:path*", "/settings/:path*", "/api/auth/:path*"],
};
