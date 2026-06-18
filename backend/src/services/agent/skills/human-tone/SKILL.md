---
name: human-tone
updated: 2026-06-18
metadata:
  author: jarvis-system
  version: "1.1"
  scope: [jarvis, koda, ragel, ui]
  auto_invoke:
    - Cuando el usuario pide "hablar más natural"
    - Cuando el usuario dice "menos formal"
    - Cuando el usuario solicita "tono humano"
    - Cuando el usuario quiere "evitar detección de IA"
allowed-tools: []
description: >
  Creates natural, human-like responses with unpredictable patterns to avoid AI detection. Trigger: When user wants to avoid AI detection scores or needs more organic language flow.
license: Apache-2.0
---

## When to Use
- When content needs to pass AI detection tests
- For creative writing with natural flow
- When avoiding formulaic structures

## Critical Patterns
1. **Asymmetry**: Mix paragraph lengths (4-5 lines + 1-line impact)
2. **Punctuation variety**: Use ;, rhetorical questions, and short impactful sentences
3. **Active voice only**: Direct statements without passive constructions
4. **Narrative flow**: Present concepts as intellectual arguments, not encyclopedic facts
5. **Unpredictable structure**: Start with time clauses ("When X did Y...") to break traditional patterns

## Code Examples
```text
"Turing demostró que las máquinas pueden pensar. Pero nadie preguntó: ¿qué pensaría Turing si viera IA moderna?"

"Cuando los algoritmos escriben, siguen patrones. La humanidad no."
```

## Commands
```bash
# No direct commands - use as writing style pattern
```