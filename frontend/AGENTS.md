# Frontend (UI) Guidelines

## How to Use This Guide
This file contains the specific rules and skills for the Frontend application. Code-generating agents (like Koda) MUST read this before modifying UI components.

## Available Skills

> **Skills Reference**: For detailed patterns, use these skills:
> (Skills will be automatically injected here by sync.sh)

### Auto-invoke Skills

When performing these actions, ALWAYS invoke the corresponding skill FIRST:

| Action | Skill |
|--------|-------|
| "diseño frontend", "auditoría UI", "mejorar interfaz", "accesibilidad web", "optimizar UX", "refinar diseño", "animaciones UI", "paleta de colores", "tipografía web", "layout responsive", "polish UI", "criticar diseño", "harden frontend", "delight UI", "live edit UI" | `impeccable` |
| "ui design", "emil kowalski", "frontend design", "animations", "ui polish" | `emil-design-eng` |
| UI design assistance | `frontend-design` |
| animaciones en React | `motion-framer` |
| diseño de interacciones UI | `motion-framer` |
| diseño de interfaz | `frontend-design` |
| efectos de hover/tap/drag | `motion-framer` |
| frontend design | `frontend-design` |
| guidance visual | `frontend-design` |
| react, nextjs, performance, best-practices | `vercel-react-best-practices` |
| transiciones de página | `motion-framer` |

---

## CRITICAL RULES

1. **Framework**: Always use React (Functional Components + Hooks).
2. **Styling**: Always use TailwindCSS for styling. Do not write raw CSS files.
3. **State Management**: Use Zustand for global state.
