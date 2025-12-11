import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";
import type { Metadata } from "next";

import { authOptions } from "@/app/api/auth/[...nextauth]/route";
import ConnectionsClient from "./ConnectionsClient";

export const metadata: Metadata = {
  title: "Connections · API Compass",
};

export default async function ConnectionsPage() {
  const session = await getServerSession(authOptions);

  if (!session?.user?.email || !session.user.orgId) {
    redirect("/api/auth/signin?callbackUrl=/connections");
  }

  const orgName = session.user.orgName ?? "Your organization";
  const userName = session.user.name ?? session.user.email;

  return (
    <ConnectionsClient
      orgId={session.user.orgId}
      orgName={orgName}
      userName={userName}
      userEmail={session.user.email}
    />
  );
}
