# Vue Setup with Bun

This is the baseline frontend setup for the dashboard using Vue 3 + TypeScript + Vite, managed with `bun`.

## Create App

```bash
bun create vite dashboard --template vue-ts
cd dashboard
bun install
```

## Run Local Development

```bash
bun run dev
```

## Build and Test

```bash
bun run build
bun run test
```

## Recommended Folder Layout

```text
dashboard/
  src/
    app/
      router/
      providers/
    modules/
      onboarding/
      sources/
      status/
      progress/
      chat/
    components/
      ui/
    composables/
    services/
      api/
    models/
    pages/
  public/
  index.html
  bun.lock
  package.json
  tsconfig.json
  vite.config.ts
```

## Implementation Notes

- Use Composition API with `script setup` and typed props/emits.
- Keep API access in `src/services/api` and not in page components.
- Keep shared business logic in composables and avoid duplicated logic in views.
- Model async states explicitly (`idle`, `loading`, `success`, `error`).
- Create one page for onboarding first so first-run setup is front-loaded.

## Suggested First Screens

1. Onboarding wizard (Obsidian path + Qdrant mode).
2. Sources management page.
3. Status page (jobs + connector health).
4. File progress page.
5. Chat page with filters and citations.
