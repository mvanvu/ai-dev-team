# Headless core components + swappable templates

## Contents
1. Directory layout
2. The template contract
3. Template provider (Vue / React)
4. Core component examples (Vue / React)
5. Template pack example
6. Adaptive shells
7. Enforcing the boundaries
8. Testing
9. Checks

## 1. Directory layout

```
src/
  ui/
    core/                 # stable component API — the ONLY UI import path for features
      UiButton.(vue|tsx)
      UiDialog.(vue|tsx)
      UiInput.(vue|tsx)
      UiPagination.(vue|tsx)
      UiDataList.(vue|tsx)   # list shell: filters, columns, selection, pagination, states (list-page.md)
      UiPickerInput.(vue|tsx) # input → modal with a list, single or multiple select
      useListQuery.ts       # filters/sort/page: URL query on pages (never localStorage), memory in pickers
      useColumnVisibility.ts
      pagination.ts       # paginationRange() — pure, framework-free (section 4a)
      index.ts            # public barrel
    template/
      contract.ts         # UiTemplate interface
      provider.(ts|tsx)   # provide/inject (Vue) or Context (React)
      useTemplate.ts
      useBreakpoint.ts    # media-query helper for shells
  templates/
    default/
      index.ts            # exports a UiTemplate
      tokens.css          # CSS variables scoped by [data-template="default"]
      recipes/
        button.ts
        dialog.ts
      shells/
        MobileShell.(vue|tsx)
        DesktopShell.(vue|tsx)
    index.ts              # registry: { default, brandX, ... }
  features/ …             # screens; import from '@/ui/core' only
```

## 2. The template contract

```ts
// src/ui/template/contract.ts
// Every template must implement this interface, so a missing recipe is a compile error.
import type { Component } from 'vue' // React: import type { ComponentType } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type Size = 'sm' | 'md' | 'lg'

export interface UiRecipes {
  button: (p: { variant: ButtonVariant; size: Size; block?: boolean }) => string
  input: (p: { size: Size; invalid: boolean }) => string
  dialog: { overlay: string; content: string; title: string; description: string; close: string }
  // Add one entry per core component; slots are named parts, not visual decisions.
}

export interface UiTemplate {
  name: string
  recipes: UiRecipes
  shells: { mobile: Component; desktop: Component } // React: ComponentType<{ children: ReactNode }>
  motion: UiMotion // durations, easings, springs, page transition style — see native-feel.md §10
}
```

Rules:
- Props in the contract are **semantic** (`variant`, `size`, `invalid`), never visual (`color="blue"`).
- Multi-part components expose named slots (`overlay`, `content`, …) so templates style each part.
- Changing the contract is an architecture change: update all templates in the same task.

## 3. Template provider

**Vue 3**
```ts
// src/ui/template/provider.ts
import { inject, type App, type InjectionKey, shallowRef, type ShallowRef } from 'vue'
import type { UiTemplate } from './contract'

const KEY: InjectionKey<ShallowRef<UiTemplate>> = Symbol('ui-template')

export function createUi(initial: UiTemplate) {
  const current = shallowRef(initial)
  return {
    current,
    install(app: App) {
      app.provide(KEY, current)
      document.documentElement.dataset.template = initial.name
    },
    // Runtime switch: tokens follow the data attribute, recipes follow the ref.
    use(t: UiTemplate) {
      current.value = t
      document.documentElement.dataset.template = t.name
    },
  }
}

export function useTemplate() {
  const t = inject(KEY)
  if (!t) throw new Error('UiTemplate not provided — call app.use(createUi(template))')
  return t
}
```

**React**
```tsx
// src/ui/template/provider.tsx
import { createContext, useContext, useEffect, type ReactNode } from 'react'
import type { UiTemplate } from './contract'

const Ctx = createContext<UiTemplate | null>(null)

export function UiProvider({ template, children }: { template: UiTemplate; children: ReactNode }) {
  useEffect(() => { document.documentElement.dataset.template = template.name }, [template.name])
  return <Ctx.Provider value={template}>{children}</Ctx.Provider>
}

export function useTemplate() {
  const t = useContext(Ctx)
  if (!t) throw new Error('UiTemplate not provided — wrap the app in <UiProvider>')
  return t
}
```

## 4. Core component examples

**Vue 3 + Reka UI**
```vue
<!-- src/ui/core/UiButton.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import { Primitive } from 'reka-ui'
import { useTemplate } from '@/ui/template/provider'
import type { ButtonVariant, Size } from '@/ui/template/contract'

const props = withDefaults(
  defineProps<{ variant?: ButtonVariant; size?: Size; block?: boolean; asChild?: boolean; type?: 'button' | 'submit' }>(),
  { variant: 'primary', size: 'md', block: false, asChild: false, type: 'button' },
)
const template = useTemplate()
// No visual classes here: the active template decides the look.
const cls = computed(() => template.value.recipes.button({ variant: props.variant, size: props.size, block: props.block }))
</script>

<template>
  <Primitive as="button" :as-child="asChild" :type="asChild ? undefined : type" :class="cls">
    <slot />
  </Primitive>
</template>
```

```vue
<!-- src/ui/core/UiDialog.vue -->
<script setup lang="ts">
import { DialogRoot, DialogTrigger, DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription, DialogClose } from 'reka-ui'
import { useTemplate } from '@/ui/template/provider'

defineProps<{ title: string; description?: string }>()
const open = defineModel<boolean>('open', { default: false })
const t = useTemplate()
</script>

<template>
  <DialogRoot v-model:open="open">
    <DialogTrigger as-child><slot name="trigger" /></DialogTrigger>
    <DialogPortal>
      <DialogOverlay :class="t.recipes.dialog.overlay" />
      <DialogContent :class="t.recipes.dialog.content">
        <DialogTitle :class="t.recipes.dialog.title">{{ title }}</DialogTitle>
        <DialogDescription v-if="description" :class="t.recipes.dialog.description">{{ description }}</DialogDescription>
        <slot />
        <DialogClose :class="t.recipes.dialog.close" aria-label="Close">✕</DialogClose>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
```

**React + Radix UI**
```tsx
// src/ui/core/UiButton.tsx
import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { Slot } from 'radix-ui'
import { useTemplate } from '@/ui/template/provider'
import type { ButtonVariant, Size } from '@/ui/template/contract'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant; size?: Size; block?: boolean; asChild?: boolean
}

export const UiButton = forwardRef<HTMLButtonElement, Props>(
  ({ variant = 'primary', size = 'md', block = false, asChild = false, type = 'button', className, ...rest }, ref) => {
    const t = useTemplate()
    const Comp = asChild ? Slot.Root : 'button'
    // className is accepted only for layout (margin/grid placement) from feature code, never for visuals.
    return <Comp ref={ref} type={asChild ? undefined : type} className={[t.recipes.button({ variant, size, block }), className].filter(Boolean).join(' ')} {...rest} />
  },
)
```

## 4a. Pagination (`UiPagination`)

Page numbers are never all rendered when the list is long. The control shows the first and last pages, the current page with its neighbors, and an ellipsis for each gap — e.g. `1 2 3 … 10 11 12`, `1 2 3 … 5 6 7 … 18 19 20`.

```ts
// src/ui/core/pagination.ts
export type PageItem = number | 'ellipsis-start' | 'ellipsis-end'

// Keeps the item count constant while the current page moves, so the control
// never changes width and the next/previous buttons stay under the pointer.
export function paginationRange(
  page: number, count: number, boundaryCount = 3, siblingCount = 1,
): PageItem[] {
  const range = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => a + i)
  if (count <= 2 * boundaryCount + 2 * siblingCount + 3) return range(1, count)

  const startPages = range(1, boundaryCount)
  const endPages = range(count - boundaryCount + 1, count)
  const siblingsStart = Math.max(
    Math.min(page - siblingCount, count - boundaryCount - 2 * siblingCount - 1),
    boundaryCount + 2,
  )
  const siblingsEnd = Math.min(
    Math.max(page + siblingCount, boundaryCount + 2 * siblingCount + 2),
    count - boundaryCount - 1,
  )

  return [
    ...startPages,
    // A gap of exactly one page shows that page instead of an ellipsis.
    ...(siblingsStart > boundaryCount + 2 ? ['ellipsis-start' as const] : [boundaryCount + 1]),
    ...range(siblingsStart, siblingsEnd),
    ...(siblingsEnd < count - boundaryCount - 1 ? ['ellipsis-end' as const] : [count - boundaryCount]),
    ...endPages,
  ]
}
```

| Breakpoint | `boundaryCount` | `siblingCount` | Max items | Example (page 6 of 20) |
|---|---|---|---|---|
| Desktop (`md+`) | 3 | 1 | 11 | `1 2 3 … 5 6 7 … 18 19 20` |
| Mobile | 1 | 0 | 5 | `1 … 6 … 20` |

- Defaults come from the template (`pagination: { boundaryCount, siblingCount, mobileBoundaryCount, mobileSiblingCount }` in `UiTemplate`) so a template can be denser or sparser; features pass only `page`, `pageCount` and `onPageChange`.
- Markup: `<nav aria-label="Pagination">` with a list; the current page has `aria-current="page"`; previous/next buttons with labels, disabled at the ends; ellipses are non-interactive (`aria-hidden="true"`). Optionally, when `pageCount` > ~50, a "Go to page" input.
- The current page lives in the URL (`?page=6`), so reload, share and back keep it; out-of-range values clamp to the last page.
- Vue may render it with Reka UI's `Pagination` primitives (`PaginationRoot`, `PaginationList`, `PaginationEllipsis`) as long as the items come from `paginationRange()`; React renders the items directly (Radix and React Aria have no pagination primitive).
- Unknown total (cursor pagination) → previous/next only, no page numbers. Mobile feeds prefer infinite scroll or "Load more" (`native-feel.md` §6); numbered pagination on mobile is for tables, search results and admin lists.
- Tests: unit-test `paginationRange()` for count ≤ max items (no ellipsis), current at start, middle and end, a one-page gap (number, not ellipsis), and a constant item count while the page changes.

## 5. Template pack example

```css
/* src/templates/default/tokens.css */
[data-template='default'] {
  --color-bg: oklch(0.99 0 0);
  --color-fg: oklch(0.21 0.02 260);
  --color-primary: oklch(0.55 0.2 260);
  --color-primary-fg: oklch(0.99 0 0);
  --radius-control: 0.75rem;
  --space-control-x: 1rem;
  --font-sans: 'Inter', system-ui, sans-serif;
}
@media (prefers-color-scheme: dark) {
  [data-template='default'] { --color-bg: oklch(0.18 0.02 260); --color-fg: oklch(0.96 0 0); }
}
```

```css
/* src/styles/app.css — map variables into Tailwind v4 utilities once, shared by all templates */
@import 'tailwindcss';
@theme inline {
  --color-bg: var(--color-bg);
  --color-fg: var(--color-fg);
  --color-primary: var(--color-primary);
  --color-primary-fg: var(--color-primary-fg);
  --radius-control: var(--radius-control);
}
```

```ts
// src/templates/default/recipes/button.ts
import { tv } from 'tailwind-variants'
import type { UiRecipes } from '@/ui/template/contract'

const button = tv({
  base: 'inline-flex items-center justify-center gap-2 rounded-control font-medium min-h-11 focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50 disabled:pointer-events-none',
  variants: {
    variant: {
      primary: 'bg-primary text-primary-fg',
      secondary: 'bg-fg/5 text-fg',
      ghost: 'bg-transparent text-fg hover:bg-fg/5',
      danger: 'bg-red-600 text-white',
    },
    size: { sm: 'px-3 text-sm', md: 'px-4 text-base', lg: 'px-6 text-lg' },
    block: { true: 'w-full' },
  },
})

export const buttonRecipe: UiRecipes['button'] = (p) => button(p)
```

```ts
// src/templates/default/index.ts
import './tokens.css'
import type { UiTemplate } from '@/ui/template/contract'
import { buttonRecipe } from './recipes/button'
// ...other recipes and shells
export const defaultTemplate: UiTemplate = { name: 'default', recipes: { button: buttonRecipe, /* … */ } as UiTemplate['recipes'], shells: { mobile: MobileShell, desktop: DesktopShell } }
```

Do not use `as` casts in real templates — the cast above only abbreviates the example. The point of the contract is that the compiler checks completeness.

## 6. Adaptive shells

`App` picks `template.shells.mobile` or `template.shells.desktop` via `useBreakpoint('(min-width: 1024px)')`. Shells own navigation chrome (bottom tab bar vs sidebar), safe-area padding and page width. Pages render inside the shell and never know which one is active.

## 7. Enforcing the boundaries

```js
// eslint.config.js (flat config)
export default [
  {
    files: ['src/features/**', 'src/pages/**'],
    rules: {
      'no-restricted-imports': ['error', { patterns: [
        { group: ['reka-ui', 'radix-ui', '@radix-ui/*', 'react-aria-components'], message: 'Use @/ui/core components.' },
        { group: ['motion', 'motion/*', 'motion-v', 'vaul', 'vaul-vue', 'sonner', 'vue-sonner', '@use-gesture/*', '@tanstack/vue-virtual', '@tanstack/react-virtual', '@tanstack/vue-table', '@tanstack/react-table'], message: 'Interaction libraries are wrapped by @/ui/core components.' },
        { group: ['@/templates/*', '**/templates/**'], message: 'Templates are selected via the provider only.' },
      ] }],
    },
  },
  {
    files: ['src/ui/core/**'],
    rules: {
      // Core must not depend on a specific template.
      'no-restricted-imports': ['error', { patterns: [{ group: ['@/templates/*', '**/templates/**'] }] }],
    },
  },
]
```

## 8. Testing
- Core components: Vitest + `@testing-library/vue` / `@testing-library/react`. Assert roles, keyboard behavior, emitted events/callbacks, and that the class comes from the provided template (inject a stub template with marker classes).
- Template completeness: type-check is the test. Optionally a test that mounts every core component with every registered template and checks it renders without errors.
- Visual: screenshots at 360px and 1280px per template when tooling allows.

## 9. Checks
1. No file under `src/features/` or `src/pages/` imports a headless library, an interaction library or a template; the boundary lint rules of §7 exist and pass.
2. Core components hold no visual classes, colors or spacing values; every visual comes from the active template's recipes and tokens.
3. Templates hold no behavior or business logic; a template-only task changes nothing outside `src/templates/`.
4. Every registered template implements the full `UiTemplate` contract — type-check passes with all templates.
5. A new core component has behavior tests (roles, keyboard, events) and a recipe in every template.
6. Every state in the UI spec is implemented (loading, empty, error, success, disabled; `offline` and `reconnecting` for mobile apps).
7. The screen is verified at 360px and 1280px, mobile layout written first.
