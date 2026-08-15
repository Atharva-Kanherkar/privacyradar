import { safeCallbackURL } from "@/lib/callback-url";
import { accountsEnabled } from "@/lib/flags";
import { LoginForm } from "./LoginForm";

export const dynamic = "force-dynamic";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const params = await searchParams;
  const next = safeCallbackURL(params.next);

  if (!accountsEnabled()) {
    return (
      <main id="main" className="mx-auto max-w-md px-6 py-16 text-center">
        <h1 className="text-3xl font-semibold tracking-tight">
          Accounts are coming soon
        </h1>
        <p className="mt-4 text-muted-foreground">
          Watchlists and change alerts are almost ready. Until then, everything
          on PrivacyRadar is free to browse without an account.
        </p>
      </main>
    );
  }

  return (
    <main id="main" className="mx-auto max-w-md px-6 py-12">
      <h1 className="font-display text-3xl font-semibold tracking-tight">
        Welcome back
      </h1>
      <p className="mt-3 text-muted-foreground">
        Sign in to watch companies and get alerts when their privacy policies
        change. Browsing never requires an account.
      </p>
      <LoginForm next={next} />
    </main>
  );
}
