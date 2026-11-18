/**
 * Drives the real index.ts with a fake `pi`: proves event names, return shapes, the
 * exit-0 decline semantics and the bounded retry loop without Pi or a model.
 */
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { afterEach, beforeEach, test } from "node:test";
import kbDocument from "../index.ts";
import { MAX_FIX_ATTEMPTS } from "../src/core.ts";

type Handler = (event: any, ctx: any) => unknown;

let repo: string;
let notes: Array<[string, string]>;

function makeRepo(): string {
	const dir = fs.mkdtempSync(path.join(os.tmpdir(), "kbdoc-wiring-"));
	// A .git marker stops the root search here (never climbs into the real home folder).
	fs.mkdirSync(path.join(dir, ".git"));
	fs.mkdirSync(path.join(dir, ".pi", "scripts"), { recursive: true });
	fs.writeFileSync(path.join(dir, ".pi", "scripts", "check_kb.py"), "# stub\n");
	fs.mkdirSync(path.join(dir, ".pi", "skills", "kb-document"), { recursive: true });
	fs.writeFileSync(path.join(dir, ".pi", "skills", "kb-document", "SKILL.md"),
		"---\nname: kb-document\ndescription: d\n---\n\nSKILL-BODY-MARKER\n");
	fs.mkdirSync(path.join(dir, ".pi", "knowledge"));
	fs.writeFileSync(path.join(dir, ".pi", "knowledge", "a.md"), "# A\n");
	fs.writeFileSync(path.join(dir, "AGENTS.md"), "# agents\n");
	return dir;
}

function load(execResult: () => { stdout: string; stderr: string; code: number | null }) {
	const handlers: Record<string, Handler> = {};
	const commands: Record<string, Handler> = {};
	const calls: string[][] = [];
	kbDocument({
		on: (name, h) => { handlers[name] = h; },
		registerCommand: (name, o) => { commands[name] = (args, ctx) => o.handler(args, ctx); },
		exec: async (cmd, args) => { calls.push([cmd, ...args]); return execResult(); },
	});
	const ctx = { cwd: path.join(repo, ".pi"), hasUI: true, ui: { notify: (t: string, l: string) => notes.push([l, t]) } };
	return { handlers, commands, calls, ctx };
}

const PASS = { stdout: "\n19 docs | 0 errors | 0 warnings | 1 source files cited\n", stderr: "", code: 0 };
const FAIL = { stdout: "ERROR   .pi/knowledge/a.md:1: broken link -> x.md\n\n1 docs | 1 errors | 0 warnings\n", stderr: "", code: 1 };

beforeEach(() => { repo = makeRepo(); notes = []; });
afterEach(() => { fs.rmSync(repo, { recursive: true, force: true }); });

test("registers the documented hooks (D19 + D25)", () => {
	const { handlers, commands } = load(() => PASS);
	assert.deepEqual(Object.keys(handlers).sort(), ["agent_before_settle", "agent_end", "before_agent_start", "session_start"]);
	assert.deepEqual(Object.keys(commands), ["kb-check"]);
});

test("trigger word injects the SKILL.md body (frontmatter stripped)", async () => {
	const { handlers, ctx } = load(() => PASS);
	const r: any = await handlers.before_agent_start({ messageType: "user", prompt: "please document this" }, ctx);
	assert.equal(r.message.customType, "kb-document");
	assert.match(r.message.content, /SKILL-BODY-MARKER/);
	assert.doesNotMatch(r.message.content, /^name: kb-document/m);
	assert.ok(notes.some(([, t]) => /injected/.test(t)));
});

test("no trigger, code-only mention, and custom-message runs inject nothing", async () => {
	const { handlers, ctx } = load(() => PASS);
	assert.equal(await handlers.before_agent_start({ messageType: "user", prompt: "fix the bug" }, ctx), undefined);
	assert.equal(await handlers.before_agent_start({ messageType: "user", prompt: "why is `document` null" }, ctx), undefined);
	assert.equal(await handlers.before_agent_start({ messageType: "custom", prompt: "document" }, ctx), undefined);
});

test("unchanged KB: checker is not run at settle", async () => {
	const { handlers, calls, ctx } = load(() => FAIL);
	await handlers.before_agent_start({ messageType: "user", prompt: "fix the bug" }, ctx);
	assert.equal(await handlers.agent_before_settle({ entries: [] }, ctx), undefined);
	assert.equal(calls.length, 0);
});

test("changed KB + passing check: settles quietly", async () => {
	const { handlers, calls, ctx } = load(() => PASS);
	await handlers.before_agent_start({ messageType: "user", prompt: "fix the bug" }, ctx);
	fs.writeFileSync(path.join(repo, ".pi", "knowledge", "a.md"), "# A\nchanged\n");
	assert.equal(await handlers.agent_before_settle({ entries: [] }, ctx), undefined);
	assert.equal(calls.length, 1);
	assert.ok(calls[0].includes("--verify-index"), "runs the non-writing verify mode");
});

test("changed KB + failing check: bounded continuations, then gives up", async () => {
	const { handlers, ctx } = load(() => FAIL);
	await handlers.before_agent_start({ messageType: "user", prompt: "fix the bug" }, ctx);
	fs.writeFileSync(path.join(repo, "AGENTS.md"), "# agents\nedited\n");
	for (let i = 1; i <= MAX_FIX_ATTEMPTS; i++) {
		const r: any = await handlers.agent_before_settle({ entries: [{ type: "custom", tag: "prior" }] }, ctx);
		assert.equal(r.continue, true, `attempt ${i} requests a continuation`);
		assert.equal(r.entries[0].tag, "prior", "preserves earlier proposed entries");
		assert.match(r.entries.at(-1).content, /broken link/);
	}
	assert.equal(await handlers.agent_before_settle({ entries: [] }, ctx), undefined, "no endless loop");
	assert.ok(notes.some(([l, t]) => l === "error" && /still failing/.test(t)));
});

test("audit question runs the checker even with no KB change", async () => {
	const { handlers, calls, ctx } = load(() => PASS);
	const r: any = await handlers.before_agent_start({ messageType: "user", prompt: "was everything recorded?" }, ctx);
	assert.match(r.message.content, /not from memory/);
	await handlers.agent_before_settle({ entries: [] }, ctx);
	assert.equal(calls.length, 1);
});

test("missing python never blocks the user", async () => {
	const { handlers, ctx } = load(() => ({ stdout: "", stderr: "not found", code: 9009 }));
	await handlers.before_agent_start({ messageType: "user", prompt: "was everything recorded?" }, ctx);
	assert.equal(await handlers.agent_before_settle({ entries: [] }, ctx), undefined);
	assert.ok(notes.some(([l, t]) => l === "warning" && /NOT verified/.test(t)));
});

test("outside the repo the extension is inert", async () => {
	const { handlers } = load(() => FAIL);
	const outside = fs.mkdtempSync(path.join(os.tmpdir(), "kbdoc-outside-"));
	fs.mkdirSync(path.join(outside, ".git"));
	try {
		const ctx = { cwd: outside, hasUI: false };
		assert.equal(await handlers.before_agent_start({ messageType: "user", prompt: "document it" }, ctx), undefined);
		assert.equal(await handlers.agent_before_settle({ entries: [] }, ctx), undefined);
	} finally {
		fs.rmSync(outside, { recursive: true, force: true });
	}
});

// --- D25 ---------------------------------------------------------------------------------

const reply = (text: string) => ({ messages: [{ role: "assistant", content: [{ type: "text", text }] }] });
const PROMISE = "When you're back, tell me and I'll run the checks.";

test("D25: unrecorded promise with an unchanged KB requests exactly one continuation", async () => {
	const { handlers, calls, ctx } = load(() => PASS);
	await handlers.before_agent_start({ messageType: "user", prompt: "what next?" }, ctx);
	await handlers.agent_end(reply(PROMISE), ctx);
	const r: any = await handlers.agent_before_settle({ entries: [{ type: "custom", tag: "prior" }], outcome: "completed" }, ctx);
	assert.equal(r.continue, true);
	assert.equal(r.entries[0].tag, "prior", "preserves earlier proposed entries");
	assert.equal(r.entries.at(-1).customType, "kb-document-commitment");
	assert.match(r.entries.at(-1).content, /tell me/);
	assert.equal(calls.length, 0, "the checker is not involved");
	// The continuation's own run ends: still no KB change -> no second nudge.
	await handlers.agent_end(reply("No record needed: it was a hypothetical."), ctx);
	assert.equal(await handlers.agent_before_settle({ entries: [], outcome: "completed" }, ctx), undefined);
});

test("D25: if the continuation records it, the normal checker runs instead", async () => {
	const { handlers, calls, ctx } = load(() => PASS);
	await handlers.before_agent_start({ messageType: "user", prompt: "I want Docker" }, ctx);
	await handlers.agent_end(reply("ok"), ctx);
	assert.equal((await handlers.agent_before_settle({ entries: [] }, ctx) as any).continue, true, "operator preference nudges");
	fs.writeFileSync(path.join(repo, ".pi", "knowledge", "a.md"), "# A\nrecorded\n");
	assert.equal(await handlers.agent_before_settle({ entries: [] }, ctx), undefined);
	assert.equal(calls.length, 1);
});

test("D25: a run that already edited the KB is not nudged; aborted runs are not nudged", async () => {
	const { handlers, ctx } = load(() => PASS);
	await handlers.before_agent_start({ messageType: "user", prompt: "I want Docker" }, ctx);
	fs.writeFileSync(path.join(repo, "AGENTS.md"), "# agents\nrecorded\n");
	await handlers.agent_end(reply(PROMISE), ctx);
	assert.equal(await handlers.agent_before_settle({ entries: [] }, ctx), undefined);
	await handlers.before_agent_start({ messageType: "user", prompt: "I want Docker" }, ctx);
	await handlers.agent_end(reply(PROMISE), ctx);
	assert.equal(await handlers.agent_before_settle({ entries: [], outcome: "aborted" }, ctx), undefined);
});

test("D25: pending next-actions are injected on the first prompt of each session only", async () => {
	fs.writeFileSync(path.join(repo, ".pi", "knowledge", "next-actions.md"),
		"# Next actions\n\n## Pending\n\n1. **Trigger:** NEXT-MARKER. **Action:** do it.\n");
	const { handlers, ctx } = load(() => PASS);
	const first: any = await handlers.before_agent_start({ messageType: "user", prompt: "hello" }, ctx);
	assert.match(first.message.content, /NEXT-MARKER/);
	assert.equal(await handlers.before_agent_start({ messageType: "user", prompt: "hello again" }, ctx), undefined);
	await handlers.session_start({ reason: "resume" }, ctx);
	const both: any = await handlers.before_agent_start({ messageType: "user", prompt: "please document this" }, ctx);
	assert.match(both.message.content, /NEXT-MARKER[\s\S]*SKILL-BODY-MARKER/, "priming and skill share one message");
});

test("D25: no next-actions file, or an empty Pending section, injects nothing", async () => {
	const { handlers, ctx } = load(() => PASS);
	assert.equal(await handlers.before_agent_start({ messageType: "user", prompt: "hello" }, ctx), undefined);
	fs.writeFileSync(path.join(repo, ".pi", "knowledge", "next-actions.md"), "# N\n\n## Pending\n\n_(none)_\n");
	await handlers.session_start({ reason: "new" }, ctx);
	assert.equal(await handlers.before_agent_start({ messageType: "user", prompt: "hello" }, ctx), undefined);
});
