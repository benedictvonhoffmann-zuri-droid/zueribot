import { useEffect, useState } from "react";

export type Prefs = {
  location?: { lat: number; lng: number; label?: string };
};

const KEY = "bunzli.prefs.v1";

const DEFAULTS: Prefs = {};

function load(): Prefs {
  if (typeof localStorage === "undefined") return DEFAULTS;
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS;
  } catch {
    return DEFAULTS;
  }
}

function save(p: Prefs) {
  try {
    localStorage.setItem(KEY, JSON.stringify(p));
  } catch {}
}

export function usePrefs(): [Prefs, (patch: Partial<Prefs>) => void] {
  const [prefs, setPrefs] = useState<Prefs>(DEFAULTS);
  useEffect(() => {
    setPrefs(load());
  }, []);
  useEffect(() => {
    save(prefs);
  }, [prefs]);
  return [prefs, (patch) => setPrefs((p) => ({ ...p, ...patch }))];
}

export function buildContextBlock(p: Prefs): string {
  const parts: string[] = [];
  if (p.location) {
    const loc = p.location.label
      ? `${p.location.label} (${p.location.lat.toFixed(4)}, ${p.location.lng.toFixed(4)})`
      : `${p.location.lat.toFixed(4)}, ${p.location.lng.toFixed(4)}`;
    parts.push(`Der Benutzer befindet sich bei: ${loc}. Nutze diese Info für ortsrelevante Antworten.`);
  }
  if (!parts.length) return "";
  return `<user_context>\n${parts.join("\n")}\n</user_context>`;
}
