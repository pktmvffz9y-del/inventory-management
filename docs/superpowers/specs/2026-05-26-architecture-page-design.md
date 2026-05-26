# Architecture Page Design Spec

**Date:** 2026-05-26
**Output:** `docs/architecture.html`
**Status:** Approved

## Overview

A single self-contained HTML file providing a professional reference overview of the Factory Inventory Management System. No external dependencies, no build step — opens directly in any browser. Dark slate palette matching the application's design system.

## Layout

Tabbed interface with four tabs. Active tab content fills the main area; all tabs visible in a fixed header. JavaScript handles tab switching inline — no framework required.

## Color System

Matches the application's design system:

| Token | Value | Usage |
|-------|-------|-------|
| Background | `#0f172a` | Page background |
| Card | `#1e293b` | Tab content panels, cards |
| Border | `#334155` | Dividers, table lines |
| Muted text | `#64748b` | Labels, secondary info |
| Body text | `#e2e8f0` | Primary readable text |
| Accent blue | `#3b82f6` | Active tab, links, Frontend |
| Accent green | `#10b981` | Backend / FastAPI |
| Accent amber | `#f59e0b` | Data layer / JSON |
| Accent purple | `#8b5cf6` | Composables / shared state |

## Tab 1 — Tech Stack

Three equal-width columns rendered as cards:

**Frontend**
- Vue 3 (Composition API)
- Vite (dev server + build, port 3000)
- Vue Router (SPA routing, 7 routes)
- Axios (HTTP client via api.js)

**Backend**
- Python 3 + FastAPI
- Pydantic (request/response validation)
- uvicorn (ASGI server, port 8001)
- uv (Python package manager)

**Data**
- 7 JSON files in `server/data/`
- In-memory filtering (no database)
- Mock data loaded at server startup via `mock_data.py`

## Tab 2 — Architecture

CSS box diagram with three horizontal layers connected by labeled arrows:

```
┌─────────────────────────────────────────────────────┐
│  Browser (Vue 3 SPA)                                │
│  Views · Components · Composables · api.js          │
└───────────────────┬─────────────────────────────────┘
                    │ HTTP REST (localhost:8001)
┌───────────────────▼─────────────────────────────────┐
│  API Layer (FastAPI)                                │
│  Endpoints · Pydantic Models · Filter Functions     │
└───────────────────┬─────────────────────────────────┘
                    │ In-memory read
┌───────────────────▼─────────────────────────────────┐
│  Data Layer                                         │
│  inventory.json · orders.json · demand_forecasts    │
│  backlog_items · spending · transactions · purchase_orders │
└─────────────────────────────────────────────────────┘
```

Each layer is a styled box. Arrows rendered with CSS borders. No SVG required.

## Tab 3 — Data Flow

Numbered timeline showing a filter change propagating end-to-end:

1. User changes a filter in **FilterBar.vue**
2. **useFilters.js** composable updates shared reactive state (`selectedLocation`, `selectedPeriod`, `selectedCategory`, `selectedStatus`)
3. Page component `watch()` fires → calls **api.js** with `getCurrentFilters()`
4. **api.js** builds `URLSearchParams` → `GET /api/orders?warehouse=Tokyo&category=sensors&month=2025-01`
5. **FastAPI endpoint** receives query params → calls `apply_filters()` + `filter_by_month()`
6. Functions filter the in-memory JSON array (case-insensitive, `'all'` bypasses filter)
7. Serialized response returned as JSON array of Pydantic-validated objects
8. Vue component updates reactive `ref` → computed properties recalculate → DOM re-renders

Each step is a numbered card. Steps 1–3 highlighted blue (frontend), 4 amber (API call), 5–7 green (backend), 8 blue (frontend).

## Tab 4 — API Endpoints

Table with columns: Method · Endpoint · Query Params · Returns. Grouped by domain with a section header row.

| Group | Endpoints |
|-------|-----------|
| Dashboard | `GET /api/dashboard/summary` |
| Inventory | `GET /api/inventory`, `GET /api/inventory/{id}` |
| Orders | `GET /api/orders`, `GET /api/orders/{id}` |
| Demand & Backlog | `GET /api/demand`, `GET /api/backlog` |
| Spending | `/api/spending/summary`, `/monthly`, `/categories`, `/transactions` |
| Reports | `GET /api/reports/quarterly`, `GET /api/reports/monthly-trends` |
| Purchase Orders | `POST /api/purchase-orders`, `GET /api/purchase-orders/{id}` |

## File Output

`docs/architecture.html` — single file, inline CSS and JS, no external requests. Open with `open docs/architecture.html` on macOS.

## Non-Goals

- No interactivity beyond tab switching
- No live data from the API
- No mobile responsiveness required (developer reference doc)
- No print stylesheet
