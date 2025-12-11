import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user: DefaultSession["user"] & {
      id: string;
      orgId: string;
      orgName?: string | null;
      email: string;
      name?: string | null;
    };
  }

  interface User {
    id: string;
    orgId: string;
    fullName?: string | null;
  }
}
