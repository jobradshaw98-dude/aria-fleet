#!/usr/bin/env python3
"""
Question-aware memory retrieval (UserPromptSubmit hook).

Two-stage routing, all deterministic, no LLM/API:
  1. SEED  — score the ARIA memory files by keyword overlap against their `name:`
             slug + `description:` frontmatter (v1 behaviour).
  2. WALK  — follow each strong seed's [[wikilinks]] one hop (via memory_linkmap)
             to pull in related memories the keywords alone would miss (e.g.
             "meals" finds the linked "protein prefs" file). Link-neighbours are
             degree-penalised + capped so a hub can't flood the results.

Purpose: surface the RIGHT few memory files for the question, instead of relying
on the MEMORY.md index that loads once at session start.

Usage (manual test):  python memory-retrieve.py "how does banksync work"
As a hook:            reads the prompt from stdin JSON (UserPromptSubmit), prints
                      an injection block to stdout.

If the link graph can't be built for any reason, this silently degrades to the
v1 keyword-only behaviour — it never blocks the prompt.
"""
import sys
import os
import re
import json
import glob
import io
import math

# Windows console defaults to cp1252; force utf-8 so em-dashes don't mangle.
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

# Trivial prompts that should not trigger retrieval (too short / pure control).
TRIVIAL = {
    "yes", "no", "sure", "ok", "okay", "go", "do it", "proceed", "continue",
    "summarize", "summary", "stop", "thanks", "thank you", "yep", "nope",
    "go ahead", "please", "yes please", "sounds good", "next",
}

# Point this at your own memory corpus via the MEMORY_DIR env var.
# Defaults to the bundled sample-memory/ so the hook runs out of the box.
MEM_DIR = os.environ.get(
    "MEMORY_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sample-memory"),
)
TOP_N = 5            # max direct keyword hits shown
MIN_SCORE = 2        # don't surface weak matches
MAX_LINKED = 3       # max link-walk neighbours shown
NEIGHBORS_PER_SEED = 2  # cap per seed so one hub can't fill every linked slot
DECAY = 0.5          # neighbour inherits this fraction of seed score (then degree-penalised)

# memory_linkmap lives in this same hooks dir; make it importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from memory_linkmap import build_graph
except Exception:
    build_graph = None  # degrade to v1 keyword-only

STOP = set("""
a an the and or but if then else for to of in on at by with from into over under
is are was were be been being do does did has have had this that these those it its
my your his her our their what when where which who whom how why i you he she we they
me him us them about as so not no yes can could should would will just like get got
""".split())


def terms(text):
    words = re.findall(r"[a-z0-9_]+", text.lower())
    return {w for w in words if len(w) >= 3 and w not in STOP}


def desc_of(path):
    """Pull the description: frontmatter line (first ~10 lines)."""
    try:
        with open(path, encoding="utf-8") as f:
            for _ in range(12):
                line = f.readline()
                if not line:
                    break
                if line.lower().startswith("description:"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def score(query_terms, name, description):
    nset = terms(name.replace("_", " "))
    dset = terms(description)
    # name match weighted higher than description match
    return 3 * len(query_terms & nset) + 2 * len(query_terms & dset)


def retrieve(prompt):
    if prompt.strip().lower() in TRIVIAL:
        return []
    q = terms(prompt)
    if len(q) < 2:  # need at least 2 meaningful terms to be worth surfacing
        return []
    hits = []
    for path in glob.glob(os.path.join(MEM_DIR, "*.md")):
        name = os.path.basename(path)[:-3]
        # skip the index, its backup, and non-memory logs/dashboards
        if name in ("MEMORY", "MEMORY_FULL", "MEMORY_MAP", "MEMORY.original",
                    "DASHBOARD", "DREAM_LOG"):
            continue
        d = desc_of(path)
        s = score(q, name, d)
        if s >= MIN_SCORE:
            hits.append((s, name, d))
    hits.sort(key=lambda h: (-h[0], h[1]))
    return hits  # all qualifying seeds (sorted); caller caps direct vs. walked


def walk(seeds, direct_names):
    """
    Expand keyword seeds one hop along the [[link]] graph. Returns a list of
    (score, name, desc, via) neighbour tuples — link-surfaced memories the
    keywords alone missed. Silent no-op if the graph can't be built.
    """
    if build_graph is None:
        return []
    try:
        graph, _ = build_graph(MEM_DIR)
    except Exception:
        return []

    best = {}  # neighbour name -> (score, desc, via_seedname)
    for s, name, _d in seeds:
        node = graph.get(name)
        if not node:
            continue
        # 1-hop neighbours, both directions; degree-penalise so big hubs add less.
        neigh = []
        for tgt in node["links"] + node["backlinks"]:
            tnode = graph.get(tgt)
            if not tnode or tnode["delisted"]:
                continue
            if tgt in direct_names:  # already a direct hit; don't double-list
                continue
            penalty = math.log2(tnode["degree"] + 2)
            nscore = (s * DECAY) / penalty
            neigh.append((nscore, tgt, tnode["desc"]))
        # cap neighbours contributed by THIS seed (strongest first)
        neigh.sort(key=lambda x: -x[0])
        for nscore, tgt, tdesc in neigh[:NEIGHBORS_PER_SEED]:
            if tgt not in best or nscore > best[tgt][0]:
                best[tgt] = (nscore, tdesc, name)

    out = [(sc, n, dsc, via) for n, (sc, dsc, via) in best.items()]
    out.sort(key=lambda x: -x[0])
    return out[:MAX_LINKED]


def main():
    # accept prompt as argv (test mode) or stdin JSON (hook mode)
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        try:
            prompt = json.load(sys.stdin).get("prompt", "")
        except Exception:
            prompt = ""
    seeds = retrieve(prompt)
    if not seeds:
        return
    direct = seeds[:TOP_N]
    direct_names = {n for _s, n, _d in direct}
    linked = walk(direct, direct_names)

    print("[memory-retrieve] Possibly relevant memory (open before answering):")
    for s, name, d in direct:
        print(f"  - {name} (score {s}) — {d}")
    for sc, name, d, via in linked:
        print(f"  - {name} (linked via {via}) — {d}")


if __name__ == "__main__":
    main()
