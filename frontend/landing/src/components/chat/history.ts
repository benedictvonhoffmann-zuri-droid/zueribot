import type {
  ExportedMessageRepository,
  ExportedMessageRepositoryItem,
  ThreadHistoryAdapter,
} from "@assistant-ui/react";
import { encryptJson, decryptJson, type Ciphertext } from "./crypto";
import {
  HEAD_PREFIX,
  STORE_MESSAGES,
  STORE_META,
  awaitTx,
  headKey,
  msgRowId,
  openDb,
  promisify,
  txOf,
} from "./db";

// On-disk shape: key is `${threadId}|${messageId}` (clear), payload is ciphertext.
type StoredRow = {
  id: string;
  ct: Ciphertext;
};

type PlainItem = {
  id: string;
  parentId: string | null;
  message: ExportedMessageRepositoryItem["message"];
  runConfig?: ExportedMessageRepositoryItem["runConfig"];
};

/**
 * Per-thread history adapter. Loads and appends messages scoped to a single
 * thread id. Messages are AES-GCM-256 encrypted before hitting IndexedDB.
 */
export function makeThreadHistory(threadId: string): ThreadHistoryAdapter {
  const prefix = `${threadId}|`;

  return {
    async load(): Promise<ExportedMessageRepository> {
      try {
        const db = await openDb();
        const { t, stores } = txOf(db, "readonly", [STORE_MESSAGES, STORE_META]);
        const [msgStore, metaStore] = stores;

        // Scan only rows with our thread prefix.
        const range = IDBKeyRange.bound(prefix, prefix + "\uffff");
        const rows = await promisify<StoredRow[]>(
          msgStore.getAll(range) as IDBRequest<StoredRow[]>
        );
        const headId =
          (await promisify<string | undefined>(
            metaStore.get(headKey(threadId)) as IDBRequest<string | undefined>
          )) ?? null;
        await awaitTx(t);
        db.close();

        const decrypted: PlainItem[] = [];
        for (const row of rows) {
          try {
            const item = await decryptJson<PlainItem>({
              iv: new Uint8Array(row.ct.iv),
              data: new Uint8Array(row.ct.data),
            });
            decrypted.push(item);
          } catch {
            // skip corrupt/undecryptable rows (e.g. key was rotated)
          }
        }

        return {
          headId,
          messages: decrypted.map((i) => ({
            message: i.message,
            parentId: i.parentId,
            runConfig: i.runConfig,
          })),
        };
      } catch {
        return { headId: null, messages: [] };
      }
    },

    async append(item: ExportedMessageRepositoryItem): Promise<void> {
      try {
        const id = (item.message as any).id as string;
        const plain: PlainItem = {
          id,
          parentId: item.parentId,
          message: item.message,
          runConfig: item.runConfig,
        };
        const ct = await encryptJson(plain);
        const row: StoredRow = { id: msgRowId(threadId, id), ct };

        const db = await openDb();
        const { t, stores } = txOf(db, "readwrite", [STORE_MESSAGES, STORE_META]);
        const [msgStore, metaStore] = stores;
        msgStore.put(row);
        metaStore.put(id, headKey(threadId));
        await awaitTx(t);
        db.close();
      } catch {
        // best-effort; ignore
      }
    },
  };
}

/** Delete every message belonging to a thread and its head pointer. */
export async function deleteThreadMessages(threadId: string): Promise<void> {
  const prefix = `${threadId}|`;
  const db = await openDb();
  const { t, stores } = txOf(db, "readwrite", [STORE_MESSAGES, STORE_META]);
  const [msgStore, metaStore] = stores;
  const range = IDBKeyRange.bound(prefix, prefix + "\uffff");
  msgStore.delete(range);
  metaStore.delete(headKey(threadId));
  await awaitTx(t);
  db.close();
}

/** Wipe every thread's messages + metadata. Used by the "forget everything" action. */
export async function clearAllHistory(): Promise<void> {
  const db = await openDb();
  const { t, stores } = txOf(db, "readwrite", [STORE_MESSAGES, STORE_META]);
  const [msgStore, metaStore] = stores;
  msgStore.clear();
  // Only clear head:* keys, not other meta values.
  const range = IDBKeyRange.bound(HEAD_PREFIX, HEAD_PREFIX + "\uffff");
  metaStore.delete(range);
  await awaitTx(t);
  db.close();
}
