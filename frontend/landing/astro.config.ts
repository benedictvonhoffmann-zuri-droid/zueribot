import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://buenzli.space',
  output: 'static',
  trailingSlash: 'always',
  vite: {
    plugins: [tailwindcss()],
  },
  integrations: [
    sitemap({
      filter: (page) => !page.includes('/design-system/'),
      i18n: {
        defaultLocale: 'zh',
        locales: {
          zh: 'gsw',
          en: 'en-GB',
        },
      },
    }),
  ],
});
