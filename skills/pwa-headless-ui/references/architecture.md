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

## 1. Directory layout

```
src/
  ui/
    core/                 # stable component API — the ONLY UI import path for features
      UiButton.(vue|tsx)
      UiDialog.(vue|tsx)
      UiInput.(vue|tsx)
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
        { group: ['motion', 'motion/*', 'motion-v', 'vaul', 'vaul-vue', 'sonner', 'vue-sonner', '@use-gesture/*', '@tanstack/vue-virtual', '@tanstack/react-virtual'], message: 'Interaction libraries are wrapped by @/ui/core components.' },
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
