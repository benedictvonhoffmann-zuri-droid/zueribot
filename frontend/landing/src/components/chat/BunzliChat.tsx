import { useEffect, useMemo, useRef, useState } from "react";
import {
  AssistantRuntimeProvider,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useLocalRuntime,
  useMessage,
  useRemoteThreadListRuntime,
  useThread,
  useThreadListItem,
  useThreadRuntime,
} from "@assistant-ui/react";
import { makeAdapter } from "./adapter";
import { Markdown } from "./Markdown";
import { usePrefs, type Prefs } from "./prefs";
import { makeThreadHistory } from "./history";
import { localThreadListAdapter } from "./threads";
import { ThreadSidebar } from "./ThreadSidebar";
import { AuthProvider, useAuth } from "../../auth/AuthProvider";
import { setAuthTokenGetter } from "./authToken";

// ── helpers ─────────────────────────────────────────────────────────────

function messageText(content: readonly any[] | any[] | undefined): string {
  return (content ?? [])
    .map((c: any) => (c.type === "text" ? c.text : ""))
    .join("");
}

// ── icons (lucide-style, 1.75 stroke, 16px default) ────────────────────

const Icon = {
  ArrowUp: (p: any) => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  ),
  Shield: (p: any) => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  ),
};

// ── messages ───────────────────────────────────────────────────────────

function UserMessage() {
  return (
    <MessagePrimitive.Root className="flex justify-end my-5">
      <div className="max-w-[78%] rounded-[18px] bg-zurich-blue text-white px-4 py-2.5 text-[15.5px] leading-[1.55] whitespace-pre-wrap">
        <MessagePrimitive.Parts />
      </div>
    </MessagePrimitive.Root>
  );
}

function AssistantMessage() {
  const text = useMessage((m) => messageText(m.content));
  return (
    <MessagePrimitive.Root className="my-6 animate-[fade-in-up_.25s_ease]">
      {text ? <Markdown>{text}</Markdown> : <TypingIndicator />}
    </MessagePrimitive.Root>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-1">
      <span className="w-2 h-2 rounded-full bg-zurich-gray/60 animate-[pulse-dot_1.4s_ease-in-out_infinite]" />
      <span className="w-2 h-2 rounded-full bg-zurich-gray/60 animate-[pulse-dot_1.4s_ease-in-out_infinite] [animation-delay:.2s]" />
      <span className="w-2 h-2 rounded-full bg-zurich-gray/60 animate-[pulse-dot_1.4s_ease-in-out_infinite] [animation-delay:.4s]" />
    </div>
  );
}

// ── empty state ────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <ThreadPrimitive.Empty>
      <div className="flex flex-col items-center text-center px-4 pt-16 pb-8">
        <h1 className="text-[32px] font-semibold tracking-tight text-zurich-dark">
          Grüezi, ich bin <span className="text-gradient">Bünzli</span>
        </h1>
        <p className="mt-2 text-[15px] text-zurich-gray max-w-md">
          Dein Assistänt für Züri. Frag mich zu Verkehr, Wätter, Badis, Events und meh.
        </p>
      </div>
    </ThreadPrimitive.Empty>
  );
}

// ── follow-ups ─────────────────────────────────────────────────────────

function FollowUps() {
  const runtime = useThreadRuntime();
  const isRunning = useThread((t) => t.isRunning);
  const lastAssistant = useThread((t) => {
    const msgs = t.messages;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === "assistant") return msgs[i];
    }
    return null;
  });

  const suggestions = useMemo(() => {
    if (!lastAssistant || isRunning) return [] as string[];
    const txt = messageText((lastAssistant as any).content).toLowerCase();
    const pool: Record<string, string[]> = {
      tram: ["Zeig mir ui de Charte", "Wie lang isch d'Fahrt?"],
      wetter: ["Und übermorn?", "Wie isch s'Wasser im See?"],
      restaurant: ["Zeig mer nochli meh", "Wie teuer isches?"],
      event: ["Wo gnau isch das?", "Gits Tickets no?"],
      default: ["Mehr Details", "Alternative?", "Was söll i no wüsse?"],
    };
    let key = "default";
    if (/tram|bus|abfahrt|vbz|sbb|zug|departure/.test(txt)) key = "tram";
    else if (/wetter|weather|regen|sonn|temperatur/.test(txt)) key = "wetter";
    else if (/restaurant|café|cafe|bar|essen|food/.test(txt)) key = "restaurant";
    else if (/event|konzert|concert|kino|cinema|festival/.test(txt)) key = "event";
    return pool[key] ?? pool.default;
  }, [lastAssistant, isRunning]);

  if (!suggestions.length) return null;
  return (
    <div className="flex flex-wrap gap-2 mt-1 mb-4 animate-[fade-in-up_.3s_ease]">
      {suggestions.map((s) => (
        <button
          key={s}
          onClick={() =>
            runtime.append({ role: "user", content: [{ type: "text", text: s }] })
          }
          className="text-[13px] px-3.5 py-1.5 rounded-full border border-zurich-border bg-white text-zurich-dark hover:border-zurich-blue/50 hover:bg-zurich-blue/5 transition"
        >
          {s}
        </button>
      ))}
    </div>
  );
}

// ── composer with smart send button ────────────────────────────────────

function SmartComposer() {
  const [hasText, setHasText] = useState(false);

  return (
    <ComposerPrimitive.Root
      className="flex items-end gap-2 rounded-[22px] border border-zurich-border bg-white pl-4 pr-2 py-2 focus-within:border-zurich-blue/40 transition"
    >
      <ComposerPrimitive.Input
        autoFocus
        placeholder="Frag mich öppis über Züri…"
        rows={1}
        onChange={(e) => setHasText((e.target as HTMLTextAreaElement).value.trim().length > 0)}
        className="flex-1 resize-none bg-transparent py-2 text-[15.5px] leading-[1.55] text-zurich-dark placeholder:text-zurich-gray/80 outline-none max-h-48"
      />
      <ComposerPrimitive.Send
        className={
          "flex-none inline-flex items-center justify-center w-9 h-9 rounded-full transition disabled:cursor-not-allowed " +
          (hasText
            ? "bg-zurich-blue text-white hover:bg-zurich-blue-dark"
            : "bg-zh-black-10 text-zurich-gray")
        }
      >
        <Icon.ArrowUp />
      </ComposerPrimitive.Send>
    </ComposerPrimitive.Root>
  );
}

// ── main ──────────────────────────────────────────────────────────────

/**
 * Per-thread chat runtime. Called once per active thread by the remote
 * thread list runtime. The thread id (stored as `remoteId` in the list
 * adapter; falls back to `id` before `initialize` completes) scopes the
 * encrypted history adapter to this thread.
 */
function useBunzliThreadRuntime(getPrefs: () => Prefs) {
  const threadId = useThreadListItem(
    (s) => s.remoteId ?? s.id
  ) as string;

  const adapter = useMemo(() => makeAdapter(getPrefs), [getPrefs]);
  const history = useMemo(() => makeThreadHistory(threadId), [threadId]);

  return useLocalRuntime(adapter, { adapters: { history } });
}

function PrivacyBadge() {
  const [open, setOpen] = useState(false);
  const popRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const items = [
    { title: "Verschlüsslet i dim Browser", body: "Chat-History mit AES-256 verschlüsslet. Nur du häsch de Schlüssel." },
    { title: "Kei Server-Logs", body: "De Bünzli-Server schribt kei Access-Logs für Chat-Aafroge." },
    { title: "Kei Tracking-Header", body: "IP, Referrer und Cookies wärded vor em Modell entfernt." },
    { title: "Schwizer Hosting", body: "S Modell lauft uf Infomaniak z Gämf. Keini Date verlönd d Schwiz." },
  ];

  return (
    <div className="relative" ref={popRef}>
      <button
        onClick={() => setOpen((o) => !o)}
        title="Dateschutz-Garantiä"
        className="inline-flex items-center gap-1.5 h-8 px-3 rounded-full bg-white border border-zurich-border text-[12.5px] font-medium text-zurich-gray hover:text-zurich-dark hover:border-zurich-blue/40 shadow-short transition"
      >
        <span className="text-zurich-blue">
          <Icon.Shield />
        </span>
        <span>Privat</span>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded-2xl border border-zurich-border bg-white shadow-[0_12px_32px_rgba(0,0,0,0.08)] p-4 z-30 text-left animate-[fade-in-up_.2s_ease]">
          <div className="text-[14px] font-semibold text-zurich-dark mb-1">
            Dini Dateschutz-Garantiä
          </div>
          <p className="text-[12px] text-zurich-gray mb-3">
            Was gschiht mit dine Chats.
          </p>
          <ul className="space-y-2.5">
            {items.map((it) => (
              <li key={it.title} className="flex gap-2.5">
                <span className="flex-none mt-0.5 text-zurich-blue">
                  <Icon.Shield />
                </span>
                <div>
                  <div className="text-[13px] font-semibold text-zurich-dark">{it.title}</div>
                  <div className="text-[12px] text-zurich-gray leading-snug">{it.body}</div>
                </div>
              </li>
            ))}
          </ul>
          <a
            href="/#privacy"
            className="mt-3 inline-block text-[12px] text-zurich-blue hover:underline"
          >
            Meh zur Architektur →
          </a>
        </div>
      )}
    </div>
  );
}

function ChatPane() {
  return (
    <ThreadPrimitive.Root className="flex-1 min-w-0 flex flex-col bg-zh-black-5 relative">
      {/* Floating privacy badge, top-right. Informational only. */}
      <div className="absolute top-3 right-3 z-20">
        <PrivacyBadge />
      </div>

      {/* Top spacer so neither floating button (sidebar top-left, privacy
          top-right) overlaps content. */}
      <div className="flex-none h-14" />

      <ThreadPrimitive.Viewport className="chat-scroll flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-5">
          <EmptyState />
          <ThreadPrimitive.Messages
            components={{
              UserMessage,
              AssistantMessage,
            }}
          />
          <FollowUps />
          <div className="h-4" />
        </div>
      </ThreadPrimitive.Viewport>

      <div className="flex-none">
        <div className="mx-auto max-w-3xl px-5 pb-5 pt-2">
          <SmartComposer />
          <p className="mt-2 text-[11.5px] text-zurich-gray/80 text-center">
            Bünzli cha Fähler mache. Prüef wichtigi Infos.
          </p>
        </div>
      </div>
    </ThreadPrimitive.Root>
  );
}

function LoginScreen() {
  const { login } = useAuth();
  return (
    <div className="min-h-[100dvh] flex items-center justify-center bg-zh-black-5 px-6">
      <div className="w-full max-w-sm rounded-2xl border border-zurich-border bg-white shadow-short p-8 text-center">
        <h1 className="text-[22px] font-semibold tracking-tight text-zurich-dark">
          Grüezi, ich bin <span className="text-gradient">Bünzli</span>
        </h1>
        <p className="mt-2 text-[14px] text-zurich-gray">
          Zum Schwätzä musch dich zerst aamäldä.
        </p>
        <button
          onClick={() => login()}
          className="mt-5 w-full h-10 rounded-full bg-zurich-blue text-white text-[14px] font-medium hover:bg-zurich-blue-dark transition"
        >
          Aamäldä
        </button>
      </div>
    </div>
  );
}

function AuthedChat() {
  const { state, getAccessToken } = useAuth();
  const [prefs, setPrefs] = usePrefs();
  const prefsRef = useRef(prefs);
  prefsRef.current = prefs;

  useEffect(() => {
    setAuthTokenGetter(getAccessToken);
    return () => setAuthTokenGetter(null);
  }, [getAccessToken]);

  const runtime = useRemoteThreadListRuntime({
    adapter: localThreadListAdapter,
    runtimeHook: () => useBunzliThreadRuntime(() => prefsRef.current),
  });

  if (state.status === "loading") {
    return <div className="min-h-[100dvh] flex items-center justify-center bg-zh-black-5 text-[14px] text-zurich-gray">Lade…</div>;
  }
  if (state.status === "anonymous") {
    return <LoginScreen />;
  }

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <style>{`
        @keyframes fade-in-up { from { opacity: 0; transform: translateY(6px) } to { opacity: 1; transform: none } }
        @keyframes wordmark-in { from { opacity: 0; transform: translateX(-6px); letter-spacing: 0.02em } to { opacity: 1; transform: none; letter-spacing: normal } }
        @keyframes pulse-dot { 0%,80%,100% { opacity: 0.3; transform: scale(0.85) } 40% { opacity: 1; transform: scale(1) } }
        .prose-chat code { word-break: break-word }
        /* Thin, modern scrollbar */
        .chat-scroll::-webkit-scrollbar { width: 10px }
        .chat-scroll::-webkit-scrollbar-track { background: transparent }
        .chat-scroll::-webkit-scrollbar-thumb { background: transparent; border-radius: 10px; border: 3px solid transparent; background-clip: padding-box }
        .chat-scroll:hover::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); background-clip: padding-box; border: 3px solid transparent }
      `}</style>
      <div className="h-[100dvh] flex">
        <ThreadSidebar prefs={prefs} setPrefs={setPrefs} />
        <ChatPane />
      </div>
    </AssistantRuntimeProvider>
  );
}

export default function BunzliChat() {
  return (
    <AuthProvider>
      <AuthedChat />
    </AuthProvider>
  );
}
