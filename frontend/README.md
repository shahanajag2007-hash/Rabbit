# STYLEAI frontend

React 19 + Vite + TypeScript + React Three Fiber. See the [root README](../README.md) for setup.

```
src/
  pages/                 the six dashboard pages (RecommendationsPage = protected Recommended Outfit page)
  components/
    layout/              page header, step progress, section headings
    navigation/          top navigation (6 pages)
    common/              Streamlit-equivalent widgets (buttons, sliders, alerts, columns)
    outfit/              product card, outfit breakdown, customize/budget, why + fabric panels
    avatar/              3D viewer, GLB avatar loader, procedural fitting mannequin, garment mapping
  hooks/                 session store (zustand), outfit score, avatar helpers, meta data
  services/api.ts        typed client for the FastAPI backend
  types/                 shared types
  styles/theme.css       port of ui_theme.py + widget styles
public/models/           optional realistic avatar assets (see README there)
```

Scripts: `npm run dev`, `npm run dev:all` (backend + frontend), `npm run build`, `npm run preview`, `npm run typecheck`.
