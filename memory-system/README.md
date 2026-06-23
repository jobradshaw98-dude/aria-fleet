# Memory System — question-aware retrieval for AI agents

A deterministic, **zero-LLM** retrieval layer that surfaces the *right few* memory
files for a prompt — before the model answers. It runs as a Claude Code
`UserPromptSubmit` hook in **~40 ms** over the sample corpus (Python startup
included; scales roughly linearly with corpus size) and never calls an API.

The problem it solves: a static "load everything at session start" index doesn't
scale. As a memory corpus grows past a few dozen files, you either blow the context
window or miss the one note that mattered. This hook reads the prompt and pulls only
what's relevant — including notes that share no keywords with the prompt but are one
wiki-link away.

## How it works

Two stages, both pure Python over a folder of Markdown files:

**1. Seed (keyword score).** Extract meaningful terms from the prompt (stop-words
dropped). Score every memory file by overlap against its `name:` slug (weight ×3) and
`description:` frontmatter (weight ×2). Keep the top hits above a minimum score.

**2. Walk (link expansion).** For each strong seed, follow its `[[wikilinks]]` one hop
in both directions over a graph built from the whole corpus. Neighbors are
**degree-penalized** (`score × 0.5 / log2(degree+2)`) so a popular hub note can't flood
the results, and capped per seed. This is what catches the relevant-but-no-shared-keyword
note — e.g. a prompt about *deploy timing* surfaces the linked *timezone* note.

If the graph can't be built, it silently degrades to keyword-only — the hook never
blocks a prompt.

```
prompt ──▶ [seed: keyword score] ──▶ top N direct hits
                   │
                   └──▶ [walk: 1-hop wiki-links, degree-penalized] ──▶ linked hits
                                                                  │
                          inject "Possibly relevant memory" block ◀┘
```

## Memory file format

Each memory is one Markdown file with frontmatter and a body that links related notes:

```markdown
---
name: project_helios_auth
description: Helios auth subsystem — OAuth2 login via Google, JWT sessions
metadata:
  type: project
---

Auth for [[project_helios]] uses OAuth2 with short-lived JWT sessions.
Setup in [[reference_oauth_setup]]. Secrets rule: [[feedback_no_plaintext_secrets]].
```

`[[name]]` links to another memory's `name:` slug — that's the edge the walk follows.

## Try it

No dependencies beyond Python 3.8+ stdlib. The bundled `sample-memory/` (a fictional
dev "Sam" and project "Helios") lets it run immediately:

```bash
cd memory-system/hooks

# graph health report over the sample corpus
python memory_linkmap.py

# retrieval — note the link-walked hits the keywords alone wouldn't find
python memory-retrieve.py "how does helios auth handle secrets"
python memory-retrieve.py "when should I deploy to production"
```

Expected: the auth query returns the auth and secrets notes as direct hits **and**
link-walks to the OAuth-setup note; the deploy query link-walks from the off-hours
rule to the timezone note.

## Use it on your own corpus

1. Point the hook at your notes: `export MEMORY_DIR=/path/to/your/memory` (defaults to
   the bundled `sample-memory/`).
2. Write notes in the format above, linking related ones with `[[slug]]`.
3. Wire the hook into Claude Code — see `settings.example.json`.

## Files

| File | Role |
|---|---|
| `hooks/memory-retrieve.py` | The hook — seed + walk, prints the injection block |
| `hooks/memory_linkmap.py` | Builds the wiki-link graph; also a standalone health report |
| `hooks/memory-freshness.sh` | Optional companion — warns on stale memories |
| `sample-memory/` | 16 interlinked demo notes so everything runs out of the box |
| `settings.example.json` | Claude Code hook wiring template |
