# Repository Guidelines (Jarvis System)

## How to Use This Guide

- Start here for cross-project norms. Jarvis is a multi-agent system with several domain-specific agents.
- Each agent has an `AGENT.md` file with specific guidelines (e.g., `jarvis/AGENT.md`, `Koda/AGENT.md`).
- Domain-specific agent docs override this file when guidance conflicts.

## Available Skills

Use these skills for detailed patterns on-demand:

### Generic Skills (Any Project)

<!-- GENERIC_SKILLS_TABLE_START -->
| Skill | Description | URL |
|-------|-------------|-----|
| `skill-creator` | Creates new AI agent skills following the Agent Skills spec. | [SKILL.md](skills/skill-creator/SKILL.md) |
| `skill-sync` | Synchronizes skill metadata to AGENTS.md Auto-invoke sections. | [SKILL.md](skills/skill-sync/SKILL.md) |
| `mcp-sync-docs` | Syncing MCP documentation to agents | [SKILL.md](skills/mcp-sync-docs/SKILL.md) |
<!-- GENERIC_SKILLS_TABLE_END -->

### Jarvis-Specific Skills

<!-- SPECIFIC_SKILLS_TABLE_START -->
| Skill | Description | URL |
|-------|-------------|-----|
| `skill-creator` | Creates new AI agent skills following the Agent Skills spec. | [SKILL.md](skills/skill-creator/SKILL.md) |
| `skill-sync` | Synchronizes skill metadata to AGENTS.md Auto-invoke sections. | [SKILL.md](skills/skill-sync/SKILL.md) |
| `mcp-sync-docs` | Syncing MCP documentation to agents | [SKILL.md](skills/mcp-sync-docs/SKILL.md) |
<!-- SPECIFIC_SKILLS_TABLE_END -->

### Auto-invoke Skills

When performing these actions, ALWAYS invoke the corresponding skill FIRST:

| Action | Skill |
|--------|-------|
| "diseño frontend", "auditoría UI", "mejorar interfaz", "accesibilidad web", "optimizar UX", "refinar diseño", "animaciones UI", "paleta de colores", "tipografía web", "layout responsive", "polish UI", "criticar diseño", "harden frontend", "delight UI", "live edit UI" | `impeccable` |
| "ui design", "emil kowalski", "frontend design", "animations", "ui polish" | `emil-design-eng` |
| After creating/modifying a skill | `skill-sync` |
| Creating new skills | `skill-creator` |
| Regenerate AGENTS.md Auto-invoke tables (sync.sh) | `skill-sync` |
| Syncing MCP documentation to the agents | `mcp-sync-docs` |
| Troubleshoot why a skill is missing from AGENTS.md auto-invoke | `skill-sync` |
| UI design assistance | `frontend-design` |
| actualizar specs principales | `openspec-sync-specs` |
| analizar requisitos | `openspec-explore` |
| animaciones en React | `motion-framer` |
| aplicar cambios de delta specs | `openspec-sync-specs` |
| archivar un cambio OpenSpec | `openspec-archive-change` |
| continuar implementación de un cambio | `openspec-apply-change` |
| crear propuesta OpenSpec | `openspec-propose` |
| diseño de interacciones UI | `motion-framer` |
| diseño de interfaz | `frontend-design` |
| efectos de hover/tap/drag | `motion-framer` |
| explorar ideas | `openspec-explore` |
| finalizar cambio completado | `openspec-archive-change` |
| frontend design | `frontend-design` |
| generar diseño y tareas | `openspec-propose` |
| guidance visual | `frontend-design` |
| implementar tareas de un cambio OpenSpec | `openspec-apply-change` |
| investigar un problema | `openspec-explore` |
| pensar en voz alta | `openspec-explore` |
| proponer un nuevo cambio | `openspec-propose` |
| react, nextjs, performance, best-practices | `vercel-react-best-practices` |
| sincronizar specs de un cambio | `openspec-sync-specs` |
| trabajar en tareas de OpenSpec | `openspec-apply-change` |
| transiciones de página | `motion-framer` |

---

## Project Overview

Jarvis is an Autonomous Multi-Agent AI system designed to handle software engineering, infrastructure monitoring, and user productivity through the Model Context Protocol (MCP).

### Agent Domains
| Agent | Location | Role / Tech Stack |
|-----------|----------|------------|
| Jarvis | `jarvis/` | Main Orchestrator, LLM Router, Delegation |
| Koda | `Koda/` | Autonomous Software Engineer, Sandbox execution |
| Lamar | `lamar/` | Sentinel, Infrastructure, DevOps, Token Tracking |
| Ragel | `ragel/` | Researcher, RAG, Vector Database (pgvector) Internet Access |
| Nexus | `nexus/` | MCP Specialist, Productivity, APIs |

### Project Domains
| Domain | Location | Description |
|-----------|----------|------------|
| Frontend (UI) | `../../../../frontend/` | React, UI/UX, User Interface |
| Backend (API) | `../../../../backend/` | Python, Flask, LangGraph |
| Database | `../../../../backend/src/database/` | PostgreSQL, Alembic, Models |
| SDK | `../../../../../jarvis-sdk/` | External SDK for Jarvis integration |
| MCP Servers | `../../../../backend/servers/` | Model Context Protocol servers |

---

