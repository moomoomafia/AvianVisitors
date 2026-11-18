#!/usr/bin/env python3
"""Check the repo's agent knowledge base and regenerate its reverse index.

Ruling D18 (.pi/knowledge/open-decisions.md). Conventions this enforces:

* Doc-to-doc references are relative markdown links, never bare backtick names.
* Source references stay backtick ``path:line`` (not links), written with the full
  repo-relative path the first time a file appears in each section.
* Every link and heading anchor resolves under GitHub slug rules.
* Every cited source file exists and every cited line is within the file.

Usage (from anywhere inside the repo)::

    python .pi/scripts/check_kb.py            # report; exit 1 on errors
    python .pi/scripts/check_kb.py --index    # also rewrite .pi/knowledge/_references.md
    python .pi/scripts/check_kb.py --verify-index   # error if _references.md is stale

Standard library only; Python 3.9+.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
KB = ROOT / ".pi" / "knowledge"
INDEX = KB / "_references.md"
REGISTER = KB / "open-decisions.md"
SOURCE_EXT = {".py", ".php", ".js", ".mjs", ".sh", ".toml", ".yml", ".yaml", ".json",
              ".service", ".timer", ".txt", ".html", ".css", ".md", ".caddy", ".conf"}
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".pi"}
REPO_DIRS = ("frame/", "avian/", "scripts/", "tests/", ".github/", "homepage/",
             "templates/", "docs/", "ops/", "model/", "extras/")

LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)\)")
CODE = re.compile(r"`([^`\n]+)`")
HEAD = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
SRC = re.compile(r"^((?:[\w.-]+/)*[\w.-]+?(\.[A-Za-z0-9]+))(?::([\d][\d, \-]*))?$")
DECISION = re.compile(r"\bD([1-9][0-9]?)\b")  # D1..D99 (was capped at D19, which hid D20)


def slug(text: str) -> str:
    """GitHub heading anchor: lowercase, strip punctuation except - and _, spaces->-."""
    text = LINK.sub(lambda m: m.group(2), text).replace("`", "")
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


def docs() -> list[pathlib.Path]:
    return sorted(p for p in KB.glob("*.md") if p != INDEX) + [ROOT / "AGENTS.md"]


def lines_of(path: pathlib.Path) -> list[tuple[int, str, str]]:
    """(lineno, section-slug, text) for prose lines; fenced code blocks skipped."""
    out, section, fenced = [], "", False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = HEAD.match(line)
        if m:
            section = slug(m.group(2))
        out.append((n, section, line))
    return out


def anchors(path: pathlib.Path) -> set[str]:
    return {slug(m.group(2)) for _, _, text in lines_of(path) for m in [HEAD.match(text)] if m}


def source_index() -> dict[str, list[str]]:
    by_name = collections.defaultdict(list)
    for p in ROOT.rglob("*"):
        if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(ROOT).parts) \
                and p.suffix in SOURCE_EXT:
            by_name[p.name].append(p.relative_to(ROOT).as_posix())
    return by_name


def resolve(ref: str, by_name) -> tuple[str | None, str]:
    """Return (repo-relative path or None, status)."""
    while ref.startswith("./"):
        ref = ref[2:]
    if (ROOT / ref).is_file():
        return ref, "full"
    tail = [c for c in by_name.get(pathlib.PurePosixPath(ref).name, []) if c.endswith(ref)]
    if len(tail) == 1:
        return tail[0], "short"
    if len(tail) > 1:
        return None, "ambiguous:" + ",".join(sorted(tail))
    return None, "missing" if ref.startswith(REPO_DIRS) else "external"


class Checker:
    """Walks every doc once; collects errors, warnings and the reverse index.

    Headings are deliberately exempt from span/decision rules: rewriting a heading
    changes its anchor and silently breaks inbound links.
    """

    def __init__(self) -> None:
        self.by_name = source_index()
        self.doc_names = {p.name for p in docs()} | {p.name for p in (ROOT / ".pi").glob("*.md")}
        self.anchor_cache: dict[pathlib.Path, set[str]] = {}
        self.nlines: dict[str, int] = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.cites_src = collections.defaultdict(set)
        self.cites_doc = collections.defaultdict(set)
        self.cites_dec = collections.defaultdict(set)
        # Only IDs that exist in the register count as citations; anything else that looks
        # like "D99" is either prose ("D1–D99") or a typo, and is reported, not indexed.
        register = REGISTER.read_text(encoding="utf-8") if REGISTER.exists() else ""
        self.known_dec = set(re.findall(r"^### (D\d+) ", register, re.M)) | set(
            re.findall(r"^\| (D\d+) \|", register, re.M))

    def run(self) -> None:
        for doc in docs():
            rel_doc = doc.relative_to(ROOT).as_posix()
            full_in_section: set[tuple[str, str]] = set()
            for n, section, line in lines_of(doc):
                where = f"{rel_doc}:{n}"
                for m in LINK.finditer(line):
                    self.link(doc, rel_doc, where, m.group(3))
                if HEAD.match(line):
                    continue
                # Count decision IDs in link *text* too: a linked "[D12](...)" is still a
                # citation of D12 (stripping links here hid every migrated reference).
                for m in DECISION.finditer(LINK.sub(lambda lk: lk.group(2), line)):
                    dec = f"D{m.group(1)}"
                    if self.known_dec and dec not in self.known_dec:
                        self.warnings.append(f"{where}: `{dec}` is not a decision in the register")
                        continue
                    self.cites_dec[dec].add(rel_doc)
                prose = LINK.sub("", line)
                for m in CODE.finditer(prose):
                    self.span(doc, rel_doc, where, section, m.group(1).strip(), full_in_section)

    def link(self, doc: pathlib.Path, rel_doc: str, where: str, target: str) -> None:
        if target.startswith(("http://", "https://", "mailto:")):
            return
        path, _, frag = target.partition("#")
        dest = (doc.parent / path.replace("%20", " ")).resolve() if path else doc
        if not dest.is_relative_to(ROOT):
            self.errors.append(f"{where}: link escapes the repo -> {target}")
            return
        if not dest.exists():
            self.errors.append(f"{where}: broken link -> {target}")
            return
        if dest.suffix == ".md":
            self.cites_doc[dest.relative_to(ROOT).as_posix()].add(rel_doc)
        if frag:
            if dest not in self.anchor_cache:
                self.anchor_cache[dest] = anchors(dest)
            if frag not in self.anchor_cache[dest]:
                self.errors.append(f"{where}: missing anchor #{frag} in {dest.name}")

    def span(self, doc, rel_doc, where, section, span, full_in_section) -> None:
        name = span.split("/")[-1].split(":")[0]
        if name in self.doc_names and name != doc.name and (
                span.startswith((".pi/", "../", "./")) or "/" not in span):
            self.warnings.append(f"{where}: bare doc mention `{span}` (use a markdown link)")
            return
        sm = SRC.match(span)
        if not sm or sm.group(2) not in SOURCE_EXT:
            return
        rel, status = resolve(sm.group(1), self.by_name)
        if status.startswith("ambiguous"):
            self.errors.append(f"{where}: ambiguous `{span}` -> {status.split(':', 1)[1]}")
            return
        if status == "missing":
            self.errors.append(f"{where}: missing source `{span}`")
            return
        if rel is None:
            return  # runtime/device file (state.json, config.toml, ...)
        self.cites_src[rel].add(rel_doc)
        if status != "full" and (section, rel) not in full_in_section:
            self.warnings.append(f"{where}: `{span}` -> first use in section should be `{rel}`")
        full_in_section.add((section, rel))
        if sm.group(3):
            self.lines_in_range(where, span, rel, sm.group(3))

    def lines_in_range(self, where: str, span: str, rel: str, spec: str) -> None:
        if rel not in self.nlines:
            text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
            self.nlines[rel] = len(text.splitlines())
        for num in re.findall(r"\d+", spec):
            if int(num) > self.nlines[rel]:
                self.errors.append(f"{where}: `{span}` line {num} > {self.nlines[rel]} lines")


def check(write_index: bool, verify_index: bool = False) -> int:
    c = Checker()
    c.run()
    if verify_index:
        current = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
        if current != render_index(c.cites_src, c.cites_doc, c.cites_dec):
            c.errors.append(f"{INDEX.relative_to(ROOT).as_posix()}: stale reverse index "
                            "(run: python .pi/scripts/check_kb.py --index)")
    for e in c.errors:
        print("ERROR  ", e)
    for w in c.warnings:
        print("WARN   ", w)
    print(f"\n{len(docs())} docs | {len(c.errors)} errors | {len(c.warnings)} warnings | "
          f"{len(c.cites_src)} source files cited | {len(c.cites_dec)} decision IDs cited")
    if write_index:
        INDEX.write_text(render_index(c.cites_src, c.cites_doc, c.cites_dec), encoding="utf-8")
        print(f"wrote {INDEX.relative_to(ROOT).as_posix()}")
    return 1 if c.errors else 0


def render_index(cites_src, cites_doc, cites_dec) -> str:
    def link(rel_doc: str) -> str:
        p = (ROOT / rel_doc)
        target = p.name if p.parent == KB else "../../" + rel_doc
        return f"[{p.name}]({target})"

    def row(key: str, users: set[str], label: str) -> str:
        return f"| {label} | {', '.join(link(u) for u in sorted(users))} |"

    reg_anchors = anchors(REGISTER)
    out = ["# Reverse reference index",
           "",
           "> **GENERATED by `python .pi/scripts/check_kb.py --index` \u2014 do not edit by hand.**",
           "> Use it to find every doc that relies on a file, doc or decision before you amend it",
           "> (the \"fix everywhere it propagated\" rule in [AGENTS.md](../../AGENTS.md)).",
           "",
           "## Decisions",
           "",
           "| Decision | Cited by |",
           "|---|---|"]
    for dec in sorted(cites_dec, key=lambda d: int(d[1:])):
        anchor = next((a for a in reg_anchors if a.startswith(dec.lower() + "-")), None)
        label = f"[{dec}](open-decisions.md#{anchor})" if anchor else dec
        out.append(row(dec, cites_dec[dec], label))
    out += ["", "## Knowledge docs (backlinks)", "", "| Doc | Linked from |", "|---|---|"]
    for d in sorted(cites_doc):
        out.append(row(d, cites_doc[d], link(d)))
    out += ["", "## Source files", "", "| Source file | Cited by |", "|---|---|"]
    for s in sorted(cites_src):
        out.append(row(s, cites_src[s], f"`{s}`"))
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Check the agent knowledge base and regenerate its reverse index.")
    ap.add_argument("--index", action="store_true", help="rewrite the reverse index")
    ap.add_argument("--verify-index", action="store_true",
                    help="fail if the reverse index is out of date (no writes)")
    args = ap.parse_args()
    sys.exit(check(args.index, args.verify_index))
