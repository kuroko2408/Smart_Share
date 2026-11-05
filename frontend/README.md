# Smart Share — Frontend Application Foundation

React 19 + TypeScript + Vite frontend client for **Smart Share — Intelligent, Location-Based Cab Pooling**.

---

## 1. Directory Structure

```text
frontend/
├── public/
│   ├── favicon.svg
│   └── icons.svg
├── src/
│   ├── app/
│   │   ├── providers/          # React Query and app-level providers
│   │   └── router/             # React Router routing configuration
│   ├── assets/                 # Static media and fonts
│   ├── components/             # Reusable UI components
│   ├── features/               # Feature domain modules (home, ride request, etc.)
│   │   └── home/               # Landing page and backend health monitor
│   ├── lib/                    # Configuration, env, and utility helpers
│   ├── services/               # API client and backend service callers
│   ├── test/                   # Vitest setup and testing mocks
│   ├── App.tsx                 # Root application component
│   ├── index.css               # Global Tailwind CSS styles
│   └── main.tsx                # Application DOM entrypoint
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── vitest.config.ts
```

---

## 2. Technology Stack

- **Framework**: React 19 + React DOM 19
- **Bundler**: Vite 8 with `@vitejs/plugin-react`
- **Language**: TypeScript 5.8+ (target: ES2023)
- **Styling**: Tailwind CSS 4 with `@tailwindcss/vite`
- **Routing**: React Router 7
- **Server State**: TanStack React Query 5
- **Icons**: Lucide React
- **Validation**: Zod
- **Testing**: Vitest + Testing Library (React, Jest-DOM, User-Event)
- **Linting**: Oxlint

---

## 3. Environment Configuration

Copy `.env.example` to `.env.local`:

```bash
cp .env.example .env.local
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8000/api/v1` |
| `VITE_SUPABASE_URL` | Supabase project URL (Phase 2 Auth) | `""` |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous public key (Phase 2 Auth) | `""` |
| `VITE_MAP_TILE_URL` | Map tile layer URL | OpenStreetMap default |

---

## 4. Development Commands

From the `frontend/` directory:

```bash
# Install dependencies
npm ci

# Start development server on http://localhost:5173
npm run dev

# Run TypeScript typecheck
npm run typecheck

# Run linter (oxlint)
npm run lint

# Run automated tests (Vitest)
npm run test

# Run tests in watch mode
npm run test:watch

# Build production bundle
npm run build

# Preview production build locally
npm run preview
```
