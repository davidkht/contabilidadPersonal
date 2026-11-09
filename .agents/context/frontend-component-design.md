# Frontend component design

Portable conventions for the **component layer** in Vite + React apps. Covers
presentational and container components, props contracts, composition, styling,
and accessibility — not routing, global state, or data fetching.

Related context:

| Document | Focus |
| -------- | ----- |
| **`.agents/context/frontend-architecture.md`** | Folder tree for **this** project (`--fs layered` or `per-domain`) |
| **`.agents/context/frontend-state-design.md`** | Stores, server state, API clients |
| `docs/COMPONENT_DESIGN.md` | Project-specific overrides when present |

When project `docs/` files are missing, infer from **live components** under `src/`.
Paths for pages, components, and features live in **frontend-architecture.md**.

---

## Role of the component layer

Components are the **UI surface**: they render, compose, and accept user input.
They do **not** own network calls, cache keys, or global stores. A component
may *read* state through props or a thin hook; it must not become the place
where fetch/cache policy lives.

| Piece | Responsibility | Must **not** do |
| ----- | -------------- | --------------- |
| **Presentational** | Markup, layout, variants, a11y. Props in, events out. | Fetch, write to a global store, know route params. |
| **Container / page** | Wire a route or feature to presentational children. Pass data and callbacks down. | Duplicate presentational markup; call APIs inline in JSX. |
| **Shared primitives** | Buttons, inputs, dialogs, layout shells reused across features. | Encode feature-specific business rules. |

---

## Folder conventions

Physical paths (`src/components` vs `src/features/<domain>/ui`) live in
**`.agents/context/frontend-architecture.md`**. Colocate a component with its
styles, tests, and small helpers. Name files after the exported component
(`UserCard.tsx` exports `UserCard`).

---

## Props and typing

- Props are the **public contract**. Prefer explicit typed props over
  `children`-only soup or grabbing from a store inside a presentational
  component.
- Discriminated unions for variants (`variant: "primary" | "ghost"`) beat
  boolean piles (`isPrimary`, `isGhost`).
- Forward DOM-safe extras (`className`, `id`, `aria-*`, native button/input
  attributes) so wrappers stay accessible.
- Do not import **API wire types** or **server DTOs** into presentational
  components — map to view models in the container.

---

## Composition

- Compose small components. A page that is 400 lines of JSX usually wants
  extraction, not more props.
- Lift state only as far as siblings that need it. Everything else stays
  local (`useState` / uncontrolled inputs).
- Children and slots (`children`, `header`, `footer`) beat deep
  configuration objects.
- Do not reach across the tree with globals for something a callback prop
  can express.

---

## Styling

Pick **one** styling approach per project and stick to it (CSS modules,
Tailwind, vanilla CSS, styled-components). Document the choice in
`docs/COMPONENT_DESIGN.md` when it is not obvious from the repo.

- Variants belong in the component (props → class names), not ad-hoc
  class strings at every call site.
- Shared tokens (color, space, type) live in one place; do not hard-code
  hex values throughout feature components.

---

## Accessibility

- Prefer native elements (`button`, `a`, `label`, `input`) over clickable
  `div`s.
- Images need `alt` (empty `alt=""` only when decorative).
- Interactive controls need visible focus and keyboard support.
- Dialogs, menus, and tabs follow an established pattern (Headless UI,
  Radix, or equivalent) rather than a one-off `div` + `onClick`.
- Do not disable zoom or trap focus without an escape.

---

## Forms

Non-trivial forms belong in the **container / page**: wire the project's
form + schema library there (React Hook Form + Zod is a common pair) and pass
field state down. Shared Zod (or equivalent) schemas live next to validation
helpers, not copied into every screen. Surface field errors next to inputs and
associate them with labels.

---

## Testing

- Unit-test behaviour with Testing Library: role/name queries, user events,
  not implementation details (`getByTestId` as a last resort).
- Snapshot tests are for primitives with a stable visual contract, not
  pages that change weekly.
- Visual/a11y checks belong in Storybook or equivalent when the project has
  one.

---

## Checklist for a new component

- [ ] Presentational vs container is obvious from the file location.
- [ ] Props are typed; variants are a union, not a boolean pile.
- [ ] No fetch / store writes in presentational markup.
- [ ] Native semantics + keyboard + focus.
- [ ] Styles follow the project approach.
- [ ] Test covers the user-visible behaviour.

---

## Checklist for a new screen

Typical touch points (implement only what the task covers; data hooks belong
to the state layer):

- [ ] Page / container in the location given by **frontend-architecture.md**.
- [ ] Prefer extending existing shared primitives over duplicating markup.
- [ ] Call hooks at the container; pass typed view-model props down.
- [ ] Loading, error, and empty states consistent with sibling pages.
- [ ] Note route + nav touch points even if another agent owns routing.

---

## Project-specific docs

| If present, read | Content |
| ---------------- | ------- |
| `docs/COMPONENT_DESIGN.md` | Design-system tokens, library choice, folder exceptions |
| `AGENTS.md` | Dev/lint/test commands |
| `.agents/context/frontend-architecture.md` | Where pages, components, and features live |
| `.agents/context/frontend-state-design.md` | Where data and stores live |

When those are missing, infer from existing components under `src/`.
