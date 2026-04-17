// Shared IndexedDB opener for Bünzli chat.
//
// v2 schema:
//   - "messages": rows keyed by composite `${threadId}|${messageId}`
//   - "threads":  keyPath "id", encrypted metadata (title, createdAt, archived)
//   - "meta":     `head:${threadId}` → last message id per thread
//
// A new DB name (-v2) replaces the v1 single-thread DB rather than migrating
// in-place. Existing users lose their single test conversation; acceptable
// for a pre-beta feature. v1's `bunzli-chat` DB is left orphaned in the
// browser until the user clears site data.

export const DB_NAME = "bunzli-chat-v2";
export const STORE_MESSAGES = "messages";
export const STORE_THREADS = "threads";
export const STORE_META = "meta";

export const HEAD_PREFIX = "head:";

export function msgRowId(threadId: string, messageId: string): string {
  return `${threadId}|${messageId}`;
}

export function headKey(threadId: string): string {
  return `${HEAD_PREFIX}${threadId}`;
}

export function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_MESSAGES)) {
        db.createObjectStore(STORE_MESSAGES, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(STORE_THREADS)) {
        db.createObjectStore(STORE_THREADS, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(STORE_META)) {
        db.createObjectStore(STORE_META);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export function txOf(
  db: IDBDatabase,
  mode: IDBTransactionMode,
  stores: string[]
): { t: IDBTransaction; stores: IDBObjectStore[] } {
  const t = db.transaction(stores, mode);
  return { t, stores: stores.map((s) => t.objectStore(s)) };
}

export function promisify<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export function awaitTx(t: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    t.oncomplete = () => resolve();
    t.onerror = () => reject(t.error);
    t.onabort = () => reject(t.error);
  });
}
