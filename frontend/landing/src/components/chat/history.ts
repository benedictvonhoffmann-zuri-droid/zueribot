import type {
  ExportedMessageRepository,
  ExportedMessageRepositoryItem,
  ThreadHistoryAdapter,
} from "@assistant-ui/react";
import { encryptJson, decryptJson, type Ciphertext } from "./crypto";

const DB_NAME = "bunzli-chat";
const STORE = "messages";
const META = "meta";
const HEAD_KEY = "headId";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(META)) {
        db.createObjectStore(META);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function tx(db: IDBDatabase, mode: IDBTransactionMode, stores: string[]) {
  const t = db.transaction(stores, mode);
  return { t, stores: stores.map((s) => t.objectStore(s)) };
}

function promisify<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function clearHistory(): Promise<void> {
  const db = await openDb();
  const { t, stores } = tx(db, "readwrite", [STORE, META]);
  stores[0].clear();
  stores[1].clear();
  await new Promise<void>((r, rej) => {
    t.oncomplete = () => r();
    t.onerror = () => rej(t.error);
  });
  db.close();
}

// On-disk shape: id is clear (needed as key), payload is AES-GCM ciphertext
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

export const indexedDbHistory: ThreadHistoryAdapter = {
  async load(): Promise<ExportedMessageRepository> {
    try {
      const db = await openDb();
      const { t, stores } = tx(db, "readonly", [STORE, META]);
      const [msgStore, metaStore] = stores;
      const rows = await promisify<StoredRow[]>(
        msgStore.getAll() as IDBRequest<StoredRow[]>
      );
      const headId =
        (await promisify<string | undefined>(
          metaStore.get(HEAD_KEY) as IDBRequest<string | undefined>
        )) ?? null;
      await new Promise<void>((r) => {
        t.oncomplete = () => r();
      });
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
      const row: StoredRow = { id, ct };

      const db = await openDb();
      const { t, stores } = tx(db, "readwrite", [STORE, META]);
      const [msgStore, metaStore] = stores;
      msgStore.put(row);
      metaStore.put(id, HEAD_KEY);
      await new Promise<void>((r, rej) => {
        t.oncomplete = () => r();
        t.onerror = () => rej(t.error);
      });
      db.close();
    } catch {
      // best-effort; ignore
    }
  },
};
