// Headless proof that the installed Pi loads this extension and skill.
// Usage (repo root): node .pi/extensions/kb-document/test/verify-in-pi.mjs
// Spawns `pi --mode rpc --no-session -ne -e <ext> -ns --skill <skill>` and calls
// get_commands (no model request is made). Exits 0 only if /kb-check and the
// kb-document skill are both registered and Pi reported no extension load error.
import { spawn } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const ext = path.resolve(here, "..", "index.ts");
const skill = path.resolve(here, "..", "..", "..", "skills", "kb-document", "SKILL.md");
const agentDir = process.env.PI_CODING_AGENT_DIR ?? path.join(os.homedir(), ".pi", "agent");
const version = fs.readFileSync(path.join(agentDir, "install", "current-version"), "utf8").trim();
const cli = path.join(agentDir, "install", "releases", version, "node_modules", "@earendil-works", "pi-coding-agent", "dist", "cli.js");

const child = spawn(process.execPath, [cli, "--mode", "rpc", "--no-session", "-ne", "-e", ext, "-ns", "--skill", skill], {
	cwd: path.resolve(here, "..", "..", "..", ".."),
	stdio: ["pipe", "pipe", "pipe"],
	windowsHide: true,
});
let out = "";
let err = "";
child.stdout.on("data", (d) => { out += d; tryFinish(); });
child.stderr.on("data", (d) => { err += d; });
const timer = setTimeout(() => finish(false, "timeout waiting for get_commands"), 60_000);
child.stdin.write(JSON.stringify({ id: "c1", type: "get_commands" }) + "\n");

function tryFinish() {
	for (const line of out.split(/\r?\n/)) {
		if (!line.trim().startsWith("{")) continue;
		let msg;
		try { msg = JSON.parse(line); } catch { continue; }
		if (msg.type === "response" && msg.id === "c1") {
			const cmds = msg.data?.commands ?? [];
			const names = cmds.map((c) => `${c.source}:${c.name}`);
			const hasCmd = cmds.some((c) => c.name === "kb-check");
			const hasSkill = cmds.some((c) => /kb-document/.test(c.name) && c.source === "skill");
			const loadErr = /extension.*(error|fail)|failed to load/i.test(err + out);
			console.log("commands:", names.join(", ") || "(none)");
			finish(msg.success && hasCmd && hasSkill && !loadErr,
				`success=${msg.success} kb-check=${hasCmd} skill=${hasSkill} loadError=${loadErr}`);
		}
	}
}

function finish(ok, detail) {
	clearTimeout(timer);
	console.log(ok ? "PASS" : "FAIL", detail);
	if (!ok && err.trim()) console.log("stderr:\n" + err.trim().slice(0, 2000));
	child.kill();
	process.exit(ok ? 0 : 1);
}
