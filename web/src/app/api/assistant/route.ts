import {
  assistantEnabled,
  buildSystemPrompt,
  clientIdentity,
  loadGrounding,
  recordUsage,
  underRateLimit,
  type ChatMessage,
} from "@/lib/assistant";
import { getSessionFromCookies } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_MESSAGES = 24;
const MAX_MESSAGE_LENGTH = 2000;

function jsonError(status: number, code: string, message: string): Response {
  return Response.json({ error: message, code }, { status });
}

function parseMessages(raw: unknown): ChatMessage[] | null {
  if (!Array.isArray(raw) || raw.length === 0 || raw.length > MAX_MESSAGES) {
    return null;
  }
  const messages: ChatMessage[] = [];
  for (const entry of raw) {
    if (typeof entry !== "object" || entry === null) return null;
    const { role, content } = entry as { role?: unknown; content?: unknown };
    if (role !== "user" && role !== "assistant") return null;
    if (typeof content !== "string" || content.length === 0) return null;
    messages.push({ role, content: content.slice(0, MAX_MESSAGE_LENGTH) });
  }
  if (messages[messages.length - 1]?.role !== "user") return null;
  return messages;
}

export async function POST(request: Request): Promise<Response> {
  if (!assistantEnabled()) {
    return jsonError(503, "disabled", "The assistant is currently off.");
  }

  let body: { slug?: unknown; messages?: unknown };
  try {
    body = (await request.json()) as { slug?: unknown; messages?: unknown };
  } catch {
    return jsonError(400, "bad_request", "Invalid request body.");
  }

  const slug = typeof body.slug === "string" ? body.slug : "";
  if (!/^[a-z0-9-]{1,80}$/.test(slug)) {
    return jsonError(400, "bad_request", "Invalid company.");
  }
  const messages = parseMessages(body.messages);
  if (!messages) {
    return jsonError(400, "bad_request", "Invalid messages.");
  }

  const grounding = await loadGrounding(slug);
  if (!grounding) {
    return jsonError(404, "unknown_company", "We do not track that company.");
  }

  const session = await getSessionFromCookies();
  const identity = clientIdentity(request.headers, session?.user?.id);
  if (!(await underRateLimit(identity))) {
    return jsonError(
      429,
      "rate_limited",
      "You have reached today's question limit. Come back tomorrow.",
    );
  }

  const model =
    process.env.ASSISTANT_MODEL ??
    process.env.OPENAI_EXTRACT_MODEL ??
    "gpt-4.1-mini";

  const upstream = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model,
      stream: true,
      max_tokens: 700,
      temperature: 0.3,
      messages: [
        { role: "system", content: buildSystemPrompt(grounding) },
        ...messages,
      ],
    }),
  });

  if (!upstream.ok || !upstream.body) {
    return jsonError(
      502,
      "provider_error",
      "The assistant could not reach its model. Try again in a moment.",
    );
  }

  // Only a question that reached the model spends quota.
  await recordUsage(identity);

  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  const reader = upstream.body.getReader();

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let buffered = "";
      try {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffered += decoder.decode(value, { stream: true });
          const lines = buffered.split("\n");
          buffered = lines.pop() ?? "";
          for (const line of lines) {
            const data = line.trim();
            if (!data.startsWith("data:")) continue;
            const payload = data.slice(5).trim();
            if (payload === "[DONE]") continue;
            try {
              const parsed = JSON.parse(payload) as {
                choices?: { delta?: { content?: string } }[];
              };
              const delta = parsed.choices?.[0]?.delta?.content;
              if (delta) controller.enqueue(encoder.encode(delta));
            } catch {
              // ignore malformed keep-alive frames
            }
          }
        }
      } finally {
        controller.close();
      }
    },
    cancel() {
      void reader.cancel();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Accel-Buffering": "no",
    },
  });
}
