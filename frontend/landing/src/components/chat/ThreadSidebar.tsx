import { useEffect, useState } from "react";
import {
  ThreadListPrimitive,
  ThreadListItemPrimitive,
} from "@assistant-ui/react";
import type { Prefs } from "./prefs";

const COLLAPSE_KEY = "bunzli.sidebar.collapsed";

// ── icons ──────────────────────────────────────────────────────────────

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    </svg>
  );
}

function ChevronLeft() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function ChevronRight() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

function Caret({ open }: { open: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={"transition-transform duration-200 " + (open ? "rotate-90" : "")}
    >
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

function MapPinIcon({ className = "" }: { className?: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

function LockIcon({ className = "" }: { className?: string }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

function Lion({ size = 28 }: { size?: number }) {
  // Source SVG is white (fill="#FFFFFE"), so we invert to render dark on light.
  return (
    <img
      src="/zh-lion.svg"
      alt="Bünzli"
      width={size}
      height={Math.round(size * (136 / 102))}
      className="block select-none pointer-events-none"
      style={{ filter: "brightness(0) saturate(100%)" }}
    />
  );
}

// ── thread item ────────────────────────────────────────────────────────

function ThreadItem() {
  return (
    <ThreadListItemPrimitive.Root className="group relative flex items-center rounded-lg hover:bg-zh-black-5 transition data-[active]:bg-zurich-blue/10">
      <ThreadListItemPrimitive.Trigger className="flex-1 text-left px-3 py-2 text-[13.5px] text-zurich-dark truncate">
        <ThreadListItemPrimitive.Title fallback="Neui Chat" />
      </ThreadListItemPrimitive.Trigger>
      <ThreadListItemPrimitive.Delete
        className="opacity-0 group-hover:opacity-100 mr-1.5 p-1.5 rounded-md text-zurich-gray hover:text-badi-orange-dark hover:bg-white transition"
        aria-label="Chat löschä"
      >
        <TrashIcon />
      </ThreadListItemPrimitive.Delete>
    </ThreadListItemPrimitive.Root>
  );
}

// ── header ─────────────────────────────────────────────────────────────

function SidebarHeader({ onCollapse }: { onCollapse: () => void }) {
  return (
    <div className="flex items-center gap-2 px-1 pt-1">
      <button
        onClick={onCollapse}
        aria-label="Sidebar iiklappä"
        title="Iiklappä"
        className="w-10 h-10 flex-none inline-flex items-center justify-center rounded-lg hover:bg-zh-black-5 transition"
      >
        <Lion size={24} />
      </button>
      <span className="flex-1 min-w-0 text-[15px] font-semibold tracking-tight text-zurich-dark truncate animate-[wordmark-in_.35s_cubic-bezier(.2,.7,.2,1)_both]">
        Bünzli<span className="text-zurich-gray font-medium">.Space</span>
      </span>
      <button
        onClick={onCollapse}
        aria-label="Sidebar iiklappä"
        title="Iiklappä"
        className="flex-none w-8 h-8 inline-flex items-center justify-center rounded-md text-zurich-gray hover:text-zurich-dark hover:bg-zh-black-5 transition"
      >
        <ChevronLeft />
      </button>
    </div>
  );
}

// ── settings: location ─────────────────────────────────────────────────

function LocationItem({
  prefs,
  setPrefs,
}: {
  prefs: Prefs;
  setPrefs: (p: Partial<Prefs>) => void;
}) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const active = !!prefs.location;

  const share = () => {
    if (!navigator.geolocation) return setStatus("error");
    setStatus("loading");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPrefs({ location: { lat: pos.coords.latitude, lng: pos.coords.longitude } });
        setStatus("idle");
      },
      () => setStatus("error"),
      { enableHighAccuracy: false, timeout: 8000 }
    );
  };

  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-zh-black-5 transition text-left"
      >
        <span className={active ? "text-zurich-blue" : "text-zurich-gray"}>
          <MapPinIcon />
        </span>
        <span className="flex-1 text-[13.5px] text-zurich-dark">Standort</span>
        {active && (
          <span
            className="w-1.5 h-1.5 rounded-full bg-zurich-blue"
            aria-label="aktiv"
          />
        )}
        <span className="text-zurich-gray">
          <Caret open={open} />
        </span>
      </button>

      {open && (
        <div className="px-2 pb-2 pt-1 text-[12px] text-zurich-gray leading-snug animate-[fade-in-up_.2s_ease]">
          <p>
            Git Bünzli ortsrelevanti Antworte — s'nöchscht Tram, Badis, Restaurants.
            Wird nur lokal gspeichert.
          </p>
          {active && prefs.location && (
            <p className="mt-2 font-mono text-[11px] text-zurich-blue bg-zurich-blue/5 rounded px-2 py-1 inline-block">
              {prefs.location.lat.toFixed(4)}, {prefs.location.lng.toFixed(4)}
            </p>
          )}
          <div className="mt-2">
            {active ? (
              <button
                onClick={() => setPrefs({ location: undefined })}
                className="text-[12px] px-3 py-1.5 rounded-lg border border-zurich-border text-zurich-dark hover:bg-white transition"
              >
                Entfernä
              </button>
            ) : (
              <button
                onClick={share}
                disabled={status === "loading"}
                className="text-[12px] px-3 py-1.5 rounded-lg bg-zurich-blue text-white font-medium hover:bg-zurich-blue-dark transition disabled:opacity-60"
              >
                {status === "loading" ? "Lade…" : "Teilä"}
              </button>
            )}
          </div>
          {status === "error" && (
            <p className="mt-1.5 text-[11.5px] text-badi-orange-dark">
              Standort konnt nöd gholt wärde.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── settings section ───────────────────────────────────────────────────

function SidebarSettings({
  prefs,
  setPrefs,
}: {
  prefs: Prefs;
  setPrefs: (p: Partial<Prefs>) => void;
}) {
  return (
    <div className="flex-none -mx-3 px-3 pt-2 border-t border-zurich-border">
      <div className="flex items-center gap-2 px-1 mb-1">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-zurich-gray">
          Iistellige
        </span>
        <span className="flex-1 h-px bg-zurich-border" />
      </div>
      <div className="flex flex-col">
        <LocationItem prefs={prefs} setPrefs={setPrefs} />
      </div>
      <div
        className="mt-1 mx-1 mb-1 px-2 py-1.5 flex items-center gap-1.5 text-[11px] text-zurich-gray rounded-md bg-zh-black-5/60"
        title="Dini Chat-History isch mit AES-256 im Browser verschlüsslet."
      >
        <LockIcon className="text-zurich-blue" />
        <span>Chat-History · AES-256, nur lokal</span>
      </div>
    </div>
  );
}

// ── main ───────────────────────────────────────────────────────────────

export function ThreadSidebar({
  prefs,
  setPrefs,
}: {
  prefs: Prefs;
  setPrefs: (p: Partial<Prefs>) => void;
}) {
  // Desktop: collapsed = sidebar hidden, replaced by floating lion button.
  // Mobile:  uses the same collapsed flag, with overlay behavior.
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(COLLAPSE_KEY) === "1";
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
    } catch {
      // ignore
    }
  }, [collapsed]);

  return (
    <>
      {/* Floating expand button — lion by default, chevron-right on hover. */}
      {collapsed && (
        <button
          onClick={() => setCollapsed(false)}
          aria-label="Sidebar uufklappä"
          title="Chats"
          className="group fixed top-3 left-3 z-30 w-10 h-10 inline-flex items-center justify-center rounded-lg bg-white border border-zurich-border shadow-short hover:bg-zh-black-5 transition"
        >
          <span className="absolute inset-0 inline-flex items-center justify-center transition-opacity duration-150 group-hover:opacity-0">
            <Lion size={22} />
          </span>
          <span className="absolute inset-0 inline-flex items-center justify-center text-zurich-dark opacity-0 transition-opacity duration-150 group-hover:opacity-100">
            <ChevronRight />
          </span>
        </button>
      )}

      {/* Backdrop on mobile when sidebar is open */}
      {!collapsed && (
        <div
          className="md:hidden fixed inset-0 z-10 bg-black/20"
          onClick={() => setCollapsed(true)}
        />
      )}

      <aside
        className={
          "flex-none z-20 bg-white border-r border-zurich-border overflow-hidden " +
          "transition-[width,transform,border-color] duration-300 ease-[cubic-bezier(.2,.7,.2,1)] " +
          "fixed md:static inset-y-0 left-0 w-72 " +
          (collapsed
            ? "-translate-x-full md:translate-x-0 md:w-0 md:border-transparent"
            : "translate-x-0")
        }
      >
        {/* Inner wrapper keeps its full width during the collapse animation so
            content doesn't reflow while the outer aside shrinks. */}
        <div className="h-full w-72 flex flex-col p-3 gap-3">
          <SidebarHeader onCollapse={() => setCollapsed(true)} />

          <ThreadListPrimitive.Root className="flex flex-col flex-1 min-h-0">
            <ThreadListPrimitive.New className="inline-flex items-center gap-2 h-9 px-3 rounded-lg bg-zurich-blue text-white text-[13.5px] font-medium hover:bg-zurich-blue-dark transition">
              <PlusIcon />
              <span>Neui Chat</span>
            </ThreadListPrimitive.New>

            <div className="mt-4 mb-2 flex items-center gap-2 px-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-zurich-gray">
                Chats
              </span>
              <span className="flex-1 h-px bg-zurich-border" />
            </div>

            <div className="flex-1 overflow-y-auto -mx-1 px-1">
              <div className="flex flex-col gap-0.5">
                <ThreadListPrimitive.Items components={{ ThreadListItem: ThreadItem }} />
              </div>
            </div>
          </ThreadListPrimitive.Root>

          <SidebarSettings prefs={prefs} setPrefs={setPrefs} />
        </div>
      </aside>
    </>
  );
}
