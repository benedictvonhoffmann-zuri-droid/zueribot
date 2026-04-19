import { en } from '../src/i18n/translations/en.ts';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const API_KEY = process.env.SUPERTEXT_KEY;
if (!API_KEY) {
  console.error('Missing SUPERTEXT_KEY env var');
  process.exit(1);
}

type Entry = { path: string; value: string };
const entries: Entry[] = [];

function walk(obj: unknown, prefix: string): void {
  if (typeof obj === 'string') {
    entries.push({ path: prefix, value: obj });
  } else if (Array.isArray(obj)) {
    obj.forEach((v, i) => walk(v, `${prefix}[${i}]`));
  } else if (obj && typeof obj === 'object') {
    for (const k of Object.keys(obj as Record<string, unknown>)) {
      walk((obj as Record<string, unknown>)[k], prefix ? `${prefix}.${k}` : k);
    }
  }
}
walk(en, '');

function shouldSkip(e: Entry): boolean {
  if (e.path.endsWith('.emoji')) return true;
  if (e.value.trim() === '') return true;
  // numeric-only / punctuation-only values that shouldn't be translated
  if (/^[\s0-9.,:\-+×·°%/€$£]+$/.test(e.value)) return true;
  // preserve proper nouns that are the same in any language
  if (['Bünzli', 'Zürich', 'Züri', 'Paradeplatz', 'Bahnhofstrasse'].includes(e.value.trim())) return true;
  return false;
}

const toTranslate = entries.filter(e => !shouldSkip(e));
console.log(`Translating ${toTranslate.length} / ${entries.length} strings`);

const CHUNK_LIMIT = 9000;
const batches: Entry[][] = [];
let current: Entry[] = [];
let currentLen = 0;
for (const e of toTranslate) {
  const len = e.value.length + 10;
  if (currentLen + len > CHUNK_LIMIT && current.length) {
    batches.push(current);
    current = [];
    currentLen = 0;
  }
  current.push(e);
  currentLen += len;
}
if (current.length) batches.push(current);
console.log(`→ ${batches.length} batches`);

const results: Record<string, string> = {};
for (let i = 0; i < batches.length; i++) {
  const batch = batches[i];
  const text = batch.map(e => e.value);
  process.stdout.write(`  batch ${i + 1}/${batches.length} (${batch.length} strings)… `);
  const resp = await fetch('https://api.supertext.com/v1/translate/ai/text', {
    method: 'POST',
    headers: {
      'Authorization': `Supertext-Auth-Key ${API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ source_lang: 'en', target_lang: 'gsw-u-sd-chzh', text }),
  });
  if (!resp.ok) {
    console.error('\nHTTP', resp.status, await resp.text());
    process.exit(1);
  }
  const data = (await resp.json()) as { translated_text: string[] };
  if (!Array.isArray(data.translated_text) || data.translated_text.length !== batch.length) {
    console.error('\nshape mismatch:', JSON.stringify(data).slice(0, 500));
    process.exit(1);
  }
  batch.forEach((e, j) => { results[e.path] = data.translated_text[j]; });
  console.log('ok');
}

const mapping: Record<string, string> = {};
for (const e of entries) {
  mapping[e.path] = results[e.path] ?? e.value;
}

const __filename = fileURLToPath(import.meta.url);
const outPath = path.join(path.dirname(__filename), 'translate-zh.raw.json');
await fs.writeFile(outPath, JSON.stringify(mapping, null, 2) + '\n');
console.log(`Wrote ${Object.keys(mapping).length} entries → ${outPath}`);
