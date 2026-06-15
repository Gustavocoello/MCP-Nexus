---
name: webwright
description: >
  Runs an autonomous browser automation agent using Playwright to complete web tasks.
  Trigger: When user asks to automate a website, fill a form, scrape data, click through 
  pages, or complete any task that requires controlling a real browser.
license: Apache-2.0
metadata:
  author: jarvis-system
  version: "1.0"
  scope: [root, jarvis, koda]
  auto_invoke: "Automating browser tasks or web interactions"
allowed-tools: Bash, Read, Write
---

## When to Use

Use this skill when:
- User asks to automate any interaction with a real website
- User wants to fill forms, click buttons, or navigate pages automatically
- User wants to scrape structured data from a website
- User wants a reusable script for a recurring web task
- User asks to "book", "search", "find on the web", or "check" something on a specific site

**Do NOT use when:**
- User wants a simple web search (use Ragel/Tavily instead)
- Task can be done with an API (no browser needed)
- User just wants information, not automation

---

## Critical Patterns

### Pattern 1: Always install dependencies first

```bash
pip install -e .
playwright install chromium
```

Only needed once. Skip if already installed.

### Pattern 2: Use the Claude backend config

```bash
python -m webwright.run.cli \
  -c base.yaml \
  -c model_claude.yaml \
  -t "{task}" \
  --start-url "{url}" \
  --task-id "{task_id}" \
  -o outputs/
```

Use `model_claude.yaml` — the project uses Anthropic. Never use `model_openai.yaml`.

### Pattern 3: craft vs run

| Command | Use when |
|---------|----------|
| `/webwright:run` | One-shot task with fixed values |
| `/webwright:craft` | Reusable script for recurring tasks |

Use `craft` when the user will repeat the task with different parameters.

---

## Decision Tree

```text
User wants to automate a website?
├── Is it a one-time task?          → use `run` mode
├── Will it repeat with variations? → use `craft` mode (produces parameterized script)
└── Does it need login/auth?        → warn user: Webwright handles sessions but 
                                      credentials must be provided manually
```

---

## Code Examples

### Example 1: One-shot flight search

```bash
python -m webwright.run.cli \
  -c base.yaml -c model_claude.yaml \
  -t "Find the cheapest economy flight from GYE to JFK on 2026-07-15" \
  --start-url https://www.google.com/flights \
  --task-id gye_jfk_search \
  -o outputs/
```

### Example 2: Reusable form filler

```bash
python -m webwright.run.cli \
  -c base.yaml -c model_claude.yaml \
  --craft \
  -t "Fill the contact form at example.com with name, email and message" \
  --start-url https://example.com/contact \
  --task-id contact_form \
  -o outputs/
```

### Example 3: Run a previously crafted script

```bash
python outputs/contact_form/final_script.py \
  --name "Gustavo" \
  --email "gustavo@example.com" \
  --message "Hello from Jarvis"
```

---

## Output Structure

```text
outputs/{task-id}/
├── plan.md              # Agent's step-by-step plan
├── final_script.py      # Reusable Playwright script (craft mode)
└── final_runs/
    └── run_1/
        ├── screenshots/ # Visual verification at each step
        └── trajectory/  # Full action log
```

---

## Commands

```bash
# One-shot task
python -m webwright.run.cli -c base.yaml -c model_claude.yaml \
  -t "{task}" --start-url "{url}" --task-id "{id}" -o outputs/

# Reusable script
python -m webwright.run.cli -c base.yaml -c model_claude.yaml \
  --craft -t "{task}" --start-url "{url}" --task-id "{id}" -o outputs/

# Run existing crafted script
python outputs/{task-id}/final_script.py --{param} "{value}"
```

---

## Resources

- **Source**: `src/webwright/` — core agent loop and Playwright environment
- **Configs**: `src/webwright/config/` — `base.yaml`, `model_claude.yaml`
- **Outputs**: `outputs/` — trajectories, screenshots, final scripts