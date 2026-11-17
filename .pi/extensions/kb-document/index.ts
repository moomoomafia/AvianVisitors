/**
 * kb-document — project extension for the AvianVisitors knowledge base (decision D19).
 *
 * 1. `before_agent_start`: when the user's prompt contains a trigger word (document, record,
 *    write down, note this, register, decision, ruling, or "was everything recorded"),
 *    inject `.pi/skills/kb-document/SKILL.md` into the turn. Deterministic: does not rely
 *    on the model choosing to open the skill.
 * 2. `agent_before_settle`: if the run changed `.pi/knowledge/` or `AGENTS.md` (or the user
 *    asked for an audit), run `python .pi/tools/check_kb.py --verify-index`; on failure
 *    send the errors back and request a continuation, at most MAX_FIX_ATTEMPTS times.
 * 3. `/kb-check`: run the checker on demand.
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
	detect,
	findRepoRoot,
	freshState,
	shouldCheck,
	skillBody,
	verdict,
	type CheckResult,
	type Snapshot,
} from "./src/core.ts";

const SKILL = path.join(".pi", "skills", "kb-document", "SKILL.md");
const CHECKER = path.join(".pi", "tools", "check_kb.py");
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
	const rootOf = (cwd: string) =>
		findRepoRoot(cwd, { exists: fs.existsSync, join: path.join, dirname: path.dirname });
	const notify = (ctx: any, text: string, level: "info" | "warning" | "error" = "info") => {
		if (ctx?.hasUI) ctx.ui?.notify?.(text, level);
	};

	pi.on("before_agent_start", async (event, ctx) => {
		if (event?.messageType !== "user") return; // our own continuation / custom messages
		const root = rootOf(ctx?.cwd ?? process.cwd());
		if (!root) return;
		const match = detect(String(event.prompt ?? ""));
		state = { baseline: snapshot(root), audit: Boolean(match?.audit), attempts: 0 };
		if (!match) return;
		let body: string;
		try {
			body = skillBody(fs.readFileSync(path.join(root, SKILL), "utf8"));
		} catch {
			notify(ctx, `kb-document: ${SKILL} is missing; trigger ignored`, "warning");
			return;
		}
		notify(ctx, `kb-document: documentation procedure injected (${match.audit ? "audit" : match.words.join(", ")})`);
		return { message: { customType: "kb-document", content: buildInjection(match, body), display: false } };
	});

	pi.on("agent_before_settle", async (event, ctx) => {
		const root = rootOf(ctx?.cwd ?? process.cwd());
		if (!root) return;
		const action = shouldCheck(state, snapshot(root));
		if (action.kind === "skip") return;
		const result = await runChecker(pi, root);
		const v = verdict(state, result, action.changed);
		if (v.kind === "pass") {
			state = freshState();
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
		description: "Run the knowledge-base checker (.pi/tools/check_kb.py --verify-index)",
		handler: async (_args, ctx) => {
			const root = rootOf(ctx?.cwd ?? process.cwd());
			if (!root) return notify(ctx, "kb-check: not inside the AvianVisitors repo", "warning");
			const r = await runChecker(pi, root);
			const summary = r.output.split(/\r?\n/).find((l) => / docs \| /.test(l)) ?? r.output.trim();
			notify(ctx, `kb-check: ${r.ok ? "PASS" : r.unavailable ? "UNAVAILABLE" : "FAIL"} \u2014 ${summary}`, r.ok ? "info" : "error");
		},
	});
}
