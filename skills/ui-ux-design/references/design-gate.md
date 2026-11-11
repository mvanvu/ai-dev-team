# Design gate: from request to an approved mockup

A mockup is the user's first look at the work. Measured runs showed every option rejected when the designer skipped the design skills, framed the wrong scope (a page around one component instead of a whole site template), or broke a layout rule the plugin owns — and the user saw it before anyone checked it. This file is the procedure for UI design mode and the `DESIGN` rule pack.

## Contents
1. Inventory first
2. Design with the skills
3. One file of options
4. Design QA before the user sees it
5. Showing and asking
6. `DESIGN` checks

## 1. Inventory first
Before drawing anything, list what the product type needs — from the request, the domain and the platform's conventions, not from the screen that triggered the request:
- **Product type** in one line (site template for a CMS, ordering app, admin console, marketing page, …).
- **Screens / page types** it serves. A site template for a CMS: home or featured page, article, category blog and list, search results, the component pages it hosts, login and profile, 404 / error, offline / maintenance, print view if the CMS has one. An app: every tab, list, detail, form, empty and error state.
- **Chrome and regions**: header (logo, primary navigation, search, account), secondary navigation, breadcrumbs, sidebars or module positions in use, footer, notices, cookie / consent, skip links.
- **Real content per screen**: names, lengths and amounts from the domain (`REAL`), worst cases included.
- **Visible assumptions**: every choice the user will see that the request did not settle — print colours (light or dark paper), default theme, use of photos, density, tone of copy, which items show — listed as a choice with a proposed default and the domain's common practice, never decided silently.

When the request is a new product, template or app (not a change to one screen), the leader shows this inventory and the visible assumptions to the user and gets a yes before the mockups are drawn; for a smaller design task, the visible assumptions alone are asked. A missing page type found after the mockups costs a full redesign.

## 2. Design with the skills
- Load `ai-dev-team:ui-ux-design` (this skill) first; follow its Procedure and Visual identity steps.
- When `ui-ux-pro-max` is in the session's skill list, run it for style direction, palette, typography pairing and layout patterns of the product type, then filter the result through Visual identity. Never install it.
- Apply the packs the screens need: `REAL` always; `COMPACT` for every phone-sized screen; `LIST`, `PTR`, `FEEL`, `CONN` when the inventory has those screens.
- The notes list every skill called (name and what it was used for).

## 3. One file of options, in two stages
A mockup file is generated token by token, so its size is its wait: every option × every page × every preset in one file took over ten minutes before the user saw anything. Draw the choice small and the chosen option complete.
- **Stage 1 — choose a direction**: 2–3 options that differ in structure (layout, navigation, density), not only in colour, each showing only **three representative pages** of the inventory (e.g. home, one content page, the main component page) at phone and desktop width, one preset in light and dark. The user picks from this.
- **Stage 2 — complete the chosen option**: after the pick, the chosen option only, now with every page of the inventory, every state that matters and every preset the request names. Design QA (§4) runs again on it before the build starts.
- **Build the file small**: one self-contained HTML at `$TEAM_WS/mockups/<name>.html` while it is a draft — never in the repo (`.superpowers/` included) — with shared CSS and tokens once, page content written as data (a small script or `<template>` that renders each page per option and preset), a switcher for option, page, width, light/dark and preset. Never copy the same markup per option or per preset.
- Each option already satisfies every check in §6; options never trade a rule away.
- Next to the HTML: one contact sheet per option from `overflow-check.mjs --sheet` at the profile's phone widths and the widest width, light and dark.

## 4. Design QA before the user sees it
- The leader sends the HTML and sheets to a fresh `reviewer` (`model: "sonnet"`) in design QA mode: inventory complete (§1), domain conventions and real content (`REAL`), no wasted space or overflow (`COMPACT`), contrast, states. Verdict per option: `pass` or the failing check IDs with the cell.
- A failing option is fixed by the designer or dropped before the user sees anything. At least one option must pass; otherwise the designer reworks and QA runs again (this is not a fix round of a build task).

## 5. Showing and asking
- Open the HTML for the user (`xdg-open` on Linux, `open` on macOS, or a local static server with the URL) and give its absolute path. The leader looking at screenshots is not the user seeing the mockup.
- Then ask with AskUserQuestion: one option per mockup option, each with its one-line idea; the user can also ask for changes. Build tasks start only after the user picks an option.
- **Keep the approved mockup**: when the user picks, copy that option (the HTML reduced to it, plus its contact sheets) to the profile's `mockup_dir` in the repo, named after the feature, and write that path into the UI spec and the build tasks' notes so later changes compare against it. `mockup_dir: none` → nothing goes into the repo. Drafts and rejected options stay in `$TEAM_WS/mockups/`.

## 6. `DESIGN` checks
1. **Inventory** — the product type, every page type and chrome region it needs, real content per screen and the visible assumptions were listed before drawing; the user confirmed the assumptions (and, for a new product, template or app, the whole list).
2. **Skills used** — `ai-dev-team:ui-ux-design` was loaded, and `ui-ux-pro-max` was run when it was available; the notes name them.
3. **One file, two stages** — the options are in one self-contained HTML in `$TEAM_WS/mockups/` built from shared CSS and page data; stage 1 shows three representative pages per option at phone and desktop width, light and dark; stage 2 shows every inventory page and requested preset for the chosen option only; no draft was written into the repo.
4. **Rules hold in every option** — every option passes `REAL` and, for phone-sized screens, `COMPACT`; contact sheets sit beside the HTML.
5. **QA before the user** — a design QA reviewer passed at least one option, and failing options were fixed or dropped before the user saw them.
6. **User saw it** — the HTML was opened for the user with its path before the choice was asked.
7. **Approved mockup kept** — the picked option was copied to `mockup_dir` (unless `none`) and its path is in the UI spec and the build tasks' notes.
