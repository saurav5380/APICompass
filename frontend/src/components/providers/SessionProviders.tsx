'use client';

import type { Session } from "next-auth";
import { SessionProvider } from "next-auth/react";
import { QueryClientProvider } from "@tanstack/react-query";

import queryClient from "@/lib/queryClient";

interface SessionProvidersProps {
  session: Session | null;
  children: React.ReactNode;
}

export default function SessionProviders({ session, children }: SessionProvidersProps) {
  return (
    <SessionProvider session={session}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </SessionProvider>
  );
}
