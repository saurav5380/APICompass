import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";

import { authOptions } from "@/app/api/auth/[...nextauth]/route";
import DashboardClient from "./DashboardClient";

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);

  if (!session?.user?.email || !session.user.orgId) {
    redirect("/api/auth/signin?callbackUrl=/dashboard");
  }

  return <DashboardClient />;
}
