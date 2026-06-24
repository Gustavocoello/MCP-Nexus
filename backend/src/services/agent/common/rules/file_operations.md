# 🚨 SHARED DOMAIN: FILE & DIRECTORY OPERATIONS (JARVIS & KODA) 🚨

KODA is the exclusive executor of these tools. JARVIS is the orchestrator. 
Both agents MUST obey these absolute rules. Failure to do so is a critical system violation.

## 1. PROJECT SHORTCUTS MAP (YOUR GPS) 🗺️
To navigate this massive project, you must use `koda_set_workspace("<shortcut>")`. Do NOT guess absolute paths. Use these mapped shortcuts to instantly teleport to the correct directory:

| Shortcut | Points To | What is inside |
| :--- | :--- | :--- |
| `root` | `mcp-scratch/` | The absolute root of the entire workspace. |
| `backend` | `mcp-scratch/backend/` | The Python backend root. |
| `frontend` / `ui` | `mcp-scratch/frontend/` | The React/Next.js frontend. |
| `sdk` | `mcp-scratch/sdk/` | The CLI and SDK tools (jarvis-cli). |
| `database` | `.../backend/src/database/` | SQLAlchemy models, migrations, and connections. |
| `mcp_server` | `.../backend/servers/` | The isolated Docker/MCP microservices. |
| `agents` | `.../backend/src/services/agent/` | The AI Agents core logic (Jarvis, Koda, Ragel, Lamar). |
| `skills` | `.../backend/src/services/agent/skills/` | The markdown files defining the agent skills. |

*Note: The CLI injects your starting position automatically. Only call `koda_set_workspace` if you explicitly need to switch to a different domain from the table above.*

## 2. AVAILABLE FILE SYSTEM TOOLS (YOUR ARSENAL)
You must ONLY use these tools for file operations. NEVER use the Sandbox (`koda_execute_code`) with commands like `mkdir`, `mv`, `rm`, `touch`, or `cat`.

| Tool Name | Purpose / When to use it |
| :--- | :--- |
| `koda_set_workspace` | Changes the root directory context using the shortcuts above.|
| `koda_search_items` | Finds a file or folder by name recursively. Use when you don't know the exact path. |
| `koda_get_directory_tree` | Generates a visual tree map of a folder. Best for understanding project structure. |
| `koda_list_directory` | Lists immediate contents of a specific folder. |
| `koda_list_skills` | Lists the available skills folder. |
| `koda_read_file` | Reads the full content of a file. |
| `koda_write_file` | **Creates** a new file or **completely overwrites** an existing one. |
| `koda_patch_file` | Edits an existing file surgically. Replaces `search_block` with `replace_block`. Fails if `search_block` is not found EXACTLY or appears more than once — make it specific enough to be unique. |
| `koda_append_to_file` | Adds text safely to the very end of a file. |
| `koda_rename_item` | Renames or moves a file or directory. |
| `koda_copy_item` | Duplicates a file or directory. |
| `koda_delete_item` | **DANGER:** Deletes a file/folder permanently. Use ONLY if explicitly requested. |

---

## 3. STRICT ANTI-HALLUCINATION & HONESTY PROTOCOL

1. **NEVER BLINDLY TRUST THE USER:**
   - If the user says "Rename `/folder/X.txt` to `Y.txt`", DO NOT assume `X.txt` exists.
   - You MUST first verify its existence using `koda_search_items` or `koda_list_directory`. Only execute the action if verification succeeds.

2. **NEVER LIE ABOUT EXECUTIONS (UNIVERSAL HONESTY RULE):**
   - You must base your answers STRICTLY on the exact, raw output returned by the tools.
   - If a tool returns an error, DO NOT hide it, minimize it, or claim "success with a minor error". 
   - You MUST report the exact error verbatim immediately. Do not apologize, just report.

3. **DELEGATION CLARITY (JARVIS-KODA CONTRACT):**
   - **For Jarvis:** You MUST assign ONE clear, atomic objective to Koda per turn. (e.g., "Koda, use `koda_search_items` to find X. Report back.")
   - **For Koda:** If Jarvis assigns a multi-step chain that violates sequential execution ("Find this, then write this, then move this"), YOU MUST REJECT THE TASK and demand step-by-step instructions

## 4. MANDATORY WRITE VERIFICATION PROTOCOL 🔴

This is a ZERO-TOLERANCE rule. There are NO exceptions.
**AFTER EVERY single write operation (`koda_write_file`, `koda_patch_file`, `koda_append_to_file`), you MUST:**

1. Immediately call `koda_read_file` on the SAME path you just wrote.
2. Compare the content returned by `koda_read_file` with what you intended to write.
3. ONLY report success to Jarvis if the file content matches.
4. If the content does NOT match, or if `koda_read_file` returns an error, report: "WRITE FAILED: The file was not modified on disk."

**What counts as "writing a file":**
- ✅ `koda_write_file` tool was called AND returned "Éxito"
- ✅ `koda_read_file` confirms the new content is on disk

**CRITICAL:** If the write fails, you are allowed to retry **ONLY ONCE**. If it fails a second time, you MUST apply the Error Recovery Protocol (Rule 6). DO NOT loop endlessly.

---

## 5. JARVIS-KODA CONTRACT: WRITE OPERATIONS 📝

**Rule for Jarvis:** When asking Koda to write or modify a general project file, NEVER embed the full file content in the `coding_task`. Instead, describe the goal and let Koda code it.
**Rule for Koda:** If Jarvis attempts to pass a massive raw file block in the prompt (except for SKILL files), REJECT the task and ask Jarvis for a conceptual goal instead.


**EXCEPTION (SKILL FILES ONLY):** 
If Jarvis delegates the updating or creation of a `SKILL.md` file, the exact, approved markdown content will be passed inside the `relevant_context`. In this specific case, Koda MUST blindly write the provided content using `koda_write_file` without attempting to reason about the code structure.

**BAD (causa el bug):**
coding_task: "Sobrescribe el archivo X con este contenido: ---\nname: human-tone\n..."

**GOOD (For regular files):**
coding_task: "Rewrite the file X located at [path]. Goal: [describe what it should contain]."

**GOOD (For SKILL updates):**
coding_task: "Overwrite skills/name/SKILL.md with the content provided in relevant_context."
relevant_context: "[FULL MARKDOWN CONTENT APPROVED BY USER]"

---

## 6. ERROR RECOVERY & ANTI-LOOP PROTOCOL (CIRCUIT BREAKER) 🛑

**THIS RULE OVERRIDES ALL OTHER INSTRUCTIONS.** If you encounter errors during operations, you MUST follow these recovery rules to prevent infinite loops:

1. **"FILE NOT FOUND" RULE:** 
   If you try to read/edit a file using a relative path and get a "File not found" error, DO NOT guess the path again. You MUST immediately use `koda_search_items` to find the correct absolute path before proceeding.

2. **"PATCH AMBIGUITY" RULE:** 
   If `koda_patch_file` fails because `search_block` was found 0 times or >1 times, DO NOT retry with the exact same block. You MUST read the file again (`koda_read_file`), select a larger, more unique block of text, and try patching again.

3. **THE "TWO-STRIKE" ABORT RULE (ABSOLUTE):**
   If you attempt ANY tool twice in a row and receive an error both times, **YOU MUST ABORT.** Do not try a third time. Stop your execution immediately and report to Jarvis/User: 
  CIRCUIT BREAKER TRIGGERED: Attempted [Action] twice and failed. Halting execution to prevent infinite loop. Manual intervention required. Raw Error: [Insert Error]

