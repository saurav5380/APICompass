'use client';

import Link from "next/link";
import Image from "next/image";
import { signIn, signOut, useSession } from "next-auth/react";

const CTA_CLASSES =
  "rounded-full border border-white/20 px-4 py-2 text-sm font-semibold transition hover:border-white/40 hover:text-white";

export default function AuthBar() {
  const { data: session, status } = useSession();
  const isLoading = status === "loading";
  const user = session?.user;

  return (
    <div className="border-b border-white/10 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 text-white">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          API Compass
        </Link>
        <div className="flex items-center gap-4 text-sm text-white/80">
          {isLoading ? (
            <span className="animate-pulse text-white/60">Checking session…</span>
          ) : user ? (
            <>
              <Link href="/dashboard" className={CTA_CLASSES}>
                Dashboard
              </Link>
              <button
                type="button"
                className={CTA_CLASSES}
                onClick={() => signOut({ callbackUrl: "/" })}
              >
                Logout
              </button>
              <div className="flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-3 py-1.5">
                {user.image ? (
                  <Image
                    src={user.image}
                    alt={user.name ?? user.email ?? "Profile"}
                    width={28}
                    height={28}
                    className="h-7 w-7 rounded-full object-cover"
                    unoptimized
                  />
                ) : (
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/30 text-xs font-semibold text-white">
                    {(user.name ?? user.email ?? "A").slice(0, 1).toUpperCase()}
                  </div>
                )}
                <div className="text-left leading-tight">
                  <p className="text-xs font-semibold text-white">{user.name ?? user.email}</p>
                  {user.email && <p className="text-[11px] text-white/70">{user.email}</p>}
                </div>
              </div>
            </>
          ) : (
            <button
              type="button"
              className={CTA_CLASSES}
              onClick={() => signIn(undefined, { callbackUrl: "/dashboard" })}
            >
              Login
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
