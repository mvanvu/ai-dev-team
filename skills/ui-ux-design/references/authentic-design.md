# Authentic design: no "AI-generated" look

**Rule:** every screen should look like it was designed by a team that knows the product and its users — not assembled from generic defaults. Users notice generated design within seconds: it reads as untrustworthy and unfinished. This applies to app screens, template packs and marketing pages alike.

## Contents
1. Why generated design is recognizable
2. Tells to remove
3. What makes a design feel real
4. Process
5. Checks

## 1. Why generated design is recognizable
Generated design averages every product it has seen, so it lands on the same safe choices: centered symmetric layouts, the same rounded card, decorative gradients, an icon for every heading, and copy that could describe any product. Nothing in it comes from this product's users, data or workflow. Authenticity comes from specifics: real content shapes, the domain's own conventions, and choices that a generic product would not make.

## 2. Tells to remove
Unless the brief explicitly asks for them:
- **Color**: purple-to-blue or multi-stop decorative gradients; gradient text; glowing borders and neon shadows; a different accent color per card; glassmorphism (`backdrop-blur`) on ordinary surfaces.
- **Surfaces**: every block in an identical rounded card with the same soft shadow; cards nested in cards; one large radius on everything regardless of size.
- **Layout**: centered hero + three-column feature grid on app screens; perfectly symmetric grids where the content is not symmetric; big empty bands of whitespace on dense, task-focused screens.
- **Icons and decoration**: an icon on every heading, label and button; emoji used as UI icons; icons mixed from several sets or stroke widths; decorative blobs, sparkles, abstract 3D shapes, stock illustrations with no meaning.
- **Typography**: ALL-CAPS eyebrow labels above every heading; one accented word in a headline; display fonts on functional screens; the same font size and weight for everything inside a card.
- **Copy**: "Welcome back, John!", "Supercharge your workflow", "Seamless", "Unlock", "Effortless"; lorem ipsum, "John Doe", "Acme" (use real-looking names and content instead; placeholder and seed email addresses still use reserved domains such as `example.com` — that is correct, not a tell); round, fake-perfect numbers (`$12,345`, `99.9%`, `+12.5%` on every tile); explanatory sentences under every title; tooltips and helper text that repeat the label.
- **Dashboards**: rows of identical stat tiles with sparklines and green up-arrows that answer no question the user has.
- **Motion**: fade-up on every element on load; hover lifts on non-interactive cards; ambient floating animations.

## 3. What makes a design feel real
1. **Start from real content.** Design with the product's actual data shapes: real field names, long and short values, missing values, realistic counts and amounts, real statuses. Lay out what the user actually reads first.
2. **Follow the domain's conventions.** Look at how established products in the same domain present the same data (a POS order ticket, a bank statement, a delivery tracker, a medical record) and the platform's own patterns (iOS Human Interface Guidelines, Material 3). Familiar beats clever.
3. **Hierarchy by frequency of use.** The most frequent action is the most prominent; rare actions go into menus. Not every element gets equal weight or a card.
4. **Density that fits the task.** Operational screens (lists, tickets, tables, forms) are dense and scannable; only onboarding and marketing breathe. On phones, follow `ai-dev-team:pwa-headless-ui` → `references/compact-layout.md`.
5. **Restrained palette with meaning.** One neutral scale, one brand color, semantic colors (success, warning, danger, info) used only for state. Color marks state and action, not decoration.
6. **One type family, tuned.** One family (two at most, with clear roles), a short scale, weights doing the hierarchy work, tabular numbers for amounts and times.
7. **Consistent, sparse iconography.** One icon set, one stroke width, icons only where they speed recognition (navigation, frequent actions, statuses).
8. **Copy in the product's voice.** Short, specific labels using the users' own terms ("Table 12 · 4 guests", not "Table entity #12"); verbs on buttons; no marketing tone inside the app; no instructions the UI should make unnecessary.
9. **Real states.** Empty, loading, error, partial and long-content states designed with real wording — an empty state says what to do next in one line, not a paragraph with an illustration.
10. **Purposeful detail.** A few precise details that show care (aligned numbers, correct plurals, sensible truncation, real timestamps like "2 min ago") beat decoration.

## 4. Process
1. Before designing, write down: who uses the screen, on which device, in what situation (standing at a counter, one hand, glare), and the 1–3 jobs the screen does.
2. Collect 2–3 reference products from the same domain and note the conventions to keep.
3. Build the wireframe with real or realistic data, including the longest and emptiest cases.
4. Review the result against §2; for each tell found, remove it or write why this product needs it.
5. Ask: "Would this screen look the same for any other product?" If yes, it is not specific enough.

## 5. Checks
1. No tell from §2 remains without a written reason in the UI spec.
2. Screens are built with realistic domain data (no lorem ipsum, "John Doe", "Acme", fake-perfect numbers) in specs, prototypes, seed data and screenshots; email addresses in them use reserved domains (`example.com`, `example.org`, RFC 2606).
3. Layout, density and hierarchy follow the domain's conventions and the frequency of use; on phones, `compact-layout.md` applies.
4. Palette: neutrals + one brand color + semantic state colors; no decorative gradients, gradient text or glows.
5. One icon set with one stroke width; icons only where they aid recognition; no emoji as UI icons.
6. Copy is short, specific and in the users' terms; no marketing tone inside the app; no instruction text the UI could make unnecessary.
7. Motion is user-triggered and purposeful; no load-in animation on every element, no hover lift on non-interactive cards.
