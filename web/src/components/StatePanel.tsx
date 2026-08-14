export function StatePanel({
  title,
  children,
}: {
  title: string;
  children: string;
}) {
  return (
    <section
      className="mt-8 border border-[var(--rule)] bg-[var(--surface)] p-6"
      aria-live="polite"
    >
      <h2 className="font-sans text-lg">{title}</h2>
      <p className="mt-2 text-[var(--muted)]">{children}</p>
    </section>
  );
}
