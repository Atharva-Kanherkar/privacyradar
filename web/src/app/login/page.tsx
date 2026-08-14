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
    <main id="main" className="mx-auto max-w-xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">Sign in</h1>
      <p className="mt-3 text-[var(--muted)]">
        We email a single-use link. Browsing companies does not require an
        account. We do not infer your region from your IP address.
      </p>
      <LoginForm next={next} />
    </main>
  );
}
