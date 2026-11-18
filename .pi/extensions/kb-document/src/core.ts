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
	/** D25: the user prompt that started the run, and the latest assistant reply text. */
	prompt: string;
	reply: string;
	commitAttempts: number;
}

export function freshState(): SettleState {
	return { baseline: null, audit: false, attempts: 0, prompt: "", reply: "", commitAttempts: 0 };
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
		"Fix every item below, then run `python .pi/scripts/check_kb.py --index` unpiped and confirm exit 0.",
		"",
		...shown,
		lines.length > shown.length ? `\u2026 and ${lines.length - shown.length} more` : "",
	]
		.filter((l, i, a) => l !== "" || i < a.length - 1)
		.join("\n");
	return { kind: "retry", message };
}

// ---------------------------------------------------------------------------
// D25: commitment gate + session-start priming
// ---------------------------------------------------------------------------

type Pattern = { label: string; re: RegExp };

/** Assistant-side: promises about the future, recommendations, questions put to the operator. */
export const REPLY_PATTERNS: ReadonlyArray<Pattern> = [
	{ label: "conditional promise", re: /\b(?:when|once|as soon as)\s+you(?:'re|\s+are)?\b/i },
	{ label: "next session", re: /\b(?:next|new|fresh)\s+session\b/i },
	{ label: "after the reboot", re: /\bafter\s+(?:the|your|a)\s+reboot\b/i },
	{ label: "promise to remember", re: /\bI(?:'ll|\s+will)\s+(?:remember|keep\s+(?:that|this|it)\s+in\s+mind|pick\s+(?:it|this|that)\s+up|follow\s+up|come\s+back)\b/i },
	{ label: "standing promise", re: /\b(?:from\s+now\s+on|going\s+forward|next\s+time)\b/i },
	{ label: "recommendation", re: /\b(?:I\s+recommend|my\s+recommendation|I'd\s+(?:use|pick|choose|go\s+with)|my\s+preference)\b/i },
	{ label: "question to the operator", re: /\b(?:do\s+you\s+want|shall\s+I|should\s+I)\b[^?\n]{0,160}\?/i },
];

/** User-side: preferences, rulings, facts about the setup. */
export const PROMPT_PATTERNS: ReadonlyArray<Pattern> = [
	{ label: "operator preference", re: /\bI\s+(?:want|prefer|need|decided|chose|installed|use|don't\s+use|do\s+not\s+use)\b/i },
	{ label: "operator fact", re: /\bI\s+know\s+(?:for\s+(?:a\s+)?fact|that)\b/i },
	{ label: "operator choice", re: /\bmy\s+(?:preference|choice|decision|setup)\b/i },
	{ label: "team direction", re: /\b(?:let's|we(?:'ll|\s+will|\s+should))\s+(?:use|go\s+with|keep|switch|stick)\b/i },
	{ label: "memory concern", re: /\bremember\b/i },
	{ label: "standing rule", re: /\b(?:always|never)\s+(?:do|use|run|commit|push|ask)\b/i },
];

/** The model's explicit opt-out line. */
export const NO_RECORD_RE = /^\s*(?:[*_>]+\s*)?no record needed:/im;
export const MAX_COMMIT_ATTEMPTS = 1;

export interface CommitmentHit {
	side: "reply" | "prompt";
	label: string;
	excerpt: string;
}

function excerptAround(text: string, index: number): string {
	const start = text.lastIndexOf("\n", index) + 1;
	const endNl = text.indexOf("\n", index);
	const line = text.slice(start, endNl === -1 ? undefined : endNl).trim().replace(/\s+/g, " ");
	return line.length > 140 ? `${line.slice(0, 137)}...` : line;
}

function scan(text: string, side: CommitmentHit["side"], patterns: ReadonlyArray<Pattern>): CommitmentHit[] {
	const prose = stripCode(text ?? "");
	const hits: CommitmentHit[] = [];
	for (const p of patterns) {
		const m = p.re.exec(prose);
		if (m) hits.push({ side, label: p.label, excerpt: excerptAround(prose, m.index) });
	}
	return hits;
}

/** Commitments in this run's reply and prompt (code and URLs ignored). Empty when none. */
export function detectCommitments(prompt: string, reply: string): CommitmentHit[] {
	return [...scan(reply, "reply", REPLY_PATTERNS), ...scan(prompt, "prompt", PROMPT_PATTERNS)];
}

export type CommitmentAction = { kind: "skip"; reason: string } | { kind: "nudge"; message: string };

/** Called only when the KB is unchanged this run. */
export function commitmentGate(state: SettleState, outcome?: string): CommitmentAction {
	if (!state.baseline) return { kind: "skip", reason: "no user run in progress" };
	if (outcome && outcome !== "completed") return { kind: "skip", reason: `run ${outcome}` };
	if (state.commitAttempts >= MAX_COMMIT_ATTEMPTS) return { kind: "skip", reason: "already nudged" };
	if (NO_RECORD_RE.test(state.reply)) return { kind: "skip", reason: "model opted out" };
	const hits = detectCommitments(state.prompt, state.reply);
	if (!hits.length) return { kind: "skip", reason: "nothing to record" };
	return { kind: "nudge", message: buildCommitmentNudge(hits) };
}

export function buildCommitmentNudge(hits: CommitmentHit[]): string {
	return [
		"[kb-document extension \u2014 commitment gate, decision D25]",
		"This run changed nothing in .pi/knowledge/ or AGENTS.md, but it contains:",
		...hits.map((h) => `- ${h.side === "reply" ? "your reply" : "operator"} \u2014 ${h.label}: "${h.excerpt}"`),
		"",
		"Memory is volatile: a promise, recommendation, operator preference or open question that exists",
		"only in chat is lost at the next session. Record it now: operator rulings, preferences, facts and",
		"open questions in .pi/knowledge/open-decisions.md (quoted, dated); future promises as a",
		"trigger -> action item in .pi/knowledge/next-actions.md. Then run",
		"`python .pi/scripts/check_kb.py --index` and tell the operator in one line where it was recorded.",
		"If nothing here needs recording, reply with one line starting `No record needed:` and the reason.",
	].join("\n");
}

/** Plain text of the last assistant message in an `agent_end` message list. */
export function lastAssistantText(messages: unknown): string {
	if (!Array.isArray(messages)) return "";
	for (let i = messages.length - 1; i >= 0; i--) {
		const m: any = messages[i];
		if (m?.role !== "assistant") continue;
		if (typeof m.content === "string") return m.content;
		if (!Array.isArray(m.content)) continue;
		const text = m.content.filter((c: any) => c?.type === "text" && typeof c.text === "string").map((c: any) => c.text).join("\n");
		if (text.trim()) return text;
	}
	return "";
}

/** The `## Pending` section of next-actions.md, wrapped for injection; null when it has no items. */
export function nextActionsInjection(markdown: string): string | null {
	const m = /^## Pending[^\n]*\n([\s\S]*?)(?=^## |(?![\s\S]))/m.exec(markdown ?? "");
	if (!m || !/^\s*(?:\d+\.|[-*])\s+\S/m.test(m[1])) return null;
	return [
		"[kb-document extension \u2014 session priming, decision D25]",
		"Pending commitments from earlier sessions (.pi/knowledge/next-actions.md). If the operator's",
		"message matches a trigger below, do that action first. Remove an item once it is done and logged.",
		"",
		m[1].trim(),
	].join("\n");
}

/** Walk up from `start` to the folder holding `.pi/scripts/check_kb.py`; stop at a git root. */
export function findRepoRoot(
	start: string,
	probe: { exists(path: string): boolean; join(...p: string[]): string; dirname(p: string): string },
): string | null {
	let dir = start;
	for (let i = 0; i < 64; i++) {
		if (probe.exists(probe.join(dir, ".pi", "scripts", "check_kb.py"))) return dir;
		if (probe.exists(probe.join(dir, ".git"))) return null; // reached repo root without the tool
		const parent = probe.dirname(dir);
		if (parent === dir) return null;
		dir = parent;
	}
	return null;
}
