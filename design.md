# DESIGN SKILL - UI

Use this as the implementation guardrail for all new or modified UI.

## Core Intent

- Build for operators, not marketing pages.
- Keep interfaces technical, dense, and predictable.
- Maintain current visual identity exactly unless explicitly asked to rebrand.

## Non-Negotiable Identity

- **Typeface:** `JetBrains Mono` only for product UI.
- **Primary accent:** `#C9754B`.
- **Accent hover:** `#E78468`.
- **Focus ring:** `#F4CBB9` (2px treatment on key controls).
- **Dark-first shell:** graphite surfaces with warm accent actions.

## Theme Tokens (Use Existing Variables)

Use tokenized variables from `frontend/src/style.css`; do not hardcode ad-hoc values.

- Dark shell:
  - canvas `#0F1114`
  - surface `#161A1D`
  - raised `#1F252D`
  - border `#2A3036` equivalent
  - text `#F5F7FA / #A8B0BA / #8A93A0`
- Light shell:
  - canvas `#F5F4F1`
  - surface `#FFFFFF`
  - raised `#F5F7FA`
  - border `#E5E7EB` equivalent
  - text `#11161C / #2C3139 / #3A424C`

## Logo Rules

Canonical source:
- `design/assets/logos/CraftsmanLabs-white.svg`

Required parity:
- `frontend/src/CraftsmanLabs.svg` must match canonical.
- `frontend/public/favicon.svg` must match canonical.

Theme rendering:
- Dark mode: white logo as-is.
- Light mode: invert via `--logo-filter`.

## UI Architecture Rules

- Keep shell structure stable:
  - sticky top bar
  - left icon sidebar
  - main workspace
  - bottom response drawer
- Keep toast system for runtime status (no inline raw status strings).

## Component Behavior Rules

- Buttons:
  - primary = accent fill
  - secondary = neutral shell
  - destructive = explicit danger
  - ghost = low-emphasis utility
- Inputs/selects/textareas:
  - always visible border
  - explicit focus-visible ring
  - support invalid/valid states where applicable
- KPI/metrics:
  - grouped semantic cards
  - large value + compact label
- Loading/empty/error:
  - skeleton/empty-state patterns, no plain unstyled placeholders

## Spacing / Radius / Stroke

- Spacing rhythm: `4, 8, 12, 16, 20, 24` (and larger section spacing where needed).
- Radius:
  - controls `8-10`
  - cards `12-16`
  - pills `999`
- Stroke: 1px default; avoid heavy borders except active/focus signals.

## Accessibility and Interaction

- Keyboard focus visible on every interactive control.
- Keep hover/focus subtle and technical; avoid playful motion.
- Respect reduced-motion preferences.
- Never rely on color-only status semantics.

## Engineering Rules for UI Changes

- Reuse existing classes/tokens first (DRY).
- Keep changes local and reversible (KISS).
- Preserve behavior contracts while adjusting visuals.
- Avoid broad CSS rewrites when targeted updates suffice.

## Avoid

- New font families.
- New accent color systems.
- Purple-forward visual palettes.
- Glassmorphism/neumorphism.
- Inconsistent radius or spacing systems.


# SimpleFlow Design Language (Current Production Spec)

This document defines the current implemented design language for SimpleFlow web surfaces, with emphasis on the Control Plane Workbench.

Primary implementation sources:
- `frontend/src/style.css`
- `frontend/src/pages/ControlPlanePage.vue`
- `frontend/src/pages/control-plane/*.vue`

Machine-readable token reference:
- `design/tokens/simpleflow-ui-tokens.json`

## 1) Product Tone

- Operator-first, technical, and audit-friendly.
- Information-dense by default, with explicit hierarchy and status semantics.
- Monospace-forward identity (`JetBrains Mono`) across product UI.
- Warm accent usage for action and state emphasis, not decoration.

## 2) Typography Contract

- Font family:
  - Body/UI: `JetBrains Mono`
  - Monospace technical values: `JetBrains Mono`
- Weight guidance:
  - `700`: high-priority titles/values
  - `600`: section titles, labels, action captions
  - `500`: body/action text
- Core sizes in Control Plane:
  - page/title: `24`
  - section: `18`
  - body input/value: `16`
  - metadata/labels: `12`

## 3) Color and Theme Contract

### Accent and interaction
- Primary accent: `#C9754B`
- Primary hover: `#E78468`
- Focus ring: `#F4CBB9`

### Dark mode (primary operational shell)
- Canvas: `#0F1114`
- Surface: `#161A1D`
- Raised surface: `#1F252D`
- Offset surface: `#12171D`
- Border: `#2A3036` equivalent alpha blend
- Text primary: `#F5F7FA`
- Text secondary: `#A8B0BA`
- Text muted: `#8A93A0`

### Light mode (secondary)
- Canvas: `#F5F4F1`
- Surface: `#FFFFFF`
- Raised surface: `#F5F7FA`
- Offset surface: `#EEF1F4`
- Border: `#E5E7EB` equivalent alpha blend
- Text primary: `#11161C`
- Text secondary: `#2C3139`
- Text muted: `#3A424C`

### Status tokens
- Success: dark-first green family (`#5CD0A5` + tinted variants)
- Warning: amber family (`#E0B460` / `#B45309`)
- Error: warm-red mapped to system accent family for consistency
- Status must always be conveyed by icon/text + color (never color-only)

## 4) Logo and Brand Asset Rules

Canonical logo asset:
- `design/assets/logos/CraftsmanLabs-white.svg`

Frontend usage:
- `frontend/src/CraftsmanLabs.svg` should match the canonical asset.
- `frontend/public/favicon.svg` should match the canonical asset.

Theme rendering behavior:
- Dark mode: use white logo as-is.
- Light mode: invert white logo to dark via CSS filter token (`--logo-filter`).

## 5) Spatial System

- Spacing scale: `4, 8, 12, 16, 20, 24` for app shell internals.
- Radius scale:
  - small controls: `6-8`
  - button/input: `8-10`
  - cards/panels: `12-16`
  - pills/chips: `999`
- Borders: `1px` standard; avoid heavy outlines except explicit active/focus states.
- Shadows: restrained; used for overlays/toasts/drawers only.

## 6) Control Plane Shell Spec

### Top bar
- Sticky top bar with:
  - brand/logo + workspace breadcrumb
  - utility actions (info/help/notifications)
  - current user/org chip
- Height target: compact operator bar (~56px).

### Sidebar
- Icon-led navigation with text labels.
- Required states:
  - default
  - hover
  - active (accent emphasis + left indicator)
  - focus-visible
- Collapse toggle anchored at sidebar footer.

### Feedback surfaces
- Toast stack at bottom-right:
  - success/loading/error variants
  - dismissible
- Response Console as collapsible bottom drawer:
  - collapsed summary strip (last action + quick copy)
  - expanded payload panel with JSON highlighting

## 7) Form and Action System

- Inputs/selects/textareas must always show:
  - visible border
  - readable background contrast
  - clear focus-visible ring
- Buttons must map to intent:
  - primary: filled accent
  - secondary: neutral surfaced/outlined
  - ghost: low-emphasis utility
  - destructive: explicit danger styling
- Validation states:
  - invalid border + helper text
  - valid border where real-time validation is required

## 8) Data and Panel Patterns

- KPI/stat cards:
  - grouped by semantic domain
  - large numeric value, smaller uppercase/metadata label
  - absent values should use explicit placeholder (for example `—`), not ambiguous zero when meaning is unknown.
- Empty states:
  - must include actionable next step text.
- Loading states:
  - prefer skeletons/placeholders over raw running text.

## 9) Motion Rules

- Motion must be functional and subtle.
- Typical transitions: `140-220ms`.
- Hover lift should remain minimal (`-1px` to `-2px`).
- Respect reduced-motion with global fallback.
- Avoid spring/bouncy motion on enterprise/operator surfaces.

## 10) Accessibility Requirements

- Maintain contrast >= WCAG-friendly thresholds for text and controls.
- All interactive controls require keyboard-visible focus.
- Ensure no keyboard traps in drawers/popovers/accordions.
- Use semantic labels for icon-only controls.

## 11) Implementation Guardrails

Do:
- Keep tokens centralized and semantic.
- Reuse existing panel/action patterns before inventing variants.
- Preserve behavior while refactoring visuals.

Do not:
- Introduce new typefaces for product UI.
- Introduce additional accent palettes (especially purple-forward themes).
- Use decorative-only motion, glassmorphism, or mismatched radius systems.
