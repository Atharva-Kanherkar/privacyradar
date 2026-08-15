import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { magicLink } from "better-auth/plugins";
import { Pool } from "pg";
import postgres from "postgres";
import { emailHash, safeCallbackURL } from "./auth-helpers";

const connectionString = process.env.DATABASE_URL ?? "";
const appOrigin = process.env.BETTER_AUTH_URL ?? "http://127.0.0.1:3000";

function isHostedProduction(): boolean {
  return (
    process.env.VERCEL_ENV === "production" ||
    process.env.RAILWAY_ENVIRONMENT_NAME === "production"
  );
}

function resolveAuthSecret(): string {
  const secret = process.env.AUTH_SECRET;
  if (secret && secret.length >= 16) {
    return secret;
  }
  if (isHostedProduction()) {
    throw new Error("AUTH_SECRET is required in production");
  }
  if (process.env.CI === "true" || process.env.AUTH_DELIVERY === "fixture") {
    return "ci-only-auth-secret-not-for-production";
  }
  throw new Error("AUTH_SECRET is required");
}

function fixtureDeliveryEnabled(): boolean {
  if (isHostedProduction()) {
    return false;
  }
  return process.env.AUTH_DELIVERY === "fixture";
}

const pool = new Pool({
  connectionString: connectionString || "postgresql://127.0.0.1:1/invalid",
  max: 4,
});

const sql = connectionString
  ? postgres(connectionString, { max: 2, idle_timeout: 20 })
  : null;

async function deliverMagicLink(email: string, url: string): Promise<void> {
  if (!fixtureDeliveryEnabled()) {
    return;
  }
  if (!sql) return;
  const safe = new URL(url, appOrigin);
  safe.searchParams.set(
    "callbackURL",
    safeCallbackURL(safe.searchParams.get("callbackURL")),
  );
  if (safe.searchParams.has("errorCallbackURL")) {
    safe.searchParams.set(
      "errorCallbackURL",
      safeCallbackURL(safe.searchParams.get("errorCallbackURL")),
    );
  }
  if (safe.searchParams.has("newUserCallbackURL")) {
    safe.searchParams.set(
      "newUserCallbackURL",
      safeCallbackURL(safe.searchParams.get("newUserCallbackURL")),
    );
  }
  await sql`
    insert into auth_magic_inbox (email_hash, url)
    values (${emailHash(email)}, ${safe.pathname + safe.search})
  `;
}

export const auth = betterAuth({
  secret: resolveAuthSecret(),
  baseURL: appOrigin,
  database: pool,
  trustedOrigins: [
    appOrigin,
    "https://privacyradar.app",
    "https://www.privacyradar.app",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
  ],
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
    requireEmailVerification: false,
  },
  logger: { disabled: true },
  user: {
    modelName: "auth_users",
    fields: {
      emailVerified: "email_verified",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
  session: {
    modelName: "auth_sessions",
    fields: {
      expiresAt: "expires_at",
      createdAt: "created_at",
      updatedAt: "updated_at",
      ipAddress: "ip_address",
      userAgent: "user_agent",
      userId: "user_id",
    },
  },
  account: {
    modelName: "auth_accounts",
    fields: {
      accountId: "account_id",
      providerId: "provider_id",
      userId: "user_id",
      accessToken: "access_token",
      refreshToken: "refresh_token",
      idToken: "id_token",
      accessTokenExpiresAt: "access_token_expires_at",
      refreshTokenExpiresAt: "refresh_token_expires_at",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
  verification: {
    modelName: "auth_verifications",
    fields: {
      expiresAt: "expires_at",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
  rateLimit: {
    enabled: true,
    window: 60,
    max: 200,
    customRules: {
      "/get-session": false,
    },
  },
  databaseHooks: {
    user: {
      create: {
        after: async (user) => {
          if (!sql) return;
          await sql`
            insert into consumer_profiles (user_id, region)
            values (${user.id}, 'unspecified')
            on conflict (user_id) do nothing
          `;
          await sql`
            insert into consent_events (user_id, action)
            values (${user.id}, 'signup')
          `;
        },
      },
    },
  },
  plugins: [
    magicLink({
      expiresIn: 600,
      storeToken: "hashed",
      disableSignUp: false,
      rateLimit: { window: 60, max: 20 },
      sendMagicLink: async ({ email, url }) => {
        await deliverMagicLink(email, url);
      },
    }),
    nextCookies(),
  ],
});

export { emailHash, safeCallbackURL } from "./auth-helpers";
