"""Regenerate .pi/handoff/plan.md for a worker step (Plan step P2 and its successors).

Usage (repo root):  python .pi/scripts/build_handoff.py <plan.md> <task-header.md>
Writes .pi/handoff/plan.md = task header + the plan's §3-§7 and §9 verbatim + the rulings
(D1, D2, D3, D12-D17, D20, house-style D6-D10) verbatim from .pi/knowledge/open-decisions.md,
with doc links rewritten to resolve from .pi/handoff/.
"""
import re
import sys

RULINGS = ["D1", "D2", "D3", "D12", "D13", "D14", "D15", "D16", "D17", "D20"]
REGISTER = ".pi/knowledge/open-decisions.md"
OUTPUT = ".pi/handoff/plan.md"


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as error:
        raise SystemExit(f"cannot read {path}: {error}") from error


def section(text, start, end):
    a = text.index(start)
    b = text.find(end, a + len(start))
    return text[a:b if b != -1 else len(text)].rstrip() + "\n"


def main(plan_path, header_path):
    plan = read(plan_path)
    reg = read(REGISTER)
    heads = [m.start() for m in re.finditer(r"^(### |## )", reg, re.M)]

    def ruling(dec_id):
        match = re.search(r"^### " + dec_id + r" — .*$", reg, re.M)
        if match is None:
            raise SystemExit(f"ruling {dec_id} not found in {REGISTER}")
        a = match.start()
        b = min([h for h in heads if h > a] or [len(reg)])
        return reg[a:b].rstrip() + "\n"

    body = section(plan, "## 3. Requirements", "## 8. Deployment")
    body = body.replace("\n## ", "\n### §").replace("\n### 4.", "\n#### 4.")
    gates = section(plan, "## 9. Gates", "\n## ZZZ").replace("## 9.", "### §9.")
    house = section(reg, "## Non-blocking — decided by the parent", "## Opened by Audit 2")
    out = read(header_path)
    out += "## Plan §3–§7 (verbatim)\n\n" + body + "\n## Plan §9 (verbatim)\n\n" + gates
    out += "\n## Rulings (verbatim from `.pi/knowledge/open-decisions.md`)\n\n"
    out += "\n".join(ruling(i) for i in RULINGS) + "\n" + house
    out = out.replace("](knowledge/", "](../knowledge/")
    out = out.replace("](reset-after-midnight%20Plan", "](../reset-after-midnight%20Plan")
    out = re.sub(r"\]\((?!\.\./|https?:|#)([a-z0-9_.-]+\.md)", r"](../knowledge/\1", out)
    out = re.sub(r"\]\(#(d\d+[^)]*)\)", r"](../knowledge/open-decisions.md#\1)", out)
    try:
        with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
    except OSError as error:
        raise SystemExit(f"cannot write {OUTPUT}: {error}") from error
    print(len(out.splitlines()), "lines written to", OUTPUT)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
