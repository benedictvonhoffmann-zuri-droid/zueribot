export const LOCALES = ['zh', 'en'] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = 'en';

export const LOCALE_META: Record<Locale, { label: string; htmlLang: string; flag: string }> = {
  zh: { label: 'Züridütsch', htmlLang: 'gsw',   flag: '🦁' },
  en: { label: 'English',    htmlLang: 'en-GB', flag: '🇬🇧' },
};
