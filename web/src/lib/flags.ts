/**
 * Account features ship dark until sign-in is verified end to end in
 * production. Set ACCOUNTS_ENABLED=false to show the coming-soon state;
 * anything else (including unset, so local dev and CI) keeps accounts on.
 */
export function accountsEnabled(): boolean {
  return process.env.ACCOUNTS_ENABLED !== "false";
}
