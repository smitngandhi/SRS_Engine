# code-review-graph — Complete Daily Workflow

> Mixed stack · uv/uvx · Feed context to Claude / Gemini / ChatGPT

---

* [ ] PHASE 0 — One-Time Install (Do This Once)

```bash
# Install via uv (recommended — faster, no venv hassle)
uv tool install code-review-graph

# Verify it works
code-review-graph --version
```

---

## PHASE 1 — New Project Setup (Do This Once Per Repo)

```bash
# 1. Go to your project root
cd your-project/

# 2. Build the full graph (parses ALL files across ALL languages)
code-review-graph build

# 3. Check what was found
code-review-graph status
```

**Example `status` output:**

```
Files:      18
Functions:  94
Classes:    12
Edges:     203
Languages:  Python, TypeScript, JavaScript
Graph DB:   .code-review-graph/graph.db
```

```bash
# 4. Generate the visual HTML map of your codebase
code-review-graph visualize
# → Opens/saves as .code-review-graph/graph.html
# → Open this file in your browser (Chrome recommended)
```

---

## PHASE 2 — Getting Context to Feed Any LLM

### Option A: Copy-Paste into Chat (Claude.ai / Gemini / ChatGPT)

```bash
# Get a full risk-scored change impact report
code-review-graph detect-changes

# Get graph stats summary (lightweight context)
code-review-graph status
```

Copy the output → paste into your LLM chat with your question:

```
Prompt template:

"Here is my codebase graph summary and change impact report:

[PASTE detect-changes output here]

[PASTE status output here]

Now review the changes in auth.py. Are there any risks?
Which other files might break? Suggest improvements."
```

---

### Option B: Export to File and Upload

```bash
# Export full graph context to a text file
code-review-graph detect-changes > context.txt

# Append status too
code-review-graph status >> context.txt

# Optional: append the wiki/architecture summary
code-review-graph wiki >> context.txt
```

Then upload `context.txt` to Claude.ai / Gemini / ChatGPT as an attachment.

---

### Option C: Both (Recommended for Big Projects)

```bash
# Create a rich context bundle
code-review-graph detect-changes > llm-context.txt
code-review-graph status >> llm-context.txt
code-review-graph visualize   # for your own reference in browser
```

Upload `llm-context.txt` AND paste the key change section in chat.

---

## PHASE 3 — You Make the LLM-Recommended Changes

After the LLM tells you what to fix → go fix your files.

---

## PHASE 4 — Update the Graph After Changes (NOT a Rebuild)

```bash
# Incremental update — only re-parses changed files (< 2 seconds)
code-review-graph update
```

This is smart — it:

- Detects which files you modified via SHA-256 hash diff + git diff
- Re-parses ONLY those files + their dependents
- Updates edges (calls, imports, tests) automatically
- Does NOT touch unchanged files

```bash
# After updating, check impact of your new changes
code-review-graph detect-changes

# Refresh the visual map
code-review-graph visualize
```

Repeat Phase 2 → share with LLM again for a follow-up review.

---

## PHASE 5 — Live Watch Mode (While Actively Coding)

Open a **second terminal** and run:

```bash
code-review-graph watch
```

Leave it running. Every time you save a file, the graph auto-updates:

```
[WATCH] auth.py modified → re-parsed (0.3s)
[WATCH] orders.py dependency updated
```

No need to run `update` manually when watch mode is active.

---

## PHASE 6 — Generate Architecture Docs (Bonus)

```bash
# Requires Ollama running locally (free, open source LLM runner)
# Install Ollama: https://ollama.com

# Then generate a markdown wiki of your whole codebase
code-review-graph wiki
```

This produces a `wiki.md` you can upload to any LLM for deep architectural questions.

---

## Full Daily Loop (Quick Reference)

```
Morning / Start of work:
  code-review-graph watch          ← run in background terminal, leave it

Before asking LLM to review:
  code-review-graph detect-changes > llm-context.txt
  → Upload to Claude / Gemini / ChatGPT

After making LLM-recommended changes:
  code-review-graph update
  code-review-graph detect-changes > llm-context.txt
  → Upload again for follow-up review

When you want the visual map:
  code-review-graph visualize
  → Open .code-review-graph/graph.html in browser
```

---

## All Commands — Cheat Sheet

| Command                                            | What it does                        | When to use                   |
| -------------------------------------------------- | ----------------------------------- | ----------------------------- |
| `code-review-graph build`                        | Full parse of entire repo           | Once per project              |
| `code-review-graph update`                       | Re-parse only changed files         | After every coding session    |
| `code-review-graph watch`                        | Auto-update on every file save      | Leave running while coding    |
| `code-review-graph detect-changes`               | Risk-scored impact report           | Before/after LLM review       |
| `code-review-graph status`                       | Graph health + file/function counts | Quick sanity check            |
| `code-review-graph visualize`                    | Interactive HTML graph map          | When you want to see the map  |
| `code-review-graph wiki`                         | Auto-generate architecture docs     | Weekly / before big refactors |
| `code-review-graph detect-changes > context.txt` | Export context to file              | To upload to any LLM          |
| `code-review-graph status >> context.txt`        | Append stats to file                | Combine with above            |

---

## When to Rebuild from Scratch

Only needed if:

- You deleted a large number of files
- You renamed the project structure heavily
- The graph DB gets corrupted

```bash
# Force full rebuild
rm -rf .code-review-graph/
code-review-graph build
```

Otherwise, always use `update`. It's faster and smarter.

---

## Example End-to-End Session

```bash
# Terminal 1 (background)
cd my-app/
code-review-graph watch

# Terminal 2 (your work terminal)
# ... you code, edit auth.py and payments.py ...

# Ready for LLM review:
code-review-graph detect-changes > llm-context.txt
code-review-graph status >> llm-context.txt

# Upload llm-context.txt to Claude.ai / Gemini / ChatGPT
# Ask: "Review these changes. What could break? Suggest fixes."

# LLM says: fix validate_token() return type and add null check
# You make those fixes...

# Update graph:
code-review-graph update

# Check new impact:
code-review-graph detect-changes

# Visualize final state:
code-review-graph visualize
# Open .code-review-graph/graph.html in browser ✓
```
