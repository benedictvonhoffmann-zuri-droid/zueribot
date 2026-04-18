import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { User } from "oidc-client-ts";
import { getUserManager } from "./client";

type AuthState =
  | { status: "loading" }
  | { status: "anonymous" }
  | { status: "authenticated"; user: User };

type AuthCtx = {
  state: AuthState;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => string | null;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });
  const userRef = useRef<User | null>(null);

  useEffect(() => {
    const um = getUserManager();

    const applyUser = (u: User | null) => {
      userRef.current = u && !u.expired ? u : null;
      setState(userRef.current ? { status: "authenticated", user: userRef.current } : { status: "anonymous" });
    };

    um.getUser().then(applyUser).catch(() => applyUser(null));

    const onLoaded = (u: User) => applyUser(u);
    const onUnloaded = () => applyUser(null);
    const onExpired = () => applyUser(null);

    um.events.addUserLoaded(onLoaded);
    um.events.addUserUnloaded(onUnloaded);
    um.events.addAccessTokenExpired(onExpired);

    return () => {
      um.events.removeUserLoaded(onLoaded);
      um.events.removeUserUnloaded(onUnloaded);
      um.events.removeAccessTokenExpired(onExpired);
    };
  }, []);

  const value = useMemo<AuthCtx>(() => ({
    state,
    login: () => getUserManager().signinRedirect(),
    logout: () => getUserManager().signoutRedirect(),
    getAccessToken: () => userRef.current?.access_token ?? null,
  }), [state]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used inside AuthProvider");
  return c;
}
