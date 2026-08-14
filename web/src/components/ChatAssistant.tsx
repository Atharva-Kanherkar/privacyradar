"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { Radar, SendHorizontal, Sparkles } from "lucide-react";

type Message = { role: "user" | "assistant"; content: string };

const MAX_INPUT = 2000;

export function ChatAssistant({
  slug,
  companyName,
}: {
  slug: string;
  companyName: string;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  // Synchronous lock: `streaming` state is stale within the same render, so a
  // double Enter/click could start two requests without this.
  const sendingRef = useRef(false);

  const suggestions = [
    `What data does ${companyName} collect about me?`,
    "Do they sell or share my data?",
    "Can I delete my data?",
    "Do they use my data to train AI?",
  ];

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => () => abortRef.current?.abort(), []);

  async function send(question: string) {
    const trimmed = question.trim().slice(0, MAX_INPUT);
    if (!trimmed || sendingRef.current) return;
    sendingRef.current = true;
    setError(null);
    setInput("");
    const history: Message[] = [...messages, { role: "user", content: trimmed }];
    setMessages([...history, { role: "assistant", content: "" }]);
    setStreaming(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await fetch("/api/assistant", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug, messages: history }),
        signal: controller.signal,
      });
      if (!response.ok) {
        let message = "Something went wrong. Please try again.";
        try {
          const payload = (await response.json()) as { error?: string };
          if (payload?.error) message = payload.error;
        } catch {
          // keep the generic message
        }
        setMessages(history);
        setError(message);
        return;
      }
      if (!response.body) {
        setMessages(history);
        setError("No response received. Please try again.");
        return;
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let answer = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        answer += decoder.decode(value, { stream: true });
        const snapshot = answer;
        setMessages([...history, { role: "assistant", content: snapshot }]);
      }
      if (!answer.trim()) {
        setMessages(history);
        setError("The assistant returned an empty answer. Please try again.");
      }
    } catch (cause) {
      if ((cause as Error).name !== "AbortError") {
        setMessages(history);
        setError("Connection lost. Please try again.");
      }
    } finally {
      sendingRef.current = false;
      setStreaming(false);
      abortRef.current = null;
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send(input);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send(input);
    }
  }

  return (
    <section
      aria-label={`Chat about ${companyName}'s privacy policy`}
      className="mt-12 overflow-hidden rounded-2xl border border-[var(--rule)] bg-[var(--surface)] shadow-sm"
    >
      <div className="flex items-center gap-2 border-b border-[var(--rule)] px-5 py-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
          <Sparkles size={16} aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-sans text-base font-semibold">
            Ask about {companyName}&rsquo;s privacy policy
          </h2>
          <p className="font-sans text-xs text-[var(--muted)]">
            Answers come only from the captured policy evidence. Not legal advice.
          </p>
        </div>
      </div>

      <div
        ref={scrollRef}
        className="max-h-[26rem] min-h-[10rem] space-y-4 overflow-y-auto px-5 py-4"
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <div className="flex flex-wrap gap-2 py-2">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => void send(suggestion)}
                className="min-h-10 rounded-full border border-[var(--rule)] bg-white px-4 font-sans text-sm text-[var(--ink)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]"
              >
                {suggestion}
              </button>
            ))}
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {message.role === "assistant" ? (
                <span
                  aria-hidden="true"
                  className="mr-2 mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]"
                >
                  <Radar size={14} />
                </span>
              ) : null}
              <div
                className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 font-sans text-[0.95rem] leading-relaxed ${
                  message.role === "user"
                    ? "bg-[var(--ink)] text-white"
                    : "bg-[var(--panel)] text-[var(--ink)]"
                }`}
              >
                {message.content ||
                  (streaming && index === messages.length - 1 ? (
                    <span className="inline-flex gap-1" aria-label="Thinking">
                      <span className="animate-bounce">·</span>
                      <span className="animate-bounce [animation-delay:120ms]">·</span>
                      <span className="animate-bounce [animation-delay:240ms]">·</span>
                    </span>
                  ) : (
                    ""
                  ))}
              </div>
            </div>
          ))
        )}
        {error ? (
          <p role="alert" className="font-sans text-sm text-[var(--danger)]">
            {error}
          </p>
        ) : null}
      </div>

      <form
        onSubmit={onSubmit}
        className="flex items-end gap-2 border-t border-[var(--rule)] px-4 py-3"
      >
        <label htmlFor="assistant-input" className="sr-only">
          Question about this company
        </label>
        <textarea
          id="assistant-input"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          maxLength={MAX_INPUT}
          placeholder={`Message PrivacyRadar about ${companyName}…`}
          className="max-h-40 min-h-11 w-full resize-y rounded-xl border border-[var(--rule)] bg-white px-4 py-2.5 font-sans text-[0.95rem] outline-none focus:border-[var(--accent)]"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          aria-label="Send"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--accent)] text-white transition-opacity disabled:opacity-40"
        >
          <SendHorizontal size={18} aria-hidden="true" />
        </button>
      </form>
    </section>
  );
}
