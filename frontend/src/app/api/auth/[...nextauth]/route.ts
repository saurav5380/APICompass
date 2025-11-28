import NextAuth, { type NextAuthOptions } from "next-auth";
import { PrismaAdapter } from "@next-auth/prisma-adapter";
import EmailProvider from "next-auth/providers/email";
import GitHubProvider from "next-auth/providers/github";
import GoogleProvider from "next-auth/providers/google";
import { prisma } from "@/lib/prisma";

const warnIfMissing = (name: string) => {
  if (!process.env[name]) {
    console.warn(`[auth] Missing environment variable: ${name}`);
  }
};

const emailPort = Number(process.env.EMAIL_SERVER_PORT ?? 587);
if (!Number.isFinite(emailPort)) {
  console.warn(
    "[auth] EMAIL_SERVER_PORT is invalid. Falling back to port 587 for the email provider.",
  );
}

warnIfMissing("NEXTAUTH_SECRET");
warnIfMissing("GOOGLE_CLIENT_ID");
warnIfMissing("GOOGLE_CLIENT_SECRET");
warnIfMissing("GITHUB_CLIENT_ID");
warnIfMissing("GITHUB_CLIENT_SECRET");
warnIfMissing("EMAIL_SERVER_HOST");
warnIfMissing("EMAIL_SERVER_USER");
warnIfMissing("EMAIL_SERVER_PASSWORD");
warnIfMissing("EMAIL_FROM");

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  secret: process.env.NEXTAUTH_SECRET,
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
    }),
    GitHubProvider({
      clientId: process.env.GITHUB_CLIENT_ID ?? "",
      clientSecret: process.env.GITHUB_CLIENT_SECRET ?? "",
    }),
    EmailProvider({
      server: {
        host: process.env.EMAIL_SERVER_HOST ?? "localhost",
        port: Number.isFinite(emailPort) ? emailPort : 587,
        auth: {
          user: process.env.EMAIL_SERVER_USER ?? "",
          pass: process.env.EMAIL_SERVER_PASSWORD ?? "",
        },
      },
      from: process.env.EMAIL_FROM ?? "no-reply@example.com",
    }),
  ],
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
