import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { getServerSession } from "next-auth";

import "./globals.css";
import { authOptions } from "@/app/api/auth/[...nextauth]/route";
import SessionProviders from "@/components/providers/SessionProviders";
import AuthBar from "@/components/auth/AuthBar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "API Spend Tracker for Developers - Forecasts, Alerts, Savings Tips",
  description: "See and forecast your OpenAI/Twilio/SendGrid costs in one place. Alerts before tier jumps. Privacy-first local connector available.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await getServerSession(authOptions);

  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} bg-slate-950 text-white antialiased`}>
        <SessionProviders session={session}>
          <div className="min-h-screen bg-slate-950">
            <AuthBar />
            {children}
          </div>
        </SessionProviders>
      </body>
    </html>
  );
}
