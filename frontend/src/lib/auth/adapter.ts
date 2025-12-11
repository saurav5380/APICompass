import type { Adapter, AdapterUser } from "next-auth/adapters";
import type { PrismaClient } from "@prisma/client";
import { PrismaAdapter } from "@next-auth/prisma-adapter";

const deriveOrgName = (user?: Pick<AdapterUser, "email" | "name">) => {
  if (user?.name?.trim()) {
    return `${user.name.trim()}'s workspace`;
  }
  const emailHandle = user?.email?.split("@")[0];
  if (emailHandle) {
    return `${emailHandle}'s workspace`;
  }
  return "Personal workspace";
};

export const createApiCompassAdapter = (prisma: PrismaClient): Adapter => {
  const baseAdapter = PrismaAdapter(prisma);

  return {
    ...baseAdapter,
    async createUser(userData) {
      if (!userData.email) {
        throw new Error("Email is required to create a user record.");
      }

      const normalizedEmail = userData.email.trim().toLowerCase();
      const existingUser = await prisma.user.findFirst({
        where: {
          email: {
            equals: normalizedEmail,
            mode: "insensitive",
          },
        },
      });
      if (existingUser) {
        return existingUser;
      }

      const org = await prisma.org.create({
        data: {
          name: deriveOrgName(userData),
        },
        select: { id: true },
      });

      const createdUser = await prisma.user.create({
        data: {
          orgId: org.id,
          email: normalizedEmail,
          name: userData.name ?? null,
          fullName: userData.name ?? null,
          image: userData.image ?? null,
          emailVerified: userData.emailVerified ?? null,
          authProvider: "nextauth",
        },
      });

      return createdUser;
    },
  };
};
