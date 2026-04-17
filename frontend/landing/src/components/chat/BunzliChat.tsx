import { useEffect, useMemo, useRef, useState } from "react";
import {
  AssistantRuntimeProvider,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useLocalRuntime,
  useMessage,
  useThread,
  useThreadRuntime,
} from "@assistant-ui/react";
import { makeAdapter } from "./adapter";
import { Markdown } from "./Markdown";
import { usePrefs, type Prefs } from "./prefs";
import { clearHistory, indexedDbHistory } from "./history";

// ── helpers ─────────────────────────────────────────────────────────────

function messageText(content: readonly any[] | any[] | undefined): string {
  return (content ?? [])
    .map((c: any) => (c.type === "text" ? c.text : ""))
    .join("");
}

// ── icons (lucide-style, 1.75 stroke, 16px default) ────────────────────

const Icon = {
  MapPin: (p: any) => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  ),
  Plus: (p: any) => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  ),
  ArrowUp: (p: any) => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  ),
  Tram: (p: any) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <rect x="4" y="3" width="16" height="14" rx="2" />
      <path d="M4 11h16M8 21l2-4M16 21l-2-4M9 7h.01M15 7h.01" />
    </svg>
  ),
  Cloud: (p: any) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M17.5 19a5 5 0 0 0-1-9.9A6 6 0 0 0 4.5 11.5a4.5 4.5 0 0 0 1 8.9z" />
    </svg>
  ),
  Utensils: (p: any) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M3 2v7a3 3 0 0 0 3 3 3 3 0 0 0 3-3V2M6 12v10M14 12h7M17 2v10a3 3 0 0 0 3 3v7" />
    </svg>
  ),
  Sparkles: (p: any) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2zM19 14l1 2 2 1-2 1-1 2-1-2-2-1 2-1zM5 14l1 2 2 1-2 1-1 2-1-2-2-1 2-1z" />
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

type Starter = { icon: keyof typeof Icon; label: string; prompt: string };
const STARTERS: Starter[] = [
  { icon: "Tram", label: "Verkehr", prompt: "Wenn fahrt s'nöchschte Tram vom Bellevue?" },
  { icon: "Cloud", label: "Wätter", prompt: "Wie isch s'Wätter morn i Züri?" },
  { icon: "Utensils", label: "Essä", prompt: "Empfieh mir es guets Restaurant im Chreis 4" },
  { icon: "Sparkles", label: "Events", prompt: "Welli Events sind hüt z'Züri?" },
];

function EmptyState() {
  const runtime = useThreadRuntime();
  return (
    <ThreadPrimitive.Empty>
      <div className="flex flex-col items-center text-center px-4 pt-12 pb-8">
        <h1 className="text-[32px] font-semibold tracking-tight text-zurich-dark">
          Grüezi, ich bin <span className="text-gradient">Bünzli</span>
        </h1>
        <p className="mt-2 text-[15px] text-zurich-gray max-w-md">
          Dein Assistänt für Züri. Frag mich zu Verkehr, Wätter, Badis, Events und meh.
        </p>
        <div className="mt-10 grid grid-cols-2 gap-2.5 w-full max-w-xl">
          {STARTERS.map((s) => {
            const I = Icon[s.icon];
            return (
              <button
                key={s.prompt}
                onClick={() =>
                  runtime.append({
                    role: "user",
                    content: [{ type: "text", text: s.prompt }],
                  })
                }
                className="group flex items-start gap-3 text-left px-4 py-3.5 rounded-2xl border border-zurich-border bg-white hover:border-zurich-blue/40 hover:bg-white transition shadow-[0_1px_2px_rgba(0,0,0,0.02)]"
              >
                <span className="flex-none mt-0.5 text-zurich-blue"><I /></span>
                <span className="flex flex-col leading-snug">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-zurich-gray">{s.label}</span>
                  <span className="text-[14px] text-zurich-dark mt-0.5">{s.prompt}</span>
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </ThreadPrimitive.Empty>
  );
}

// ── header controls ────────────────────────────────────────────────────

function LocationButton({
  prefs,
  setPrefs,
}: {
  prefs: Prefs;
  setPrefs: (p: Partial<Prefs>) => void;
}) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const popRef = useRef<HTMLDivElement>(null);
  const active = !!prefs.location;

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const share = () => {
    if (!navigator.geolocation) return setStatus("error");
    setStatus("loading");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPrefs({ location: { lat: pos.coords.latitude, lng: pos.coords.longitude } });
        setStatus("idle");
        setOpen(false);
      },
      () => setStatus("error"),
      { enableHighAccuracy: false, timeout: 8000 }
    );
  };

  return (
    <div className="relative" ref={popRef}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={
          "inline-flex items-center gap-1.5 rounded-full h-8 px-3 text-[12.5px] font-medium transition " +
          (active
            ? "bg-zurich-blue/10 text-zurich-blue hover:bg-zurich-blue/15"
            : "text-zurich-gray hover:bg-zh-black-5 hover:text-zurich-dark")
        }
      >
        <Icon.MapPin />
        <span>Standort</span>
        {active && <span className="w-1.5 h-1.5 rounded-full bg-zurich-blue" />}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded-2xl border border-zurich-border bg-white shadow-[0_12px_32px_rgba(0,0,0,0.08)] p-4 z-20 text-left">
          <div className="text-[14px] font-semibold text-zurich-dark mb-1.5">
            Standort teilen
          </div>
          <p className="text-[13px] text-zurich-gray leading-relaxed">
            Bünzli chan dir ortsrelevanti Antworte geh — zum Bispiel d'nöchscht Tramhaltstell, Badis i de Nöchi oder Restaurants um dich ume.
          </p>
          <p className="mt-2.5 text-[11.5px] text-zurich-gray">
            Wird nur lokal im Browser gspeichert. Nie a öpper anders gschickt.
          </p>
          {active && prefs.location && (
            <p className="mt-3 text-[11.5px] font-mono text-zurich-blue bg-zurich-blue/5 rounded-lg px-2 py-1.5 inline-block">
              {prefs.location.lat.toFixed(4)}, {prefs.location.lng.toFixed(4)}
            </p>
          )}
          <div className="mt-4 flex gap-2">
            {active ? (
              <button
                onClick={() => {
                  setPrefs({ location: undefined });
                  setOpen(false);
                }}
                className="flex-1 text-[13px] px-3 py-2 rounded-xl border border-zurich-border text-zurich-dark hover:bg-zh-black-5 transition"
              >
                Entfernä
              </button>
            ) : (
              <button
                onClick={share}
                disabled={status === "loading"}
                className="flex-1 text-[13px] px-3 py-2 rounded-xl bg-zurich-blue text-white font-medium hover:bg-zurich-blue-dark transition disabled:opacity-60"
              >
                {status === "loading" ? "Lade…" : "Teilä"}
              </button>
            )}
          </div>
          {status === "error" && (
            <p className="mt-2 text-[11.5px] text-badi-orange-dark">
              Standort konnt nöd gholt wärde.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function PrivacyButton() {
  const [open, setOpen] = useState(false);
  const popRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const items: { title: string; body: string }[] = [
    {
      title: "Verschlüsslet i dim Browser",
      body: "Dini Chats wärded mit AES-256 verschlüsslet im Browser gspeichert. Nur du häsch de Schlüssel.",
    },
    {
      title: "Kei Server-Logs",
      body: "De Bünzli-Server schribt kei Access-Logs für Chat-Aafroge.",
    },
    {
      title: "Kei Tracking-Header",
      body: "IP, Referrer und Cookies wärded vor em Modell entfernt.",
    },
    {
      title: "Schwizer Hosting",
      body: "S Modell lauft uf Infomaniak z Gämf. Keini Date verlönd d Schwiz.",
    },
  ];

  return (
    <div className="relative" ref={popRef}>
      <button
        onClick={() => setOpen((o) => !o)}
        title="Dateschutz"
        className="inline-flex items-center gap-1.5 h-8 px-3 rounded-full text-[12.5px] font-medium text-zurich-gray hover:bg-zh-black-5 hover:text-zurich-dark transition"
      >
        <Icon.Shield />
        <span>Privat</span>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded-2xl border border-zurich-border bg-white shadow-[0_12px_32px_rgba(0,0,0,0.08)] p-4 z-20 text-left">
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

async function newChat(runtime: any) {
  await clearHistory();
  runtime?.reset?.();
}

function NewChatButton() {
  const runtime = useThreadRuntime();
  return (
    <button
      onClick={() => newChat(runtime)}
      title="Neues Gespräch (⌘K)"
      className="inline-flex items-center gap-1.5 h-8 px-3 rounded-full text-[12.5px] font-medium text-zurich-gray hover:bg-zh-black-5 hover:text-zurich-dark transition"
    >
      <Icon.Plus />
      <span>Neu</span>
    </button>
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

export default function BunzliChat() {
  const [prefs, setPrefs] = usePrefs();
  const prefsRef = useRef(prefs);
  prefsRef.current = prefs;
  const adapter = useMemo(() => makeAdapter(() => prefsRef.current), []);
  const runtime = useLocalRuntime(adapter, {
    adapters: { history: indexedDbHistory },
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        newChat((runtime as any)?.thread ?? runtime);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [runtime]);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <style>{`
        @keyframes fade-in-up { from { opacity: 0; transform: translateY(6px) } to { opacity: 1; transform: none } }
        @keyframes pulse-dot { 0%,80%,100% { opacity: 0.3; transform: scale(0.85) } 40% { opacity: 1; transform: scale(1) } }
        .prose-chat code { word-break: break-word }
        /* Thin, modern scrollbar */
        .chat-scroll::-webkit-scrollbar { width: 10px }
        .chat-scroll::-webkit-scrollbar-track { background: transparent }
        .chat-scroll::-webkit-scrollbar-thumb { background: transparent; border-radius: 10px; border: 3px solid transparent; background-clip: padding-box }
        .chat-scroll:hover::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); background-clip: padding-box; border: 3px solid transparent }
      `}</style>
      <ThreadPrimitive.Root className="h-[100dvh] flex flex-col bg-zh-black-5">
        <header className="flex-none">
          <div className="mx-auto max-w-3xl px-5 py-3 flex items-center gap-2">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <div className="w-7 h-7 rounded-lg bg-zurich-blue text-white flex items-center justify-center text-[11px] font-bold tracking-tight">
                B
              </div>
              <span className="text-[14.5px] font-semibold text-zurich-dark">Bünzli</span>
            </div>
            <PrivacyButton />
            <LocationButton prefs={prefs} setPrefs={setPrefs} />
            <NewChatButton />
          </div>
        </header>

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
              Bünzli cha Fähler mache. Prüef wichtigi Infos. ·
              {" "}
              <span className="inline-flex items-center gap-1 text-zurich-gray">
                <Icon.Shield /> AES-256 verschlüsslet, nur lokal
              </span>
            </p>
          </div>
        </div>
      </ThreadPrimitive.Root>
    </AssistantRuntimeProvider>
  );
}
