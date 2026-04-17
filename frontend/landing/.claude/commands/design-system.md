# Bünzli Design System Reference

Invoked as `/design-system` within `frontend/landing/`.  
Visual showcase: `/design-system/` (noindex page).

---

## Color Tokens

| Token | Value | Use |
|---|---|---|
| `zurich-blue` | `#0070B4` | Primary CTA, links, accents |
| `zurich-blue-dark` | `#00407C` | Hover state of primary |
| `zurich-blue-light` | `#EDF5FA` | Tinted backgrounds |
| `zurich-navy` | `#08111F` | Dark section backgrounds |
| `badi-orange` | `#F26522` | Secondary CTA |
| `badi-orange-dark` | `#D4541A` | Hover state of secondary |
| `tram-green` | `#3D8A3E` | Success, live indicators |
| `zurich-dark` | `#1A1A1A` | Body text |
| `zurich-gray` | `#6B7280` | Muted text, labels |
| `zurich-border` | `#E5E7EB` | Default borders |
| `zh-black-100` | `#000000` | ZH gray scale (formal) |
| `zh-black-90` | `#1A1A1A` | — |
| `zh-black-80` | `#333333` | — |
| `zh-black-60` | `#666666` | — |
| `zh-black-40` | `#999999` | — |
| `zh-black-20` | `#CCCCCC` | — |
| `zh-black-10` | `#E5E5E5` | — |
| `zh-black-5` | `#F7F7F7` | Page/section background |
| `zh-success` | `#1A7F1F` | Semantic success |
| `zh-error` | `#D93C1A` | Semantic error |

**Rules:**
- Never use Tailwind's `gray-*` scale — use `zh-black-*` instead.
- Never use bracket opacity like `/[0.04]` — use `/5`, `/10`, `/20` etc.
- Section backgrounds: `bg-white` (primary) or `bg-zh-black-5` (alternate). Never `bg-gray-50`.
- Dark sections: `bg-zurich-navy`. Never inline `style="background: hsl(...)"`.

---

## Shadow Tokens

| Token | Use |
|---|---|
| `shadow-short` | Hover lift on cards and buttons |
| `shadow-regular` | Cards, panels, popovers |
| `shadow-long` | Modals, dropdowns, overlays |

---

## Components

All in `src/components/ui/`.

### `Button.astro`

```astro
import Button from '../components/ui/Button.astro';

<!-- Link button -->
<Button href="/path" variant="primary" size="lg">Label</Button>

<!-- Action button -->
<Button type="submit" variant="outline" size="sm">Submit</Button>
```

| Prop | Type | Default | Options |
|---|---|---|---|
| `href` | `string?` | — | if set, renders `<a>` |
| `variant` | `string` | `primary` | `primary` `secondary` `outline` `ghost` |
| `size` | `string` | `md` | `sm` `md` `lg` |
| `type` | `string` | `button` | `button` `submit` `reset` |
| `disabled` | `boolean` | `false` | — |
| `class` | `string?` | — | extra Tailwind classes |

Variants: `primary` = blue, `secondary` = orange, `outline` = blue border, `ghost` = text only.

### `Badge.astro`

```astro
import Badge from '../components/ui/Badge.astro';

<Badge variant="blue">Open Source</Badge>
<Badge variant="green" count={12}>Connectors</Badge>
```

| Prop | Type | Default | Options |
|---|---|---|---|
| `variant` | `string` | `blue` | `blue` `green` `orange` `gray` |
| `count` | `string \| number?` | — | appended in monospace |

### `Card.astro`

```astro
import Card from '../components/ui/Card.astro';

<Card variant="blue-tint" padding="lg" hover>
  Content here
</Card>
```

| Prop | Type | Default | Options |
|---|---|---|---|
| `variant` | `string` | `default` | `default` `blue-tint` `dark` |
| `padding` | `string` | `md` | `sm` `md` `lg` |
| `hover` | `boolean` | `false` | adds hover shadow + border transition |

Use `dark` variant inside `bg-zurich-navy` sections only.

### `Pill.astro`

```astro
import Pill from '../components/ui/Pill.astro';

<!-- KB topic -->
<Pill emoji="🏠" label="Miete" count="47" tooltip="Rental law..." />

<!-- Connector (dashed = coming soon) -->
<Pill emoji="🔍" label="Web Search" dashed />
```

| Prop | Type | Default |
|---|---|---|
| `emoji` | `string?` | — |
| `label` | `string` | required |
| `count` | `string \| number?` | — |
| `tooltip` | `string?` | maps to `title` attr |
| `dashed` | `boolean` | `false` |

### `SectionHeader.astro`

```astro
import SectionHeader from '../components/ui/SectionHeader.astro';

<SectionHeader
  eyebrow="Use cases"
  heading="Was chasch du frage?"
  subtext="Alles rund um Zürich."
  align="center"
  theme="light"
/>

<!-- Dark section with custom heading markup -->
<SectionHeader eyebrow="Dateschutz" heading="" theme="dark">
  <span slot="heading">
    Dini Date ghöre dir.
    <br />
    <span class="text-white/50">Immer.</span>
  </span>
</SectionHeader>
```

| Prop | Type | Default | Options |
|---|---|---|---|
| `eyebrow` | `string?` | — | mono uppercase label above heading |
| `heading` | `string` | required | pass empty string when using slot |
| `subtext` | `string?` | — | paragraph below heading |
| `align` | `string` | `center` | `center` `left` |
| `theme` | `string` | `light` | `light` `dark` |

Use `slot="heading"` for headings with mixed colors or line breaks.

---

## Section Backgrounds

| Section | Background |
|---|---|
| Hero | `bg-white` |
| Scenarios | `bg-white` |
| How It Works | `bg-zh-black-5` |
| Privacy | `bg-zurich-navy` |
| Community | `bg-white` |

Alternate white and `bg-zh-black-5` to create visual rhythm without heavy borders.

---

## Naming Conventions

- Color aliases → always use token names (`zurich-blue`), never raw hex in Tailwind classes.
- Opacity → always `/5`, `/10`, `/20`, `/30`, `/40`, `/50`, `/60`, `/70`, `/80`, `/90`. Never bracket syntax.
- Gray shades → always `zh-black-*`. Never `gray-*`, `slate-*`, `neutral-*`.
- Sections → always use `<SectionHeader>` for the eyebrow + heading + subtext trio.
- CTAs → always use `<Button>` for actionable links and form actions.
- Tags/chips → `<Pill>` for KB topics and connectors; `<Badge>` for status labels.
- Cards → `<Card>` replaces raw `rounded-xl border p-6` patterns.
