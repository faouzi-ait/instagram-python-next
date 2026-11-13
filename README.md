# Instagram Project

A starter web application with a Next.js frontend and a FastAPI backend.

## Features

- **Frontend:** Next.js App Router, React, TypeScript, and Tailwind CSS.
- **Backend:** FastAPI with a health-check endpoint at `GET /api/health`.
- **Frontend-to-backend check:** The home page includes a button that calls `/api/health` and displays success or failure status.
- **API documentation:** FastAPI provides Swagger UI at `/docs`, ReDoc at `/redoc`, and the OpenAPI schema at `/openapi.json`.
- **Development API proxy:** Next.js rewrites `/api/*` requests to the FastAPI server. Set `FASTAPI_URL` to override the default `http://127.0.0.1:8000` destination.
- **Cross-origin requests:** The backend only allows origins listed in the comma-separated `AUTH_ALLOWED_ORIGINS` environment variable.

## Tooling

- **Next.js 16** and **React 19** for the frontend.
- **FastAPI** and **Uvicorn** for the Python API.
- **TypeScript** for frontend type checking.
- **Tailwind CSS** for styling.
- **ESLint** for JavaScript/TypeScript linting.
- **Prettier** for consistent formatting.
- **Vitest**, **React Testing Library**, and **jsdom** for frontend tests.
- **pytest** and FastAPI's `TestClient` for backend tests.
- **Lefthook** for pre-commit formatting, lint, and test checks. Install its Git hook with `npx lefthook install` if it is not already installed.

## Requirements

- Node.js and npm.
- Python 3.13 (or a compatible Python version).

## Setup

Install the frontend dependencies:

```bash
npm install
```

Create the backend virtual environment and install its requirements from the project root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r app/backend/requirements.txt
```

## Run locally

Start the FastAPI backend in one terminal:

```bash
npm run backend
```

The backend listens on port `8000`. The script binds to `0.0.0.0`, making it reachable from other devices on the local network as well as from this computer. Do not expose it to untrusted networks without appropriate security controls.

Start the Next.js frontend in another terminal:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

For a different backend URL, define `FASTAPI_URL` in the environment where Next.js is started, for example:

```bash
FASTAPI_URL=http://127.0.0.1:8000 npm run dev
```

## Available npm scripts

- `npm run dev` — Start the Next.js development server.
- `npm run backend` — Start the FastAPI backend with Uvicorn reload enabled on port 8000.
- `npm run build` — Create a production build of the Next.js app.
- `npm run start` — Start the Next.js production server. Run `npm run build` first.
- `npm run lint` — Run ESLint.
- `npm run format` — Format project files with Prettier.
- `npm run format:check` — Check formatting without modifying files.
- `npm test` — Run the frontend Vitest suite.
- `npm run test:backend` — Run backend pytest tests.

## Tests and Git hooks

Run the test suites independently or together:

```bash
npm test
npm run test:backend
```

The configured Lefthook pre-commit jobs check staged files with Prettier and ESLint, then run both frontend and backend test suites. To run the hook manually without committing:

```bash
npx lefthook run pre-commit
```

## Project structure

```text
app/
  __tests__/          Frontend page tests
  backend/
    main.py           FastAPI application and CORS configuration
    routes/           API route handlers
    tests/            Backend tests
  page.tsx            Home page and backend health-check UI
```
