import NextAuth, { type NextAuthOptions } from "next-auth";
import nodemailer from "nodemailer";
import EmailProvider from "next-auth/providers/email";
import GitHubProvider from "next-auth/providers/github";
import GoogleProvider from "next-auth/providers/google";
import { type SendVerificationRequestParams } from "next-auth/providers";
import { prisma } from "@/lib/prisma";
import { createApiCompassAdapter } from "@/lib/auth/adapter";

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

const APP_NAME = "API Compass";

const createVerificationHtml = (url: string) => `
  <body style="background:#0f172a;margin:0;padding:0;font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#e2e8f0;">
    <table width="100%" style="max-width:480px;margin:40px auto;padding:32px;background:#111827;border-radius:16px;">
      <tr>
        <td style="text-align:center;">
          <div style="font-size:24px;font-weight:600;margin-bottom:16px;">${APP_NAME}</div>
          <p style="color:#94a3b8;margin-bottom:24px;">Secure one-click sign-in to your dashboard.</p>
          <a href="${url}" style="display:inline-block;padding:12px 28px;background:#4f46e5;color:#ffffff;text-decoration:none;font-weight:600;border-radius:999px;">Sign in</a>
          <p style="color:#94a3b8;font-size:14px;margin-top:32px;">This magic link expires in 10 minutes. If you didn’t request it, you can safely ignore this email.</p>
        </td>
      </tr>
    </table>
  </body>
`;

const createVerificationText = (url: string) =>
  `Sign in to ${APP_NAME}\n${url}\n\nThis link expires in 10 minutes. If you did not request it, you can ignore this email.`;

const sendVerificationRequest = async ({
  identifier,
  url,
  provider,
}: SendVerificationRequestParams) => {
  const transport = nodemailer.createTransport(provider.server);

  const result = await transport.sendMail({
    to: identifier,
    from: provider.from,
    subject: `Your ${APP_NAME} magic link`,
    text: createVerificationText(url),
    html: createVerificationHtml(url),
  });

  const failed = [...(result.rejected ?? []), ...(result.pending ?? [])].filter(
    Boolean,
  );
  if (failed.length) {
    throw new Error(`Email(s) to ${failed.join(", ")} could not be sent`);
  }
};

const sessionUserSelect = {
  id: true,
  orgId: true,
  name: true,
  fullName: true,
  email: true,
  image: true,
  org: {
    select: {
      id: true,
      name: true,
    },
  },
} as const;

export const authOptions: NextAuthOptions = {
  adapter: createApiCompassAdapter(prisma),
  secret: process.env.NEXTAUTH_SECRET,
  session: {
    strategy: "database",
  },
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
      maxAge: 10 * 60, // 10 minutes
      sendVerificationRequest,
    }),
  ],
  callbacks: {
    async session({ session, user }) {
      if (!session.user?.email) {
        return session;
      }

      const profile =
        (user?.id &&
          (await prisma.user.findUnique({
            where: { id: user.id },
            select: sessionUserSelect,
          }))) ??
        (await prisma.user.findFirst({
          where: {
            email: {
              equals: session.user.email,
              mode: "insensitive",
            },
          },
          select: sessionUserSelect,
        }));

      if (profile) {
        session.user.id = profile.id;
        session.user.orgId = profile.orgId;
        session.user.orgName = profile.org?.name ?? "Your organization";
        session.user.name =
          profile.name ?? profile.fullName ?? session.user.name ?? profile.email;
        session.user.image = profile.image ?? session.user.image ?? null;
      }

      return session;
    },
    async redirect({ url, baseUrl }) {
      const dashboardUrl = `${baseUrl}/dashboard`;

      if (url.startsWith("/")) {
        if (url.startsWith("/api/auth")) {
          return dashboardUrl;
        }
        return `${baseUrl}${url}`;
      }

      try {
        const targetUrl = new URL(url);
        if (targetUrl.origin === baseUrl) {
          if (targetUrl.pathname.startsWith("/api/auth")) {
            return dashboardUrl;
          }
          return targetUrl.toString();
        }
      } catch {
        // fall through to dashboard fallback
      }

      return dashboardUrl;
    },
  },
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
