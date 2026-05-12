# `frontend/src/components/`

React component tree. Job-specific components live in `jobs/`; scraping UI in `scraping/`.

---

## Top-level components

| File | Description |
|------|-------------|
| `Header.jsx` | Top navigation bar: app title, scrape trigger button, CV upload |
| `FilterBar.jsx` | Horizontal filter strip: status tabs, source/type dropdowns, search input, score range slider |
| `Dashboard.jsx` | KPI dashboard view — applied/rejected charts, summary stat cards |
| `PipelineView.jsx` | Scraping pipeline status page — run history list, per-source progress |
| `GapAnalysis.jsx` | Skills gap analysis — two-column frequency bar chart of CV strengths vs JD gaps across scored jobs; filterable by min score and status |
| `ActivityLog.jsx` | Weekly activity log — target vs actual table with week navigation. Auto-tracked rows (applications sent, network reconnects) pull live counts from the DB; manual rows (outreach, LinkedIn posts, GitHub commits, interviews) use persisted +/- counters. Targets are click-to-edit inline. |

---

## `jobs/`

| File | Description |
|------|-------------|
| `JobTable.jsx` | Main job list — sortable columns, bulk selection, pagination, gap preview tooltip |
| `JobDrawer.jsx` | Detail drawer (slides in from right) — status actions, follow-up reminder, CV score breakdown, notes, job description |
| `ScoreBar.jsx` | Visual progress bar for a 0–100 CV match score, colour-coded by threshold |
| `StatusBadge.jsx` | Colour-coded pill badges: `StatusBadge`, `SourceBadge`, `TypeBadge` |
| `NetworkSection.jsx` | Contacts section inside the drawer — lists contacts, add/edit/reach-out actions, LinkedIn search links |

---

## `scraping/`

| File | Description |
|------|-------------|
| `ScrapeModal.jsx` | Modal shown while a scrape run is in progress — consumes the SSE stream from `/api/scraping/runs/{id}/stream` and renders per-source status rows |

---

## Key shared patterns

**React Query** — all server state is managed via `useQuery` / `useMutation` from `@tanstack/react-query`. Cache keys follow the shape `["jobs"]`, `["job", jobId]`, `["stats"]`.

**Mutation invalidation** — after any mutation (status update, scoring, note save), the mutating component invalidates `["jobs"]`, `["job", jobId]`, and `["stats"]` so all visible data refreshes without a full page reload.

**API calls** — all backend calls go through the central `api` object in `src/api/client.js`. Components never call `fetch` directly.

**Date utilities** — `relativeDate()` and `toDateInput()` are shared via `src/utils/dates.js`. `JobTable` uses relative mode ("2d ago"); `JobDrawer` uses absolute mode ("27 Mar 2026").
