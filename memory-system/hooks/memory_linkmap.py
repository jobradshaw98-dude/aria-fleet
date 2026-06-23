#!/usr/bin/env python3
"""
ARIA memory link-graph — shared module + standalone report tool.

Parses [[wikilinks]] out of every memory file body, RESOLVES each link target to a
real file (filenames vary: underscore slug vs hyphen vs frontmatter `name:`), and
builds a forward/backlink adjacency graph used by memory-retrieve.py to expand
keyword seeds into their linked neighbours.

Canonical link form going forward = the FILENAME SLUG (filenames are stable;
`name:` values are free-text and mutate). The resolver tolerates the legacy forms.

No cache, no JSON on disk: building over ~174 files is ~20 ms, far under the hook's
5 s budget. The hook imports build_graph(); this file also runs standalone:

    python memory_linkmap.py            # graph health report
    python memory_linkmap.py --json     # machine-readable report
"""
import os
import re
import sys
import json
import glob

# Point this at your own memory corpus via the MEMORY_DIR env var.
# Defaults to the bundled sample-memory/ so the report runs out of the box.
MEM_DIR = os.environ.get(
    "MEMORY_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sample-memory"),
)

# Files that are not retrievable memories (index / logs / dashboards).
NON_MEMORY = {"MEMORY", "MEMORY_FULL", "MEMORY_MAP", "MEMORY.original",
              "DASHBOARD", "DREAM_LOG"}

LINK_RE = re.compile(r"\[\[([^\]|#]+)")          # [[target]] / [[target|alias]] / [[target#hdr]]
NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
DELISTED_RE = re.compile(r"\b(SUPERSEDED|DEPRECATED|OBSOLETE)\b")
STATUS_DELISTED_RE = re.compile(r"^status:\s*delisted\s*$", re.MULTILINE | re.IGNORECASE)


def _is_delisted(text):
    """
    True only if a memory is genuinely superseded/delisted — marked in its
    FRONTMATTER (name:/description:) or a leading H1, OR `status: delisted`.
    Deliberately NOT a whole-body scan: a live memory that merely QUOTES the words
    SUPERSEDED/DEPRECATED/OBSOLETE as rule-text (e.g. feedback_memory_skills_merged)
    must stay reachable by the link-walk.
    """
    if STATUS_DELISTED_RE.search(text):
        return True
    # frontmatter block (between the first pair of --- fences)
    region = ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            region = text[:end]
    # plus any H1 lines anywhere
    region += "\n" + "\n".join(
        ln for ln in text.splitlines() if ln.startswith("# "))
    return bool(DELISTED_RE.search(region))


def _norm(s):
    """Normalise a slug for matching: lowercase, hyphen→underscore, strip .md."""
    s = s.strip()
    if s.lower().endswith(".md"):
        s = s[:-3]
    return s.lower().replace("-", "_")


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def build_graph(mem_dir=MEM_DIR):
    """
    Returns (graph, report).

    graph = { slug: {links:[slug...], backlinks:[slug...], degree:int,
                     delisted:bool, desc:str} }
    report = {dangling:[(src, raw_target)...], isolated:[slug...], files:int}
    """
    files = [p for p in glob.glob(os.path.join(mem_dir, "*.md"))
             if os.path.basename(p)[:-3] not in NON_MEMORY]

    # ---- index every file by its resolvable keys ----
    by_norm_slug = {}      # normalised filename slug -> canonical slug
    by_norm_name = {}      # normalised frontmatter name -> canonical slug
    meta = {}              # slug -> {desc, delisted, raw_links:[...]}
    for p in files:
        slug = os.path.basename(p)[:-3]
        text = _read(p)
        by_norm_slug[_norm(slug)] = slug
        nm = NAME_RE.search(text)
        if nm:
            by_norm_name.setdefault(_norm(nm.group(1)), slug)
        # description for the hit line
        desc = ""
        dm = re.search(r"^description:\s*(.+?)\s*$", text, re.MULTILINE)
        if dm:
            desc = dm.group(1)
        delisted = _is_delisted(text)
        raw_links = LINK_RE.findall(text)
        meta[slug] = {"desc": desc, "delisted": delisted, "raw_links": raw_links}

    def resolve(raw):
        n = _norm(raw)
        if n in by_norm_slug:           # 1. filename slug (incl. hyphen→underscore)
            return by_norm_slug[n]
        if n in by_norm_name:           # 2. frontmatter name: match
            return by_norm_name[n]
        return None                      # 3. genuinely dangling

    # ---- build edges ----
    graph = {s: {"links": [], "backlinks": [], "degree": 0,
                 "delisted": meta[s]["delisted"], "desc": meta[s]["desc"]}
             for s in meta}
    dangling = []
    for src, m in meta.items():
        seen = set()
        for raw in m["raw_links"]:
            tgt = resolve(raw)
            if tgt is None:
                dangling.append((src, raw.strip()))
                continue
            if tgt == src or tgt in seen:
                continue
            seen.add(tgt)
            graph[src]["links"].append(tgt)
            graph[tgt]["backlinks"].append(src)

    for s, node in graph.items():
        node["degree"] = len(node["links"]) + len(node["backlinks"])

    isolated = sorted(s for s, n in graph.items() if n["degree"] == 0)
    report = {"dangling": sorted(set(dangling)), "isolated": isolated,
              "files": len(files)}
    return graph, report


def _report_text(graph, report):
    out = []
    out.append(f"ARIA memory link-graph — {report['files']} files")
    linked = sum(1 for n in graph.values() if n["degree"] > 0)
    out.append(f"  connected: {linked}   isolated: {len(report['isolated'])}   "
               f"dangling links: {len(report['dangling'])}")
    out.append("\nTop hubs (by degree):")
    for s, n in sorted(graph.items(), key=lambda kv: -kv[1]["degree"])[:10]:
        out.append(f"  {n['degree']:3d}  {s}")
    out.append("\nDangling links (target not found — need repair):")
    for src, raw in report["dangling"]:
        out.append(f"  {src}  ->  [[{raw}]]")
    out.append(f"\nIsolated nodes ({len(report['isolated'])}) — no links in or out:")
    for s in report["isolated"]:
        out.append(f"  {s}")
    return "\n".join(out)


def main():
    import io
    try:  # utf-8 stdout only when run standalone — never as a side effect of import
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass
    graph, report = build_graph()
    if "--json" in sys.argv:
        print(json.dumps({"report": report,
                          "graph": {k: {"links": v["links"],
                                        "backlinks": v["backlinks"],
                                        "degree": v["degree"]}
                                    for k, v in graph.items()}}, indent=2))
    else:
        print(_report_text(graph, report))


if __name__ == "__main__":
    main()
