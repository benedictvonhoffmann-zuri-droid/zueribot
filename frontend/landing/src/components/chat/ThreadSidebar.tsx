import { useState } from "react";
import {
  ThreadListPrimitive,
  ThreadListItemPrimitive,
} from "@assistant-ui/react";

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

function MenuIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18M3 12h18M3 18h18" />
    </svg>
  );
}

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

export function ThreadSidebar() {
  const [open, setOpen] = useState(true);

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="md:hidden fixed top-3 left-3 z-30 inline-flex items-center justify-center w-9 h-9 rounded-lg bg-white border border-zurich-border text-zurich-dark shadow-short"
        aria-label="Chats"
      >
        <MenuIcon />
      </button>

      {/* Backdrop on mobile when open */}
      {open && (
        <div
          className="md:hidden fixed inset-0 z-10 bg-black/20"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={
          "flex-none z-20 bg-white border-r border-zurich-border transition-transform " +
          "fixed md:static inset-y-0 left-0 w-72 " +
          (open ? "translate-x-0" : "-translate-x-full md:translate-x-0 md:w-0 md:border-0 md:overflow-hidden")
        }
      >
        <div className="h-full flex flex-col p-3 gap-3">
          <div className="flex items-center justify-between px-1 pt-1">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zurich-gray">
              Chats
            </span>
            <button
              onClick={() => setOpen(false)}
              className="md:hidden text-zurich-gray hover:text-zurich-dark p-1"
              aria-label="Schliessä"
            >
              ✕
            </button>
          </div>

          <ThreadListPrimitive.Root className="flex flex-col gap-2 min-h-0">
            <ThreadListPrimitive.New className="inline-flex items-center gap-2 h-9 px-3 rounded-lg border border-zurich-border text-[13.5px] font-medium text-zurich-dark hover:bg-zh-black-5 transition">
              <PlusIcon />
              <span>Neui Chat</span>
            </ThreadListPrimitive.New>

            <div className="flex-1 overflow-y-auto -mx-1 px-1">
              <div className="flex flex-col gap-0.5">
                <ThreadListPrimitive.Items components={{ ThreadListItem: ThreadItem }} />
              </div>
            </div>
          </ThreadListPrimitive.Root>
        </div>
      </aside>
    </>
  );
}
