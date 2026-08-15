/**
 * Plain-language vocabulary for the extraction taxonomy. Every attribute the
 * worker can publish maps to a human label and a one-line explanation so the
 * UI never shows raw snake_case to a consumer.
 */

export type AttributeMeta = {
  label: string;
  plain: string;
};

export const DATA_COLLECTED: Record<string, AttributeMeta> = {
  email: { label: "Email address", plain: "The email you sign up or log in with." },
  name: { label: "Your name", plain: "Your legal or profile name." },
  phone: { label: "Phone number", plain: "Your mobile or contact number." },
  address: { label: "Home address", plain: "Your physical or mailing address." },
  location: { label: "Location", plain: "Where you are or where you've been." },
  device_id: { label: "Device identifiers", plain: "Serial numbers and IDs that mark your phone or laptop." },
  ip_address: { label: "IP address", plain: "Your network address, which can reveal rough location." },
  browsing: { label: "Browsing activity", plain: "Pages you visit and things you tap or click." },
  purchase: { label: "Purchase history", plain: "What you buy and when." },
  payment: { label: "Payment details", plain: "Cards, billing info, or transaction data." },
  photos: { label: "Photos & videos", plain: "Images and videos you upload or store." },
  voice: { label: "Voice recordings", plain: "Audio of your voice, like assistant commands or calls." },
  messages: { label: "Your messages", plain: "Contents of messages, chats, or emails on the service." },
  contacts: { label: "Your contacts", plain: "People in your address book." },
  account_activity: { label: "Account activity", plain: "How and when you use your account." },
  inferred_profile: { label: "Inferred profile", plain: "Guesses about you — interests, habits, demographics." },
  other: { label: "Other data", plain: "Additional data described in the policy." },
};

export const SENSITIVE: Record<string, AttributeMeta> = {
  biometrics: { label: "Biometrics", plain: "Fingerprints, face scans, or voice prints." },
  health: { label: "Health data", plain: "Medical, fitness, or wellness information." },
  children: { label: "Children's data", plain: "Data about kids under 13 (or local age limits)." },
  precise_location: { label: "Precise location", plain: "GPS-level tracking of exactly where you are." },
};

export const PURPOSE: Record<string, AttributeMeta> = {
  product: { label: "Running the product", plain: "Making the service itself work." },
  analytics: { label: "Analytics", plain: "Measuring how people use the service." },
  advertising: { label: "Advertising", plain: "Targeting or measuring ads." },
  personalization: { label: "Personalization", plain: "Tailoring content and recommendations to you." },
  security: { label: "Security", plain: "Preventing fraud and protecting accounts." },
  legal: { label: "Legal reasons", plain: "Complying with laws and legal requests." },
  ai_training: { label: "AI training", plain: "Using your data to train AI models." },
  research: { label: "Research", plain: "Studies and product research." },
  unspecified: { label: "Unspecified purposes", plain: "The policy doesn't say exactly why." },
};

export const SHARING: Record<string, AttributeMeta> = {
  sale: { label: "Sells data", plain: "The policy discusses selling personal data." },
  third_party: { label: "Shares with third parties", plain: "Data goes to other companies." },
  advertising_partner: { label: "Shares with advertisers", plain: "Data flows to advertising partners." },
  none_disclosed: { label: "No sharing disclosed", plain: "The captured policy doesn't disclose sharing." },
};

export const CONTROL: Record<string, AttributeMeta> = {
  deletion: { label: "You can delete your data", plain: "The policy offers a way to erase your data." },
  opt_out: { label: "You can opt out", plain: "You can say no to some uses of your data." },
  access: { label: "You can get a copy", plain: "You can request the data they hold on you." },
  none_disclosed: { label: "No controls disclosed", plain: "The captured policy doesn't disclose user controls." },
};

export const RETENTION: Record<string, AttributeMeta> = {
  duration_disclosed: { label: "Retention period disclosed", plain: "The policy says how long data is kept." },
  unspecified: { label: "Retention period not disclosed", plain: "The policy doesn't say how long data is kept." },
};

const FALLBACK_BY_CATEGORY: Record<string, Record<string, AttributeMeta>> = {
  data_collected: DATA_COLLECTED,
  sensitive: SENSITIVE,
  purpose: PURPOSE,
  sharing: SHARING,
  control: CONTROL,
  retention: RETENTION,
};

export function attributeMeta(category: string, attribute: string): AttributeMeta {
  const table = FALLBACK_BY_CATEGORY[category];
  const hit = table?.[attribute];
  if (hit) return hit;
  const label = attribute.replaceAll("_", " ");
  return { label: label.charAt(0).toUpperCase() + label.slice(1), plain: "" };
}
