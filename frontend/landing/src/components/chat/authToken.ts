// Bridge between the React AuthProvider and the plain-JS adapters
// (adapter.ts, threads.ts) which can't use hooks. The provider wires
// a getter on mount; adapters call it synchronously before each fetch.

let getter: (() => string | null) | null = null;

export function setAuthTokenGetter(g: (() => string | null) | null) {
  getter = g;
}

export function getAccessToken(): string | null {
  return getter?.() ?? null;
}
