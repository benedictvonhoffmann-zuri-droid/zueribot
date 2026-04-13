import type { Locale } from './locales';
import { de } from './translations/de';
import { en } from './translations/en';
import { fr } from './translations/fr';
import { it } from './translations/it';
import { zh } from './translations/zh';

const translations = { de, en, fr, it, zh } as const;

export function useTranslations(locale: Locale) {
  return translations[locale];
}

export function getLocalePath(locale: Locale, path = '') {
  const clean = path.replace(/^\//, '');
  return `/${locale}/${clean}`;
}
