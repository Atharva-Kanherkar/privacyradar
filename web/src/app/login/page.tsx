import { safeCallbackURL } from "@/lib/callback-url";
import { LoginForm } from "./LoginForm";

export const dynamic = "force-dynamic";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const params = await searchParams;
  const next = safeCallbackURL(params.next);

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
