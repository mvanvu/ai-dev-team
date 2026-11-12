# Design gate: from request to an approved mockup

A mockup is the user's first look at the work. Measured runs showed every option rejected when the designer skipped the design skills, framed the wrong scope (a page around one component instead of a whole site template), or broke a layout rule the plugin owns — and the user saw it before anyone checked it. This file is the procedure for UI design mode and the `DESIGN` rule pack.

## Contents
1. Inventory first
2. Design with the skills
3. Building the options: kit, files, two stages
4. Design QA before the user sees it
5. Showing and asking
6. `DESIGN` checks

## 1. Inventory first
Before drawing anything, list what the product type needs — from the request, the domain and the platform's conventions, not from the screen that triggered the request:
- **Product type** in one line (site template for a CMS, ordering app, admin console, marketing page, …).
- **Screens / page types** it serves. A site template for a CMS: home or featured page, article, category blog and list, search results, the component pages it hosts, login and profile, 404 / error, offline / maintenance, print view if the CMS has one. An app: every tab, list, detail, form, empty and error state.
- **Chrome and regions**: header (logo, primary navigation, search, account), secondary navigation, breadcrumbs, sidebars or module positions in use, footer, notices, cookie / consent, skip links.
- **Real content per screen**: names, lengths and amounts from the domain (`REAL`), worst cases included — one content set for the whole product, reused by every mockup and by the seed data.
- **Main tasks**: the 3–5 things users do most, with the step count each option needs (`EASE`, `references/ease-of-use.md` §1); the profile's `design_taste` applies to every option.
- **Visual references**: two or three apps or sites the user likes for this product, the style they want (minimal, POS-like, editorial, playful, …) and what they do not want. When the user has none, ask whether to research comparable products first (header `References`: `Find similar apps (≈5–10 min)` / `Show mood directions now`).
  - **Research** (when the user says yes): the designer finds 4–6 comparable products with WebSearch (product sites, App Store / Google Play listings, public docs with screenshots), captures their public pages with Playwright headless through `run-heavy.sh` into `$TEAM_WS/mockups/references/` (images stay out of git), and notes per product what is worth learning — navigation, density, data presentation, palette, component style. Learn patterns only: never copy another product's logo, name, imagery or exact screens (`REAL`). Skip sites that refuse automated access.
  - **Mood directions**: 4–6 short directions (a name, palette swatch, type pair, one sample component each), each citing the references it draws on when research ran; the user picks one before any option is drawn.
- **Visible assumptions**: every choice the user will see that the request did not settle — print colours (light or dark paper), default theme, use of photos, density, tone of copy, which items show — listed as a choice with a proposed default and the domain's common practice, never decided silently.

When the request is a new product, template or app (not a change to one screen), the leader shows this inventory and the visible assumptions to the user and gets a yes before the mockups are drawn; for a smaller design task, the visible assumptions alone are asked. A missing page type found after the mockups costs a full redesign.

## 2. Design with the skills
- **Platform conventions for native apps** (Flutter, Swift / SwiftUI, Kotlin / Compose): the mockup follows the platform's design system — Material 3 on Android, Cupertino / Human Interface on iOS, or an adaptive mix the user chose — with its components (app bar, navigation bar or rail, sheets, FAB, segmented controls, native dialogs), its density and touch sizes, and adaptive layouts per `ui_sizes`: phone with bottom navigation, tablet with a navigation rail and list-detail or split panes. A layout that reads as a web page (centred column, web header and footer, hover-only affordances) fails.
- **Colour**: a palette for the product's domain (from `ui-ux-pro-max` when available) with a primary, an accent, semantic colours and neutral scales, contrast checked in light and dark; a palette of greys plus one colour fails.
- Load `ai-dev-team:ui-ux-design` (this skill) first; follow its Procedure and Visual identity steps.
- When `ui-ux-pro-max` is in the session's skill list, run it for style direction, palette, typography pairing and layout patterns of the product type, then filter the result through Visual identity. Never install it.
- Apply the packs the screens need: `REAL` and `EASE` always; `COMPACT` for every phone-sized screen; `LIST`, `PTR`, `FEEL`, `CONN` when the inventory has those screens.
- The notes list every skill called (name and what it was used for).

## 3. Building the options: kit, files, two stages
A mockup file is generated token by token, so its size is its wait: every option × every page × every preset in one file took over ten minutes before the user saw anything. Draw the choice small and the chosen option complete.
- **Stage 1 — choose a direction**: 2–3 options that differ in structure (layout, navigation, density), not only in colour, each showing only **three representative pages** of the inventory (e.g. home, one content page, the main component page) at phone and desktop width, one preset in light and dark. The user picks from this.
- **Asked for every screen at once**: when the user wants all screens mocked before choosing, the leader first gives a time estimate (from the screen count × options × themes × sizes) and offers stage 1 with three screens per option followed by every screen for the chosen option; the user decides.
- **Scope fixed before drawing**: screens, width tiers / `ui_sizes`, themes and presets are fixed in the brief before the designer starts; adding a size, theme or screen while it draws is a scope change (confirm with the user, then one revision).
- **Self-check before handing over**: the designer runs the §6 checks and the design-QA points (§4) on each option itself, fixes what fails, and records the result per option in its notes; the reviewer then confirms instead of discovering.
- **Stage 2 — build the chosen option in the project's own frontend**: when the project has a runnable frontend (profile dev / build commands; a new project runs its scaffold task first), stage 2 is real code in the project's framework and conventions — screens and components in the source tree, on the feature branch — with every page of the inventory, every state that matters and every preset the request names. Data comes through a **fake adapter**: an interface per data need (repository, service or store, in the project's pattern) with an in-memory implementation that serves the DESIGN-9 content set. The user and design QA look at the running app (web: the dev URL; Flutter: Flutter web or golden screenshots). After approval, build tasks only swap the fake adapter for the real API client and add loading, error and permission handling — the screens are not rewritten. Stage 2 code is reviewed like any code (reviewer + design QA). A project with no runnable frontend keeps stage 2 as the HTML kit below.
- **Contract from the mockup**: when the API the screens need does not exist yet, the fake adapter's interface is the draft API contract. After the user approves stage 2, the leader turns it into the plan's contract, a reviewer checks it against the server-side rules the screens cannot show (pagination and limits, `LIFE`, `QUERY`, `ABUSE`, `SEC-n`), the user hears about any change it forces on the screens, and then the server tasks build it. When the API already exists, the fake adapter implements the existing contract and the screens adapt to it.
- **Kit first, screens as data**: the designer first builds a small component kit for the option — tokens plus the 10–15 components the inventory needs (header, navigation, card, list row, form field, button, sheet, empty and error states) — then composes every screen from the kit as data. No screen re-declares markup or styles the kit already has. Most of the drawing time is output tokens, so this is the main speed lever.
- **Small files, edits not rewrites**: a mockup is a folder `$TEAM_WS/mockups/<name>/` — `index.html` (shell with switchers for option, screen, size, theme and preset), `kit.css` / `kit.js` (the kit), one `screens/<screen>.js` per screen (content as data). Revisions use Edit on the kit file or the screen file concerned; never rewrite the whole mockup. Drafts stay out of the rest of the repo (`.superpowers/` included). The approved option is copied to `mockup_dir` as its folder.
- **Stage 2 in parallel**: once the user has picked and the kit is frozen, the leader splits the remaining screens into 2–3 groups (sign-in, lists, detail, settings, …) and spawns one developer per group within `max_agents`, groups owning disjoint screen files with the shared kit / components owned by one of them. An HTML-kit stage 2 runs on `model: "sonnet"`; a stage 2 in the project's frontend is production code and runs on the model the table gives a client task. A kit change during stage 2 goes through the leader to every designer. One design QA covers all groups together.
- **Light sweep in stage 1**: contact sheets at one phone size and the widest size, light and dark; every size, theme and preset only in stage 2.
- Each option already satisfies every check in §6; options never trade a rule away.
- Next to the mockup: one contact sheet per option from `overflow-check.mjs --sheet` (stage 1: one phone size and the widest, light and dark; stage 2: every size, theme and preset).

## 4. Design QA before the user sees it
- The leader sends the HTML and sheets to a fresh `reviewer` (`model: "sonnet"`) in design QA mode: inventory complete (§1), domain conventions and real content (`REAL`), main tasks walked as a new user with their step counts (`EASE`), no wasted space or overflow (`COMPACT`), contrast, states. Verdict per option: `pass` or the failing check IDs with the cell.
- Design QA also checks the user's visual references, platform conventions for native apps and the palette (`DESIGN-11`).
- Design QA covers every width tier (`ui_widths`, or `ui_sizes` for Flutter / native) and every theme in the profile's `ui_themes`; an option missing a theme or tier fails.
- A failing option is fixed by the designer or dropped before the user sees anything. At least one option must pass; otherwise the designer reworks and QA runs again (this is not a fix round of a build task).

## 5. Showing and asking
- Open the HTML for the user (`xdg-open` on Linux, `open` on macOS, or a local static server with the URL) and give its absolute path. The leader looking at screenshots is not the user seeing the mockup.
- Then ask with AskUserQuestion: one option per mockup option, each with its one-line idea; the user can also ask for changes. Build tasks start only after the user picks an option.
- **Keep the approved mockup**: when the user picks, copy that option (the HTML reduced to it, plus its contact sheets) to the profile's `mockup_dir` in the repo, named after the feature, and write that path into the UI spec and the build tasks' notes so later changes compare against it. `mockup_dir: none` → nothing goes into the repo. Drafts and rejected options stay in `$TEAM_WS/mockups/`.

## 6. `DESIGN` checks
1. **Inventory** — the product type, every page type and chrome region it needs, real content per screen and the visible assumptions were listed before drawing; the user confirmed the assumptions (and, for a new product, template or app, the whole list).
2. **Skills used** — `ai-dev-team:ui-ux-design` was loaded, and `ui-ux-pro-max` was run when it was available; the notes name them.
3. **Kit, files, two stages** — stage 1 options live in `$TEAM_WS/mockups/<name>/` as a component kit plus one data file per screen, revised by edits; stage 2 is built in the project's frontend with a fake data adapter when the project has one, otherwise as the HTML kit; stage 1 shows three representative pages per option at phone and desktop width, light and dark; stage 2 shows every inventory page and requested preset for the chosen option only; no draft was written into the repo.
4. **Rules hold in every option** — every option passes `REAL` and `EASE` and, for phone-sized screens, `COMPACT`; contact sheets sit beside the HTML.
5. **QA before the user** — a design QA reviewer passed at least one option, and failing options were fixed or dropped before the user saw them.
6. **User saw it** — the HTML was opened for the user with its path before the choice was asked.
7. **Approved mockup kept** — the picked stage-1 option (and an HTML-kit stage 2) was copied to `mockup_dir` (unless `none`); a stage 2 built in the project's frontend is kept as the code itself and its path is in the UI spec and the build tasks' notes.
8. **Drawn in UI design mode** — visual mockups came from a developer in UI design mode under this gate, never drawn by the leader inside brainstorming; brainstorming showed at most low-fidelity layout or flow sketches.
9. **One content set** — every mockup of one product draws from one content set (names, categories, items, amounts), recorded with the inventory and reused as the seed data.
10. **Self-checked** — the designer's notes hold a per-option result of the §6 checks and the design-QA points, run before handing over.
11. **Taste and platform** — the user's visual references, or the researched products (when the user asked for research) and the chosen mood, are recorded and followed; native-app mockups follow the platform design system and adaptive layouts for every size tier, with nothing that reads as a web page; the palette has primary, accent, semantic and neutral colours with checked contrast.
