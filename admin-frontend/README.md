# Admin Frontend

Modern React admin panel for KAZZA Restaurant Backend.

## Development

```bash
cd admin-frontend
npm install
npm run dev
```

Dev server runs at http://localhost:5174 with API proxy to Django.

## Production Build

```bash
cd admin-frontend
npm run build
```

Built files go to `admin-frontend/dist/` and are served by Django at `/panel/`.

## URLs

| URL | Description |
|-----|-------------|
| `/panel/` | Admin SPA (new frontend) |
| `/admin-api/` | REST API for admin operations |
| `/admin/` | Legacy Django admin (Jazzmin) |

## Stack

- React 18 + TypeScript + Vite
- TanStack Query (caching, performance)
- TanStack Table (virtualized lists)
- Tailwind CSS 4
- Lucide icons

## Authentication

Uses Django session auth. Login with staff user credentials (username + password).
