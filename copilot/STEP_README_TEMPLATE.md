# Copilot Step README Template

Every new copilot step **must** include a `STEP<N>_README.md` with a **Testing CLI commands** section. Copy this structure when adding Step 5+.

---

## Required sections

1. **Title + one-line summary** — what this step adds
2. **Architecture** — diagram or flow (if applicable)
3. **Setup** — install and config commands
4. **Testing CLI commands** — **required** (see template below)
5. **Files** — key files added or changed
6. **Interview talking points** (optional)
7. **Next step** — link to the following step README

---

## Testing CLI commands (required template)

```markdown
---

## Testing CLI commands

Run these in order to verify Step N end-to-end.

**Prerequisites**
- List what must be done first (ingestion, API keys, docker services, etc.)

| Check | Command | API key? |
|-------|---------|----------|
| ... | ... | ... |

### 1. <first test case>

\`\`\`bash
python3 scripts/...
\`\`\`

**Expected output:**
- Bullet list of what to verify

### 2. <second test case>
...

### Quick smoke test

\`\`\`bash
# Minimal end-to-end sequence
\`\`\`

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| ... | ... |

---
```

## Rules

- Every step README **must** have `## Testing CLI commands` with copy-pasteable bash blocks.
- Include **expected output** or a verification checklist for each test case.
- Include a **Quick smoke test** block that runs the step end-to-end.
- Include **Prerequisites** (prior steps, env vars, ingestion).
- Add a **Troubleshooting** table for common errors when the step has external dependencies.
