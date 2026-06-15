---
name: mcp-sync-docs
description: >
  Automatically syncs and updates MCP tool documentation into each agent's AGENT.md file.
  Trigger: Use when the user says "update the agents", "sync the MCPs", "regenerate documentation",
  "run the sync", or when tools are added/modified on any MCP server.
license: Apache-2.0
metadata:
  author: jarvis-system
  version: "1.0"
  scope: [root, jarvis]
  auto_invoke: "Syncing MCP documentation to the agents"
allowed-tools: Read, Edit, Write, Bash
---

## When to Use

Use this skill when:
- A new tool is added to an MCP server
- An existing tool description is modified
- A new MCP is connected to an agent
- The user explicitly requests updating or regenerating agent documentation
- Changes are deployed to any MCP server

---

## Critical Patterns

The script connects to each MCP via `StreamableHTTP`, fetches tools with `tools/list`, and overwrites
the `### Connected MCP Integrations` section in the corresponding `AGENT.md`.

### Pattern 1: Extracting tools from an MCP object (do NOT treat as dict)

```python
# CORRECT — fastmcp Tool objects are NOT dicts
if isinstance(mcp_tool, dict):
    name = mcp_tool.get("name", "unknown")
    desc = mcp_tool.get("description", "")
else:
    name = getattr(mcp_tool, "name", "unknown")
    desc = getattr(mcp_tool, "description", "")

# WRONG — causes 'Tool' object has no attribute 'get'
name = getattr(mcp_tool, "name", mcp_tool.get("name", "unknown"))
```

### Pattern 2: Replacing the section in AGENT.md

```python
start_marker = "### Connected MCP Integrations"

if start_marker in content:
    before, after = content.split(start_marker)[0], content.split(start_marker)[1]
    next_heading = after.find("\n## ")
    after = after[next_heading:] if next_heading != -1 else ""
    new_content = before + mcp_section + after
else:
    new_content = content + "\n" + mcp_section  # First run: append to end
```

---

## Decision Tree

```text
Is the MCP server running?          → No  → Start it before executing
Does AGENT.md already have section? → Yes → Replace it in place
Does AGENT.md already have section? → No  → Append to end of file
Does the tool return an empty desc? → Yes → Use fallback "Tool exposed via MCP"
Is mcp_tool a dict?                 → Yes → Use .get() / No → Use getattr()
```

---

## Code Examples

### Example 1: Adding a new agent to the mapping

```python
# In sync_mcps.py
AGENT_MCP_MAPPING = {
    "koda":       ["github", "context7", "files"],
    "nexus":      ["notion", "google_calendar", "devtools", "github"],
    #"new_agent":  ["slack", "jira"]          # ← add here
}

AGENT_PATHS = {
    "koda":      backend_dir / "src" / "services" / "agent" / "Koda"     / "AGENT.md",
    "nexus":     backend_dir / "src" / "services" / "agent" / "nexus"    / "AGENT.md",
    #"new_agent": backend_dir / "src" / "services" / "agent" / "NewAgent" / "AGENT.md",
}
```

### Example 2: Expected output in AGENT.md

```markdown
### Connected MCP Integrations

The following external tools are injected into this agent via MCP:

| Integration | Available Tools |
|-------------|-----------------|
| **github**  | **github_search_repositories**: Search GitHub repos<br>**github_get_file_contents**: Read file from repo<br> |
| **files**   | **mcp_read_file**: Reads a local file<br>**mcp_patch_file**: Surgically edits a file<br> |
```

---

## Commands

```bash
# Run full sync (all agents)
python src/services/agent/skills/mcp-sync-docs/assets/sync_mcps.py

# Check that all MCP servers are running before syncing
bash src/services/agent/skills/mcp-sync-docs/assets/sync_test.sh

# Run both in sequence — test first, sync only if all servers are up
bash src/services/agent/skills/mcp-sync-docs/assets/sync_test.sh && python src/services/agent/skills/mcp-sync-docs/assets/sync_mcps.py
```

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `'Tool' object has no attribute 'get'` | Tool treated as dict | Use `getattr()` — see Pattern 1 |
| `*(Error connecting)*` in table | MCP server is down | Start the MCP server on its port |
| `*(No tools exposed)*` | Server connects but registers no tools | Check tool registration on the server |
| `AGENT.md not found` | Wrong path in `AGENT_PATHS` | Verify the agent folder name |

---

## Resources

- **Main script**: See [assets/sync_mcps.py](assets/sync_mcps.py)
- **Connectivity test**: See [assets/sync_test.sh](assets/sync_test.sh)