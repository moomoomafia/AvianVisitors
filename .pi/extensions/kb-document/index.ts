/**
 * kb-document — project extension for the AvianVisitors knowledge base (decision D19).
 *
 * 1. `before_agent_start`: when the user's prompt contains a trigger word (document, record,
 *    write down, note this, register, decision, ruling, or "was everything recorded"),
 *    inject `.pi/skills/kb-document/SKILL.md` into the turn. Deterministic: does not rely
 *    on the model choosing to open the skill.
 * 2. `agent_before_settle`: if the run changed `.pi/knowledge/` or `AGENTS.md` (or the user
 *    asked for an audit), run `python .pi/scripts/check_kb.py --verify-index`; on failure
 *    send the errors back and request a continuation, at most MAX_FIX_ATTEMPTS times.
 * 3. `/kb-check`: run the checker on demand.
 * 4. D25 commitment gate (`agent_end` + `agent_before_settle`): when the KB is unchanged but
 *    the reply holds a promise/recommendation/question, or the prompt holds an operator
 *    preference/ruling/fact, request ONE continuation to record it (or opt out with
 *    "No record needed: ...").
 * 5. D25 session priming (`session_start` + first user prompt): inject the `## Pending` section
 *    of `.pi/knowledge/next-actions.md`, so commitments reach a fresh session automatically.
 *
 * Project-local: loads only after the project is trusted. This is the only file that
 * touches Pi or the filesystem; `src/core.ts` is pure and unit-tested.
 *
 * Deliberately imports nothing from `@earendil-works/*`: the three Pi methods used are
 * described by `PiSurface` below (Pi 1.5.2 docs/extensions.md), so the file type-checks
 * and tests without a machine-specific path to the Pi install, and Pi's real API object
 * (a superset) satisfies it structurally at runtime.
 */
import * as fs from "node:fs";
import * as path from "node:path";
import {
	buildInjection,
	commitmentGate,
	detect,
	lastAssistantText,
	nextActionsInjection,
	findRepoRoot,
	freshState,
	shouldCheck,
	skillBody,
	verdict,
	type CheckResult,
	type Snapshot,
} from "./src/core.ts";

const SKILL = path.join(".pi", "skills", "kb-document", "SKILL.md");
const CHECKER = path.join(".pi", "scripts", "check_kb.py");
const NEXT_ACTIONS = path.join(".pi", "knowledge", "next-actions.md");
const PYTHONS = process.platform === "win32" ? ["python", "py"] : ["python3", "python"];

/** Minimal slice of Pi's API this extension uses (keeps tests independent of Pi). */
export interface PiSurface {
	on(event: string, handler: (event: any, ctx: any) => unknown): void;
	registerCommand(name: string, options: { description: string; handler: (args: string, ctx: any) => unknown }): void;
	exec(command: string, args: string[], options?: { cwd?: string; timeout?: number }): Promise<{ stdout: string; stderr: string; code: number | null }>;
}

export function snapshot(root: string): Snapshot {
	const out: Snapshot = {};
	const add = (p: string) => {
		try {
			const s = fs.statSync(p);
			if (s.isFile()) out[path.relative(root, p).split(path.sep).join("/")] = `${s.mtimeMs}:${s.size}`;
		} catch {
			/* absent file: no key */
		}
	};
	add(path.join(root, "AGENTS.md"));
	const kb = path.join(root, ".pi", "knowledge");
	try {
		for (const name of fs.readdirSync(kb)) if (name.endsWith(".md")) add(path.join(kb, name));
	} catch {
		/* no knowledge dir */
	}
	return out;
}

async function runChecker(pi: PiSurface, root: string): Promise<CheckResult> {
	for (const py of PYTHONS) {
		try {
			const r = await pi.exec(py, [path.join(root, CHECKER), "--verify-index"], { cwd: root, timeout: 120_000 });
			const output = `${r.stdout ?? ""}${r.stderr ?? ""}`;
			if (r.code === 0) return { ok: true, output };
			if (/ERROR|WARN|docs \|/.test(output)) return { ok: false, output };
			// Interpreter missing or crashed before producing a report: try the next one.
		} catch {
			/* not on PATH */
		}
	}
	return { ok: false, unavailable: true, output: `could not run ${CHECKER} with ${PYTHONS.join(" / ")}` };
}

export default function kbDocument(pi: PiSurface): void {
	let state = freshState();
	let primed = false; // D25: next-actions injected for this session yet?
	const rootOf = (cwd: string) =>
		findRepoRoot(cwd, { exists: fs.existsSync, join: path.join, dirname: path.dirname });
	const notify = (ctx: any, text: string, level: "info" | "warning" | "error" = "info") => {
		if (ctx?.hasUI) ctx.ui?.notify?.(text, level);
	};

	pi.on("session_start", async () => {
		primed = false;
		state = freshState();
	});

	pi.on("before_agent_start", async (event, ctx) => {
		if (event?.messageType !== "user") return; // our own continuation / custom messages
		const root = rootOf(ctx?.cwd ?? process.cwd());
		if (!root) return;
		const prompt = String(event.prompt ?? "");
		const match = detect(prompt);
		state = { ...freshState(), baseline: snapshot(root), audit: Boolean(match?.audit), prompt };
		const parts: string[] = [];
		if (!primed) {
			primed = true;
			try {
				const pending = nextActionsInjection(fs.readFileSync(path.join(root, NEXT_ACTIONS), "utf8"));
				if (pending) {
					parts.push(pending);
					notify(ctx, "kb-document: pending next-actions injected");
				}
			} catch {
				/* no next-actions file: nothing pending */
			}
		}
		if (match) {
			try {
				parts.push(buildInjection(match, skillBody(fs.readFileSync(path.join(root, SKILL), "utf8"))));
				notify(ctx, `kb-document: documentation procedure injected (${match.audit ? "audit" : match.words.join(", ")})`);
			} catch {
				notify(ctx, `kb-document: ${SKILL} is missing; trigger ignored`, "warning");
			}
		}
		if (!parts.length) return;
		return { message: { customType: "kb-document", content: parts.join("\n\n---\n\n"), display: false } };
	});

	pi.on("agent_end", async (event) => {
		const text = lastAssistantText(event?.messages);
		if (text) state.reply = text;
	});

	pi.on("agent_before_settle", async (event, ctx) => {
		const root = rootOf(ctx?.cwd ?? process.cwd());
		if (!root) return;
		const action = shouldCheck(state, snapshot(root));
		if (action.kind === "skip") {
			const gate = commitmentGate(state, event?.outcome);
			if (gate.kind === "skip") return;
			state.commitAttempts += 1;
			notify(ctx, "kb-document: unrecorded commitment detected; asking for a record", "warning");
			return {
				entries: [
					...(event?.entries ?? []),
					{ type: "custom_message", customType: "kb-document-commitment", content: gate.message, display: true },
				],
				continue: true,
			};
		}
		const result = await runChecker(pi, root);
		const v = verdict(state, result, action.changed);
		if (v.kind === "pass") {
			state = freshState(); // a KB edit this run counts as recording (D25 gate not applied)
			return;
		}
		if (v.kind === "unavailable") {
			notify(ctx, `kb-document: checker unavailable (${v.output}); knowledge base NOT verified`, "warning");
			state = freshState();
			return;
		}
		if (v.kind === "give-up") {
			notify(ctx, "kb-document: knowledge-base check still failing after retries \u2014 run /kb-check", "error");
			state = freshState();
			return;
		}
		state.attempts += 1;
		return {
			entries: [
				...(event?.entries ?? []),
				{ type: "custom_message", customType: "kb-document-check", content: v.message, display: true },
			],
			continue: true,
		};
	});

	pi.registerCommand("kb-check", {
		description: "Run the knowledge-base checker (.pi/scripts/check_kb.py --verify-index)",
		handler: async (_args, ctx) => {
			const root = rootOf(ctx?.cwd ?? process.cwd());
			if (!root) return notify(ctx, "kb-check: not inside the AvianVisitors repo", "warning");
			const r = await runChecker(pi, root);
			const summary = r.output.split(/\r?\n/).find((l) => / docs \| /.test(l)) ?? r.output.trim();
			notify(ctx, `kb-check: ${r.ok ? "PASS" : r.unavailable ? "UNAVAILABLE" : "FAIL"} \u2014 ${summary}`, r.ok ? "info" : "error");
		},
	});
}
