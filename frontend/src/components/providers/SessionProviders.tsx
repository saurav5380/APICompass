'use client';

import type { Session } from "next-auth";
import { SessionProvider } from "next-auth/react";

interface SessionProvidersProps {
  session: Session | null;
  children: React.ReactNode;
}

export default function SessionProviders({ session, children }: SessionProvidersProps) {
  return <SessionProvider session={session}>{children}</SessionProvider>;
}
