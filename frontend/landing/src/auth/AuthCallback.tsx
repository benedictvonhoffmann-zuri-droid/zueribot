import { useEffect, useState } from "react";
import { getUserManager } from "./client";

export default function AuthCallback() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        await getUserManager().signinRedirectCallback();
        window.location.replace("/chat/");

      } catch (err) {
        console.error("OIDC callback error", err);
        setError(String((err as Error)?.message ?? err));
      }
    })();
  }, []);

  if (error) {
    return (
      <div className="p-8 text-[14px] text-zurich-dark">
        Aamäldig fählgschlage: <code className="text-red-600">{error}</code>
        <div className="mt-3"><a className="text-zurich-blue underline" href="/chat/">Zrugg zum Chat</a></div>
      </div>
    );
  }
  return <div className="text-[14px] text-zurich-gray">Aamäldig wird abgschlosse…</div>;
}
