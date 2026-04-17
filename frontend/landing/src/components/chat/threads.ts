import type { RemoteThreadListAdapter } from "@assistant-ui/react";
import { createAssistantStream } from "assistant-stream";
import { encryptJson, decryptJson, type Ciphertext } from "./crypto";
import {
  STORE_THREADS,
  awaitTx,
  openDb,
  promisify,
  txOf,
} from "./db";
import { deleteThreadMessages } from "./history";

// On-disk row: id in clear (IDB key), rest encrypted.
type ThreadRow = {
  id: string;
  ct: Ciphertext;
};

type ThreadMeta = {
  title: string;
  createdAt: number;
  archived: boolean;
};

async function putThread(id: string, meta: ThreadMeta): Promise<void> {
  const ct = await encryptJson(meta);
  const db = await openDb();
  const { t, stores } = txOf(db, "readwrite", [STORE_THREADS]);
  stores[0].put({ id, ct });
  await awaitTx(t);
  db.close();
}

async function readThread(id: string): Promise<ThreadMeta | null> {
  const db = await openDb();
  const { t, stores } = txOf(db, "readonly", [STORE_THREADS]);
  const row = (await promisify(
    stores[0].get(id) as IDBRequest<ThreadRow | undefined>
  )) as ThreadRow | undefined;
  await awaitTx(t);
  db.close();
  if (!row) return null;
  try {
    return await decryptJson<ThreadMeta>({
      iv: new Uint8Array(row.ct.iv),
      data: new Uint8Array(row.ct.data),
    });
  } catch {
    return null;
  }
}

async function mutateThread(
  id: string,
  fn: (meta: ThreadMeta) => ThreadMeta
): Promise<void> {
  const current = await readThread(id);
  if (!current) return;
  await putThread(id, fn(current));
}

function truncateTitle(text: string, max = 48): string {
  const normalized = text.trim().replace(/\s+/g, " ");
  if (normalized.length <= max) return normalized;
  const sliced = normalized.slice(0, max);
  const lastSpace = sliced.lastIndexOf(" ");
  return (lastSpace > max * 0.6 ? sliced.slice(0, lastSpace) : sliced).trim() + "…";
}

function extractText(message: any): string {
  const parts = message?.content ?? [];
  if (!Array.isArray(parts)) return "";
  return parts
    .map((p: any) => (p?.type === "text" ? p.text : ""))
    .join("")
    .trim();
}

/**
 * RemoteThreadListAdapter backed by IndexedDB. Thread metadata is AES-GCM-256
 * encrypted; only the thread id is in clear (it's the IDB key).
 *
 * "remoteId" here is just a local id — there is no remote. We keep the naming
 * from the @assistant-ui contract.
 */
export const localThreadListAdapter: RemoteThreadListAdapter = {
  async list() {
    try {
      const db = await openDb();
      const { t, stores } = txOf(db, "readonly", [STORE_THREADS]);
      const rows = (await promisify(
        stores[0].getAll() as IDBRequest<ThreadRow[]>
      )) as ThreadRow[];
      await awaitTx(t);
      db.close();

      const threads = await Promise.all(
        rows.map(async (row) => {
          try {
            const meta = await decryptJson<ThreadMeta>({
              iv: new Uint8Array(row.ct.iv),
              data: new Uint8Array(row.ct.data),
            });
            return {
              remoteId: row.id,
              title: meta.title,
              status: (meta.archived ? "archived" : "regular") as
                | "regular"
                | "archived",
              createdAt: meta.createdAt,
            };
          } catch {
            return null;
          }
        })
      );

      const valid = threads.filter(
        (t): t is NonNullable<typeof t> => t !== null
      );
      // Newest first.
      valid.sort((a, b) => b.createdAt - a.createdAt);
      return {
        threads: valid.map(({ remoteId, title, status }) => ({
          remoteId,
          title,
          status,
        })),
      };
    } catch {
      return { threads: [] };
    }
  },

  async initialize(threadId) {
    const meta: ThreadMeta = {
      title: "Neui Chat",
      createdAt: Date.now(),
      archived: false,
    };
    await putThread(threadId, meta);
    return { remoteId: threadId, externalId: undefined };
  },

  async rename(remoteId, newTitle) {
    await mutateThread(remoteId, (m) => ({ ...m, title: newTitle }));
  },

  async archive(remoteId) {
    await mutateThread(remoteId, (m) => ({ ...m, archived: true }));
  },

  async unarchive(remoteId) {
    await mutateThread(remoteId, (m) => ({ ...m, archived: false }));
  },

  async delete(remoteId) {
    await deleteThreadMessages(remoteId);
    const db = await openDb();
    const { t, stores } = txOf(db, "readwrite", [STORE_THREADS]);
    stores[0].delete(remoteId);
    await awaitTx(t);
    db.close();
  },

  async generateTitle(remoteId, messages) {
    // Heuristic title from the first user message. No LLM round-trip.
    const firstUser = messages.find((m: any) => m.role === "user");
    const source = firstUser ? extractText(firstUser) : "";
    const title = source ? truncateTitle(source) : "Neui Chat";
    await this.rename(remoteId, title);
    return createAssistantStream((ctrl) => {
      ctrl.appendText(title);
      ctrl.close();
    });
  },

  async fetch(threadId) {
    const meta = await readThread(threadId);
    return {
      remoteId: threadId,
      status: meta?.archived ? "archived" : "regular",
      title: meta?.title,
    };
  },
};
