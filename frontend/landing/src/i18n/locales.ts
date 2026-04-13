export const LOCALES = ['de', 'en', 'fr', 'it', 'zh'] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = 'de';

export const LOCALE_META: Record<Locale, { label: string; htmlLang: string; flag: string }> = {
  de: { label: 'Deutsch',    htmlLang: 'de-CH', flag: '🇩🇪' },
  en: { label: 'English',    htmlLang: 'en-GB', flag: '🇬🇧' },
  fr: { label: 'Français',   htmlLang: 'fr-CH', flag: '🇫🇷' },
  it: { label: 'Italiano',   htmlLang: 'it-CH', flag: '🇮🇹' },
  zh: { label: 'Züridütsch', htmlLang: 'gsw',   flag: '🦁' },
};
