import type { ChatModelAdapter } from "@assistant-ui/react";
import type { Prefs } from "./prefs";
import { buildContextBlock } from "./prefs";
import { getAccessToken } from "./authToken";

const ENDPOINT = import.meta.env.DEV
  ? "http://localhost/zuribot/v1/chat/completions"
  : "/zuribot/v1/chat/completions";

type OpenAIMsg = { role: string; content: string };

function toOpenAI(messages: readonly any[]): OpenAIMsg[] {
  return messages.map((m: any) => ({
    role: m.role,
    content: (m.content || [])
      .map((c: any) => (c.type === "text" ? c.text : ""))
      .join(""),
  }));
}

export function makeAdapter(getPrefs: () => Prefs): ChatModelAdapter {
  return {
    async *run({ messages, abortSignal }) {
      const openai = toOpenAI(messages);
      const prefs = getPrefs();
      const ctx = buildContextBlock(prefs);
      const withContext: OpenAIMsg[] = ctx
        ? [{ role: "system", content: ctx }, ...openai]
        : openai;

      const token = getAccessToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const r = await fetch(ENDPOINT, {
        method: "POST",
        headers,
        body: JSON.stringify({
          model: "zuribot",
          messages: withContext,
          stream: true,
        }),
        signal: abortSignal,
      });

      if (!r.ok || !r.body) {
        throw new Error(`Bünzli error: ${r.status} ${await r.text()}`);
      }

      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let text = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        let idx: number;
        while ((idx = buf.indexOf("\n")) >= 0) {
          const line = buf.slice(0, idx).trim();
          buf = buf.slice(idx + 1);
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (payload === "[DONE]") {
            yield { content: [{ type: "text", text }] };
            return;
          }
          try {
            const j = JSON.parse(payload);
            const delta = j.choices?.[0]?.delta?.content;
            if (delta) {
              text += delta;
              yield { content: [{ type: "text", text }] };
            }
          } catch {
            // ignore parse errors mid-stream
          }
        }
      }

      yield { content: [{ type: "text", text }] };
    },
  };
}
