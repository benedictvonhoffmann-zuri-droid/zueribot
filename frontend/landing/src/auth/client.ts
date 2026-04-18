import { UserManager, WebStorageStateStore, type UserManagerSettings } from "oidc-client-ts";

const ISSUER =
  import.meta.env.PUBLIC_ZITADEL_ISSUER ?? "http://localhost:8080";
const CLIENT_ID =
  import.meta.env.PUBLIC_ZITADEL_CLIENT_ID ?? "369055066948173827";

const origin = typeof window !== "undefined" ? window.location.origin : "";

const settings: UserManagerSettings = {
  authority: ISSUER,
  client_id: CLIENT_ID,
  redirect_uri: `${origin}/chat/auth/callback/`,
  post_logout_redirect_uri: `${origin}/chat/`,
  response_type: "code",
  scope: "openid profile email offline_access",
  automaticSilentRenew: true,
  loadUserInfo: true,
  userStore: new WebStorageStateStore({ store: typeof window !== "undefined" ? window.localStorage : undefined }),
};

let _userManager: UserManager | null = null;

export function getUserManager(): UserManager {
  if (!_userManager) _userManager = new UserManager(settings);
  return _userManager;
}
