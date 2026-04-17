import type { Locale } from './locales';
import { de } from './translations/de';
import { en } from './translations/en';

const translations = { zh: de, en } as const;

export function useTranslations(locale: Locale) {
  return translations[locale];
}

export function getLocalePath(locale: Locale, path = '') {
  const clean = path.replace(/^\//, '');
  return `/${locale}/${clean}`;
}
