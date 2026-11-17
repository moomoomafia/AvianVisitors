import assert from "node:assert/strict";
import * as path from "node:path";
import { test } from "node:test";
import {
	buildInjection,
	changedPaths,
	detect,
	findRepoRoot,
	freshState,
	MAX_FIX_ATTEMPTS,
	shouldCheck,
	skillBody,
	stripCode,
	verdict,
} from "../src/core.ts";

test("operator's trigger words fire (D19 ruling)", () => {
	for (const [text, word] of [
		["please document this", "document"],
		["is it documented?", "document"],
		["update the documentation", "document"],
		["record that in the log", "record"],
		["was it recorded", "record"],
		["write this down", "write down"],
		["write it down please", "write down"],
		["note this for later", "note this"],
		["add it to the register", "register"],
		["that decision is wrong", "decision"],
		["record my ruling", "ruling"],
	] as const) {
		assert.ok(detect(text)?.words.includes(word), `${JSON.stringify(text)} should trigger ${word}`);
	}
});

test("audit phrases set audit mode", () => {
	for (const text of [
		"was everything recorded?",
		"Was everything documented per the agent.md?",
		"did you document it?",
		"has everything been recorded",
		"make sure everything was documented",
	]) {
		assert.equal(detect(text)?.audit, true, text);
	}
	assert.equal(detect("please document this")?.audit, false);
});

test("code, identifiers, paths and URLs do not fire", () => {
	for (const text of [
		"why does document.querySelector return null",
		"see `document the thing` in code",
		"```js\nconst decision = record.register();\n```",
		"open https://example.com/document/ruling",
		"edit docs/document now",
		"the recording service restarted",
		"recordings are in By_Date",
		"documentary about birds",
		"",
	]) {
		assert.equal(detect(text), null, JSON.stringify(text));
	}
});

test("a real prompt with code still fires on its prose", () => {
	const m = detect("Fix `document.title` and then document the change.");
	assert.deepEqual(m, { words: ["document"], audit: false });
});

test("stripCode removes fences, inline spans and URLs", () => {
	assert.equal(stripCode("a ```x``` b `y` c http://z/q d").replace(/\s+/g, " "), "a b c d");
	assert.equal(stripCode("unterminated ```fence document").trim(), "unterminated");
});

test("skillBody drops YAML frontmatter only", () => {
	assert.equal(skillBody("---\nname: x\ndescription: y\n---\n\n# Title\nbody"), "# Title\nbody");
	assert.equal(skillBody("# No frontmatter"), "# No frontmatter");
	assert.equal(skillBody("---\r\nname: x\r\n---\r\nwin"), "win");
});

test("injection names the trigger and the audit duty", () => {
	assert.match(buildInjection({ words: ["record"], audit: false }, "BODY"), /record[\s\S]*BODY$/);
	assert.match(buildInjection({ words: [], audit: true }, "B"), /not from memory/);
});

test("changedPaths covers modified, added and deleted files", () => {
	assert.deepEqual(changedPaths({ a: "1", b: "1", c: "1" }, { a: "1", b: "2", d: "1" }), ["b", "c", "d"]);
	assert.deepEqual(changedPaths({ a: "1" }, { a: "1" }), []);
});

test("checker runs only when the KB changed or an audit was asked", () => {
	assert.equal(shouldCheck(freshState(), {}).kind, "skip");
	const base = { "AGENTS.md": "1" };
	assert.equal(shouldCheck({ baseline: base, audit: false, attempts: 0 }, base).kind, "skip");
	assert.deepEqual(shouldCheck({ baseline: base, audit: false, attempts: 0 }, { "AGENTS.md": "2" }), {
		kind: "check",
		changed: ["AGENTS.md"],
	});
	assert.equal(shouldCheck({ baseline: base, audit: true, attempts: 0 }, base).kind, "check");
});

test("verdict: pass, unavailable never blocks, bounded retries", () => {
	const s = { baseline: {}, audit: false, attempts: 0 };
	assert.equal(verdict(s, { ok: true, output: "" }, []).kind, "pass");
	assert.equal(verdict(s, { ok: false, unavailable: true, output: "no python" }, []).kind, "unavailable");
	const failing = { ok: false, output: "ERROR   a.md:1: broken link -> x\nWARN   b\n19 docs | 1 errors" };
	const r = verdict(s, failing, [".pi/knowledge/a.md"]);
	assert.equal(r.kind, "retry");
	assert.ok(r.kind === "retry" && r.message.includes("broken link") && r.message.includes("1/2"));
	assert.equal(verdict({ ...s, attempts: MAX_FIX_ATTEMPTS }, failing, []).kind, "give-up");
});

test("findRepoRoot stops at the git root and never climbs past it", () => {
	const files = new Set([path.join("/r", ".pi", "tools", "check_kb.py"), path.join("/r", ".git")]);
	const probe = { exists: (p: string) => files.has(p), join: path.join, dirname: path.dirname };
	// path.join normalises separators per platform ("/r" -> "\\r" on Windows).
	assert.equal(findRepoRoot(path.join("/r", "frame", "x"), probe), path.join("/r"));
	// A home-like folder above a repo that lacks the tool must not be selected.
	const other = new Set([path.join("/home", ".pi", "tools", "check_kb.py"), path.join("/home", "proj", ".git")]);
	const probe2 = { exists: (p: string) => other.has(p), join: path.join, dirname: path.dirname };
	assert.equal(findRepoRoot(path.join("/home", "proj", "src"), probe2), null);
});
