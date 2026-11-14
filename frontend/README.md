# KeyVerhaus — frontend

pnpm monorepo:

```
apps/web       Vue 3 + Vite SPA — the app (app.<domain>)
apps/shop      (later) Nuxt, public SEO pages
packages/ui    shared components + Tailwind theme (graphite + yellow, see docs/design.md)
packages/api   typed API client, types generated from the backend's OpenAPI
```

## Run

```bash
pnpm install
pnpm dev            # http://localhost:5173, /api is proxied to the backend on :8000
```

The backend must be running (see backend/README.md). Different backend port:
`API_PORT=8001 pnpm dev`.

## After every backend API change

```bash
pnpm api:gen        # regenerates packages/api/src/schema.d.ts
pnpm typecheck      # TypeScript shows every place that needs updating
```

## Notes

- Code style: in `.vue` files `<template>` comes first, then `<script setup>`. Shared
  components live in `packages/ui` and are named `UI…` (`UIButton`, `UIField`, …).

- Languages: uk and en are translated (`apps/web/src/i18n/locales`); pl, de, fr, es, it
  fall back to English until translated.
- E-mail links point to /verify-email, /reset-password, /invite — keep these routes.
- Error messages are translated by backend error code (`errors.*` in the locale files).

## Code style

- In `.vue` files `<template>` comes first, then `<script setup>`.
- Shared components live in `packages/ui` and are named `UI…` (`UIButton`, `UIField`, …).
