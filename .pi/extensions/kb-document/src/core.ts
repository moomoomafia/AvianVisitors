/**
 * Pure logic for the kb-document extension (decision D19).
 *
 * No Pi imports here: everything is plain data in / data out so it runs under
 * `node --test` with no Pi, no model and no filesystem side effects.
 */

/** Trigger words chosen by the operator (D19 ruling, 2026-11-16). */
export const TRIGGERS: ReadonlyArray<{ word: string; re: RegExp }> = [
	// `(?<![.\w/$])` / `(?!\.[A-Za-z_$])` keep JS like `document.querySelector`,
	// paths like `docs/document` and identifiers from firing.
	{ word: "document", re: /(?<![.\w/$])document(?:s|ed|ing|ation)?\b(?!\.[A-Za-z_$])/i },
	{ word: "record", re: /(?<![.\w/$])record(?:s|ed)?\b(?!\.[A-Za-z_$])/i },
	{ word: "write down", re: /\bwrite\s+(?:it\s+|this\s+|that\s+|them\s+)?down\b/i },
	{ word: "note this", re: /\bnote\s+(?:this|that)\b/i },
	{ word: "register", re: /(?<![.\w/$])register(?:s|ed)?\b(?!\.[A-Za-z_$])/i },
	{ word: "decision", re: /(?<![.\w/$])decisions?\b(?!\.[A-Za-z_$])/i },
	{ word: "ruling", re: /(?<![.\w/$])rulings?\b(?!\.[A-Za-z_$])/i },
];

/** Phrases that mean "audit whether everything was recorded" (full checklist). */
export const AUDIT_PHRASES: ReadonlyArray<RegExp> = [
	/\b(?:was|is|has)\s+everything\s+(?:been\s+)?(?:recorded|documented|written\s+down)\b/i,
	/\bdid\s+you\s+(?:document|record|write\s+(?:it\s+|this\s+|that\s+)?down)\b/i,
	/\beverything\s+(?:was\s+|is\s+)?(?:recorded|documented)\b/i,
];

/** Remove fenced code blocks, inline code spans and URLs before matching. */
export function stripCode(text: string): string {
	return text
		.replace(/```[\s\S]*?(?:```|$)/g, " ")
		.replace(/~~~[\s\S]*?(?:~~~|$)/g, " ")
		.replace(/`[^`\n]*`/g, " ")
		.replace(/\bhttps?:\/\/\S+/gi, " ");
}

export interface TriggerMatch {
	words: string[];
	audit: boolean;
}

/** Which trigger words appear in prose (code and URLs ignored). Null when none. */
export function detect(text: string): TriggerMatch | null {
	if (!text) return null;
	const prose = stripCode(text);
	const words = TRIGGERS.filter((t) => t.re.test(prose)).map((t) => t.word);
	const audit = AUDIT_PHRASES.some((re) => re.test(prose));
	if (!words.length && !audit) return null;
	return { words, audit };
}

/** SKILL.md without its YAML frontmatter. */
export function skillBody(markdown: string): string {
	const m = /^---\r?\n[\s\S]*?\r?\n---\r?\n?/.exec(markdown);
	return (m ? markdown.slice(m[0].length) : markdown).trim();
}

export function buildInjection(match: TriggerMatch, body: string): string {
	const why = match.audit
		? "The user is asking whether everything was recorded. Answer from the audit " +
		  "procedure below (all 7 steps), not from memory, and report any gaps plainly."
		: `Trigger word(s) detected: ${match.words.join(", ")}. The documentation ` +
		  "procedure below applies to this turn.";
	return [
		"[kb-document extension \u2014 injected automatically, decision D19]",
		why,
		"Source: .pi/skills/kb-document/SKILL.md (the single source of this procedure).",
		"",
		body,
	].join("\n");
}

/** mtime+size fingerprint per path; absent files are simply missing keys. */
export type Snapshot = Record<string, string>;

export function changedPaths(before: Snapshot, after: Snapshot): string[] {
	const keys = new Set([...Object.keys(before), ...Object.keys(after)]);
	// Paths are strings: plain code-point order is intended (stable, locale-independent).
	return [...keys].filter((k) => before[k] !== after[k]).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

export const MAX_FIX_ATTEMPTS = 2;

export interface SettleState {
	/** Set when a user prompt starts a run; null between prompts. */
	baseline: Snapshot | null;
	audit: boolean;
	attempts: number;
}

export function freshState(): SettleState {
	return { baseline: null, audit: false, attempts: 0 };
}

export type SettleAction =
	| { kind: "skip"; reason: string }
	| { kind: "check"; changed: string[] };

/** Should the end-of-run boundary run the checker? */
export function shouldCheck(state: SettleState, now: Snapshot): SettleAction {
	if (!state.baseline) return { kind: "skip", reason: "no user run in progress" };
	const changed = changedPaths(state.baseline, now);
	if (!changed.length && !state.audit) return { kind: "skip", reason: "knowledge base unchanged" };
	return { kind: "check", changed };
}

export interface CheckResult {
	ok: boolean;
	/** Checker never ran (no python, crash): never block the user on our own failure. */
	unavailable?: boolean;
	output: string;
}

export type Verdict =
	| { kind: "pass" }
	| { kind: "unavailable"; output: string }
	| { kind: "retry"; message: string }
	| { kind: "give-up"; output: string };

export function verdict(state: SettleState, result: CheckResult, changed: string[]): Verdict {
	if (result.unavailable) return { kind: "unavailable", output: result.output };
	if (result.ok) return { kind: "pass" };
	if (state.attempts >= MAX_FIX_ATTEMPTS) return { kind: "give-up", output: result.output };
	const lines = result.output.split(/\r?\n/).filter((l) => /^(ERROR|WARN)\b/.test(l));
	const shown = lines.slice(0, 40);
	const message = [
		`[kb-document extension] The knowledge-base check failed after this run ` +
			`(attempt ${state.attempts + 1}/${MAX_FIX_ATTEMPTS}).`,
		changed.length ? `Changed: ${changed.join(", ")}` : "Triggered by an audit request.",
		"Fix every item below, then run `python .pi/tools/check_kb.py --index` unpiped and confirm exit 0.",
		"",
		...shown,
		lines.length > shown.length ? `\u2026 and ${lines.length - shown.length} more` : "",
	]
		.filter((l, i, a) => l !== "" || i < a.length - 1)
		.join("\n");
	return { kind: "retry", message };
}

/** Walk up from `start` to the folder holding `.pi/tools/check_kb.py`; stop at a git root. */
export function findRepoRoot(
	start: string,
	probe: { exists(path: string): boolean; join(...p: string[]): string; dirname(p: string): string },
): string | null {
	let dir = start;
	for (let i = 0; i < 64; i++) {
		if (probe.exists(probe.join(dir, ".pi", "tools", "check_kb.py"))) return dir;
		if (probe.exists(probe.join(dir, ".git"))) return null; // reached repo root without the tool
		const parent = probe.dirname(dir);
		if (parent === dir) return null;
		dir = parent;
	}
	return null;
}
