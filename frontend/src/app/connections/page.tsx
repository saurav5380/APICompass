import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";
import type { Metadata } from "next";

import { authOptions } from "@/app/api/auth/[...nextauth]/route";
import { prisma } from "@/lib/prisma";
import ConnectionsClient from "./ConnectionsClient";

export const metadata: Metadata = {
  title: "Connections · API Compass",
};

export default async function ConnectionsPage() {
  const session = await getServerSession(authOptions);

  if (!session?.user?.email) {
    redirect("/api/auth/signin?callbackUrl=/connections");
  }

  const viewer = await prisma.user.findUnique({
    where: { email: session.user.email },
    select: {
      id: true,
      name: true,
      orgId: true,
      org: {
        select: {
          id: true,
          name: true,
        },
      },
    },
  });

  if (!viewer?.orgId) {
    redirect("/api/auth/signin?callbackUrl=/connections");
  }

  const orgName = viewer.org?.name ?? "Your organization";
  const userName = session.user.name ?? viewer.name ?? session.user.email;

  return (
    <ConnectionsClient
      orgId={viewer.orgId}
      orgName={orgName}
      userName={userName}
      userEmail={session.user.email}
    />
  );
}
