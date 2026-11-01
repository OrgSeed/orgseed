// Tests for refuse_writes.js, with Node.js alone: no agent app and no model is involved.
//   node test_refuse_writes.mjs
// Each group makes a throwaway organization folder and an installed copy of the add-on, with settings of its own,
// in a temporary folder; calls the hook the agent app would call before a tool runs; and checks whether the write
// was refused, and with which message. What it cannot show: how the app itself calls the hook (try that inside the
// app, with the version you register). Exit code 0 when every check passed. Nothing outside the temporary folder
// is touched, and the folder is deleted at the end.
import { mkdtempSync, mkdirSync, writeFileSync, copyFileSync, readFileSync, rmSync, symlinkSync } from "node:fs"
import { join, dirname } from "node:path"
import { tmpdir } from "node:os"
import { fileURLToPath, pathToFileURL } from "node:url"

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = mkdtempSync(join(tmpdir(), "refuse-writes-test-"))
const RECORD_IT = "Record this as a decline with enforced_by refuse-writes."
let checks = 0
let failed = 0
let n = 0

function ok(name, cond, detail) {
  checks++
  if (!cond) failed++
  console.log((cond ? "  PASS  " : "  FAIL  ") + name + (!cond && detail ? "  [" + detail + "]" : ""))
}

// The rule's check is a program of its own: it reports any figure written with a decimal point.
const CHECK = 'let s="";process.stdin.on("data",(d)=>{s+=d}).on("end",()=>{const i=JSON.parse(s);' +
  'const m=String(i.content).match(/[0-9]+[.][0-9]+/);' +
  'process.stdout.write(JSON.stringify({violations:m?["a rounded figure "+m[0]]:[]}))})'

function organization() {
  const o = join(ROOT, "org" + ++n)
  mkdirSync(join(o, "records"), { recursive: true })
  mkdirSync(join(o, "work"))
  writeFileSync(join(o, "AGENTS.md"), "# AGENTS.md\n")
  writeFileSync(join(o, "records", "events.jsonl"), "")
  writeFileSync(join(o, "work", "a.md"), "a figure 12 as printed\n")
  return o
}

function settingsFor(o, more = {}) {
  return {
    organization: o, tool_id: "refuse-writes", refusal: "reasoned", records: true,
    log: join(ROOT, "log" + ++n + ".jsonl"), on_check_error: "allow",
    rules: [{ id: "OUR-1", reason: "figures are copied as printed", applies_to: "work/", check: [process.execPath, "-e", CHECK] }],
    ...more,
  }
}

// An installed copy: the add-on, unchanged, with its settings beside it (none, if settings is null).
async function install(settings) {
  const dir = join(ROOT, "plugins" + ++n)
  mkdirSync(dir)
  copyFileSync(join(HERE, "refuse_writes.js"), join(dir, "refuse_writes.js"))
  writeFileSync(join(dir, "package.json"), '{"type": "module"}\n')
  if (settings !== null) writeFileSync(join(dir, "refuse_writes.json"), JSON.stringify(settings))
  const mod = await import(pathToFileURL(join(dir, "refuse_writes.js")).href)
  const hook = (await mod.RefuseWrites())["tool.execute.before"]
  const tryit = async (tool, args) => {
    try {
      await hook({ tool, callID: "test" }, { args })
      return null
    } catch (e) {
      return e.message
    }
  }
  return { dir, tryit }
}

const patch = (...lines) => ["*** Begin Patch", ...lines, "*** End Patch"].join("\n")
const logLines = (s) => readFileSync(s.log, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l))

try {
  console.log("Records, rules and case (reasoned refusals)")
  {
    const o = organization()
    const s = settingsFor(o)
    const { dir, tryit } = await install(s)
    let refused = 0
    const no = async (name, tool, args, has = []) => {
      const m = await tryit(tool, args)
      if (m) refused++
      ok(name, m !== null && has.every((h) => m.includes(h)), String(m))
    }
    const yes = async (name, tool, args) => {
      const m = await tryit(tool, args)
      ok(name, m === null, String(m))
    }
    await no("a write into records/ is refused (CORE-4)", "write", { filePath: "records/events.jsonl", content: "{}" }, ["CORE-4"])
    await no("so is one by its full path", "write", { filePath: join(o, "records", "events.jsonl"), content: "{}" }, ["CORE-4"])
    await no("and one that spells records/ in other letters' case", "write", { filePath: "Records/Events.jsonl", content: "{}" }, ["CORE-4"])
    await no("and one that reaches records/ through work/..", "write", { filePath: "work/../records/events.jsonl", content: "{}" }, ["CORE-4"])
    await yes("a write in work/ that keeps the rule goes ahead", "write", { filePath: "work/b.md", content: "a figure 12 as printed" })
    await no("a write in work/ that breaks the rule is refused, with the rule, its reason, what was found, the record to make and the route to a change",
      "write", { filePath: "work/b.md", content: "a figure 12.5" },
      ["OUR-1", "figures are copied as printed", "a rounded figure 12.5", RECORD_IT, "propose a change to it"])
    await no("the rule's folder is matched whatever its letters' case", "write", { filePath: "Work/B.md", content: "12.5" }, ["OUR-1"])
    await no("an edit that breaks the rule is refused", "edit", { filePath: "work/a.md", oldString: "12", newString: "12.5" }, ["OUR-1"])
    await no("so is a multiedit", "multiedit", { filePath: "work/a.md", edits: [{ oldString: "12", newString: "12.5" }] }, ["OUR-1"])
    await no("a patch that changes a record is refused", "apply_patch",
      { patchText: patch("*** Update File: records/events.jsonl", "+{}") }, ["CORE-4"])
    await no("a patch with Windows line ends is read the same way", "apply_patch",
      { patchText: patch("*** Update File: records/events.jsonl", "+{}").replace(/\n/g, "\r\n") }, ["CORE-4"])
    await no("a patch that deletes a record is refused", "apply_patch", { patchText: patch("*** Delete File: records/events.jsonl") }, ["CORE-4"])
    await no("a patch that moves a file into records/ is refused", "apply_patch",
      { patchText: patch("*** Update File: work/a.md", "*** Move to: records/a.jsonl", "+{}") }, ["CORE-4"])
    await no("a patch that moves a record out of records/ is refused", "patch",
      { patchText: patch("*** Update File: records/events.jsonl", "*** Move to: work/e.md", "+x") }, ["CORE-4"])
    await no("a patch that adds a file breaking the rule is refused", "apply_patch",
      { patchText: patch("*** Add File: work/c.md", "+a figure 12.5") }, ["OUR-1"])
    await yes("a patch that adds a file keeping the rule goes ahead", "apply_patch",
      { patchText: patch("*** Add File: work/c.md", "+a figure 12 as printed") })
    await yes("a patch that deletes a work file goes ahead", "apply_patch", { patchText: patch("*** Delete File: work/a.md") })
    await no("a write to the add-on's own code is refused (CORE-9)", "write", { filePath: join(dir, "refuse_writes.js"), content: "" }, ["CORE-9"])
    await no("so is a write to its settings, in any letters' case", "edit",
      { filePath: join(dir, "REFUSE_WRITES.JSON"), oldString: "reasoned", newString: "bare" }, ["CORE-9"])
    await no("and a patch that deletes its settings", "apply_patch", { patchText: patch("*** Delete File: " + join(dir, "refuse_writes.json")) }, ["CORE-9"])
    await no("and a write to its log", "write", { filePath: s.log, content: "" }, ["CORE-9"])
    await yes("a write outside the organization's folder is not this add-on's to judge", "write", { filePath: join(ROOT, "elsewhere.md"), content: "12.5" })
    await yes("a shell command is not seen (the gap its README states)", "bash", { command: "echo 12.5 > work/d.md" })
    if (process.platform === "win32") {
      await no("Windows: a name with a trailing dot is read as the folder it names", "write", { filePath: "records./events.jsonl", content: "{}" }, ["CORE-4"])
      await no("Windows: a stream of a record is part of the record", "write", { filePath: "records/events.jsonl:s", content: "{}" }, ["CORE-4"])
    }
    let link = true
    try {
      symlinkSync(join(o, "records"), join(o, "work", "j"), "junction")
    } catch (e) {
      link = false
    }
    if (link) await no("a write through a link from work/ into records/ is refused", "write", { filePath: "work/j/x.jsonl", content: "{}" }, ["CORE-4"])
    const entries = logLines(s)
    ok("its log has one line for each write it refused", entries.filter((e) => e.event === "refused").length === refused,
      "refused " + refused + ", logged " + entries.filter((e) => e.event === "refused").length)
  }

  console.log("Bare refusals")
  {
    const o = organization()
    const reasoned = await install(settingsFor(o))
    const bare = await install(settingsFor(o, { refusal: "bare" }))
    const m = await bare.tryit("write", { filePath: "work/b.md", content: "12.5" })
    ok("a bare refusal says only that nothing was written, and asks for the decline record", m === "Refused. Nothing was written. " + RECORD_IT, String(m))
    const r = await reasoned.tryit("write", { filePath: "work/b.md", content: "12.5" })
    ok("the reasoned refusal asks for the decline record in the same words", r !== null && r.includes(RECORD_IT), String(r))
  }

  console.log("Settings that are wrong: every file-tool write is refused (it fails closed)")
  for (const [name, settings] of [
    ["the organization folder named holds no AGENTS.md", (o) => settingsFor(join(o, "work"))],
    ["no organization folder is named", (o) => settingsFor(undefined)],
    ["its log is inside the organization's folder", (o) => settingsFor(o, { log: join(o, "work", "log.jsonl") })],
    ["a rule has no check", (o) => settingsFor(o, { rules: [{ id: "OUR-1", applies_to: "work/" }] })],
    ["there are no settings beside it", () => null],
  ]) {
    const o = organization()
    const { tryit } = await install(settings(o))
    const a = await tryit("write", { filePath: join(o, "work", "b.md"), content: "12" })
    const b = await tryit("write", { filePath: join(ROOT, "elsewhere.md"), content: "12" })
    const c = await tryit("read", { filePath: join(o, "work", "a.md") })
    ok("when " + name + ": writes inside and outside the folder are refused, saying so; other tools are not touched",
      a !== null && a.includes("not running as set up") && b !== null && c === null, [a, b, c].join(" | "))
  }

  console.log("A check that cannot run, and places the settings protect")
  {
    const o = organization()
    const missing = [{ id: "OUR-2", applies_to: "work/", check: ["no-such-program-anywhere"] }]
    const strict = await install(settingsFor(o, { rules: missing, on_check_error: "refuse" }))
    const m = await strict.tryit("write", { filePath: "work/b.md", content: "12" })
    ok("with on_check_error refuse, a write whose check cannot run is refused", m !== null && m.includes("could not run"), String(m))
    const s = settingsFor(o, { rules: missing, protect: [join(ROOT, "app-config.json")] })
    const lax = await install(s)
    const a = await lax.tryit("write", { filePath: "work/b.md", content: "12" })
    ok("with on_check_error allow, it goes ahead and the log says the check could not run",
      a === null && logLines(s).some((e) => e.event === "check_error" && e.rule === "OUR-2"), String(a))
    const p = await lax.tryit("write", { filePath: join(ROOT, "App-Config.json"), content: "{}" })
    ok("a file named under protect cannot be written by a file tool", p !== null && p.includes("CORE-9"), String(p))
  }
} finally {
  rmSync(ROOT, { recursive: true, force: true })
}

console.log("\n%d checks, %d passed, %d failed", checks, checks - failed, failed)
process.exit(failed ? 1 : 0)
