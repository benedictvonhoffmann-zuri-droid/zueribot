// AES-GCM encryption of IndexedDB payloads with a key stored in localStorage.
// Protects on-disk chat history against casual access by other apps or
// browser forensics tooling that reads LevelDB files directly.

const KEY_STORAGE = "bunzli.key.v1";

let keyPromise: Promise<CryptoKey> | null = null;

async function loadOrCreateKey(): Promise<CryptoKey> {
  const existing = localStorage.getItem(KEY_STORAGE);
  if (existing) {
    try {
      const jwk = JSON.parse(existing);
      return await crypto.subtle.importKey(
        "jwk",
        jwk,
        { name: "AES-GCM", length: 256 },
        true,
        ["encrypt", "decrypt"]
      );
    } catch {
      // fall through to regenerate
    }
  }
  const key = await crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"]
  );
  const jwk = await crypto.subtle.exportKey("jwk", key);
  localStorage.setItem(KEY_STORAGE, JSON.stringify(jwk));
  return key;
}

function getKey(): Promise<CryptoKey> {
  if (!keyPromise) keyPromise = loadOrCreateKey();
  return keyPromise;
}

export type Ciphertext = { iv: Uint8Array; data: Uint8Array };

export async function encryptJson(value: unknown): Promise<Ciphertext> {
  const key = await getKey();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const plaintext = new TextEncoder().encode(JSON.stringify(value));
  const ctBuf = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    plaintext
  );
  return { iv, data: new Uint8Array(ctBuf) };
}

export async function decryptJson<T>(ct: Ciphertext): Promise<T> {
  const key = await getKey();
  const buf = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: ct.iv },
    key,
    ct.data
  );
  const text = new TextDecoder().decode(buf);
  return JSON.parse(text) as T;
}

export function clearKey() {
  keyPromise = null;
  localStorage.removeItem(KEY_STORAGE);
}
