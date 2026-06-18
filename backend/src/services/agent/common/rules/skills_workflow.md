# STRICT RULES FOR SKILLS MANAGEMENT (CREATION, UPDATE, DOWNLOAD)

You are managing the AI Agent Skills ecosystem. **Koda** is the ONLY agent allowed to perform file operations for skills. Nexus must NOT be used for skill file operations.

## 1. Skills File Operations Mapping

| Operation | Agent | Tool Used Internally by Agent |
| :--- | :--- | :--- |
| Create NEW skill (file does not exist) | Koda | `koda_write_file` |
| Download skill from GitHub | Koda | `download_external_skill` |
| Update frontmatter or small blocks | Koda | `koda_patch_file` / `koda_append_to_file` |
| Full rewrite of existing skill | Koda | `koda_write_file` (with overwrite) |
| Rename or Move a skill | Koda | `koda_rename_item` |
| Delete a skill | Koda | `koda_delete_item` |
| Read-only List/verify directory | Koda | `koda_list_directory` |

---

## 2. SKILLS NAVIGATION — MANDATORY

When the user mentions ANY skill operation (create, rename, move, update, list):
1. ALWAYS start with: `set_workspace("agents")` → this sets root to `.../services/agent/`
2. The skills/ folder is at `agents/skills/` — all skill paths are relative to there
3. NEVER create skill folders relative to cwd without setting workspace first

Examples:
- "rename huma-tone to human-tone in skills" → set_workspace("agents") → koda_rename_item("skills/huma-tone", "skills/human-tone")
- "create skill human-tone" → set_workspace("agents") → koda_write_file("skills/human-tone/SKILL.md", content)
- "list skills" → set_workspace("agents") → koda_list_directory("skills/")

---


## 3. Skills Workflows

### A. Creating a New Local Skill
1. JARVIS: `read_skill("skill-creator")` → get the official template.
2. JARVIS: Compose the full `SKILL.md` content following the spec.
3. JARVIS: `ask_koda`: "Use set_workspace('agents'), then create file `skills/{name}/SKILL.md` with this exact content: [content]"
4. JARVIS: `ask_koda`: "List the directory to verify the folder and file exist. Use `koda_list_skills`"
5. JARVIS: Show user: "✅ Verified: `skills/{name}/SKILL.md` exists."
6. JARVIS: Ask the user: "¿Corro skill-sync para registrarlo?" → **HARD STOP** (WAIT for explicit "sí" from user).
7. JARVIS/KODA: If "sí", execute `run_bash("./skills/skill-sync/assets/sync.sh")` → report result → STOP.

### B. Updating an Existing Skill
1. JARVIS: `read_skill("{name}")` → show current content to user.
2. JARVIS: Propose the new content → **HARD STOP** → wait for user confirmation.
3. JARVIS: On "sí": `ask_koda`: "Patch `skills/{name}/SKILL.md`: read file first, then patch, then verify reading it again."
4. JARVIS: After Koda confirms with verification → ask: "¿Corro skill-sync?" → **HARD STOP** (WAIT for "sí").
5. JARVIS/KODA: Execute `run_bash("./skills/skill-sync/assets/sync.sh")` → report → STOP.

### C. Renaming or Deleting a Skill
1. JARVIS: Confirm exactly what the user wants to rename or delete.
2. JARVIS: `ask_koda`: "Use `koda_rename_item` OR `koda_delete_item` on the target skill folder in `skills/`."
3. JARVIS: After Koda confirms success → ask the user: "El cambio se realizó. ¿Corro skill-sync para actualizar el índice de agentes?" → **HARD STOP** (WAIT for "sí").
4. JARVIS/KODA: Execute `run_bash("./skills/skill-sync/assets/sync.sh")` → report → STOP.

### D. Downloading an External Skill
**Phase 1 — Download (Koda)**
1. Extract owner, repo, skill-name from URL.
2. JARVIS: `ask_koda`: "Call `download_external_skill` with owner='{owner}', repo='{repo}', path='skills/{name}'. Ensure it downloads successfully."
3. JARVIS: Wait for success confirmation from Koda.

**Phase 2 — Normalize (JARVIS proposes)**
4. JARVIS: `read_skill("{name}")` → inspect the downloaded frontmatter.
5. JARVIS: Design the new frontmatter block. Strict Rules:
   - Keep original `name`, `description`, `license` unchanged.
   - Add `metadata.author: jarvis-system`
   - Add `metadata.version: "1.0"`
   - Add `metadata.scope` — MUST be an inline YAML list: `[scope1, scope2]`
     *Choose from:* `root, jarvis, koda, lamar, ragel, ui, api, database, mcp_server, sdk`
     *NEVER write scope as bullet points.* ALWAYS inline: `[root, jarvis]` not `- root\n- jarvis`
   - Add `metadata.auto_invoke` — can be a bullet list (each trigger on its own `- line`).
   - Add `allowed-tools` — keep original if present, otherwise `[]`.
6. JARVIS: Present the complete proposed frontmatter to the user.
7. JARVIS: **HARD STOP** — wait for explicit user "sí".

**Phase 3 — Patch & Sync (Koda + Bash)**
8. JARVIS: `ask_koda`: "Patch frontmatter of `skills/{name}/SKILL.md`. Read first, patch, verify."
9. JARVIS: On Koda success → ask: "¿Corro skill-sync?" → **HARD STOP** (WAIT for "sí").
10. JARVIS/KODA: Execute `run_bash("./skills/skill-sync/assets/sync.sh")` → report → STOP.

---

## 4. Skills Discovery & Execution
- To list skills: DO NOT CALL ANY TOOL. You already have the full list of skills in your system prompt (under "ÍNDICE DE SKILLS DISPONIBLES" or "Auto-invoke Skills"). Read your own memory and present that list beautifully formatted to the user.
- `read_skill`: Use ONLY when the user asks to USE or RUN a specific skill to understand its parameters.
- `run_bash`: Use ONLY after `read_skill`, ONLY if user asked to RUN it, and ONLY targeting `./skills/*` paths.