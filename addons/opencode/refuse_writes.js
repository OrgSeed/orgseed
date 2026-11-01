// Enforcement add-on for OpenCode: it refuses a file-tool write that breaks a named rule in force.
// A reference add-on for one agent app (docs/ENFORCEMENT.md; README.md beside this file). Optional: the seed's
// scripts never load it or depend on it. Its settings are in refuse_writes.json, beside this file.
// Node's own modules only; no network. Its tests: test_refuse_writes.mjs, beside this file.
import { readFileSync, appendFileSync, existsSync, realpathSync } from "node:fs"
import { join, dirname, basename, resolve, relative, isAbsolute } from "node:path"
import { fileURLToPath } from "node:url"
import { execFileSync } from "node:child_process"

const FILE_TOOLS = new Set(["write", "edit", "multiedit", "patch", "apply_patch"])
const WINDOWS = process.platform === "win32"
const UP = /^\.\.([\\/]|$)/ // a relative path that leaves the folder it is relative to

// The real path of p: links, junctions and short names resolved through its nearest parent that exists.
function real(p) {
  let head = resolve(p)
  const tail = []
  for (;;) {
    try {
      return join(realpathSync.native(head), ...tail)
    } catch (e) {
      const up = dirname(head)
      if (up === head) return resolve(p)
      tail.unshift(basename(head))
      head = up
    }
  }
}

// Paths are compared without regard to case, on every system: on Windows, and on macOS's usual disks,
// "Records/" and "records/" are the same folder. On Windows a name's trailing dots and spaces are dropped, and a
// ":stream" suffix names part of the same file, so both are read the way the file system reads them.
function key(rel) {
  let parts = String(rel).split(/[\\/]+/)
  if (WINDOWS) parts = parts.map((s) => s.split(":")[0].replace(/[. ]+$/, ""))
  return parts.filter((s) => s && s !== ".").join("/").toLowerCase()
}

// Is the real path p the place itself, or inside it? Compared without case.
function within(place, p) {
  const rel = relative(place.toLowerCase(), p.toLowerCase())
  return rel === "" || (!UP.test(rel) && !isAbsolute(rel))
}

const HERE = real(dirname(fileURLToPath(import.meta.url)))

// Its settings. If anything in them is wrong, the add-on refuses every file-tool write and says why (it fails closed).
let SETTINGS = {}
let BROKEN = null
try {
  SETTINGS = JSON.parse(readFileSync(join(HERE, "refuse_writes.json"), "utf8")) || {}
} catch (e) {
  BROKEN = "its settings (refuse_writes.json, beside it) cannot be read"
}
const TOOL_ID = SETTINGS.tool_id || "refuse-writes"
const ORG = !BROKEN && SETTINGS.organization ? real(String(SETTINGS.organization)) : null
const LOG = SETTINGS.log ? real(resolve(HERE, String(SETTINGS.log))) : null
const RULES = Array.isArray(SETTINGS.rules) ? SETTINGS.rules : []
if (!BROKEN && !ORG) BROKEN = "its settings name no organization folder"
if (!BROKEN && !existsSync(join(ORG, "AGENTS.md"))) BROKEN = "the organization folder its settings name holds no AGENTS.md"
if (!BROKEN && LOG && within(ORG, LOG)) BROKEN = "its log is inside the organization's folder, where members could change it"
if (!BROKEN && SETTINGS.rules !== undefined && !Array.isArray(SETTINGS.rules)) BROKEN = "its rules are not a list"
if (!BROKEN && RULES.some((r) => !(r && r.id && Array.isArray(r.check) && r.check.length))) {
  BROKEN = "a rule in its settings has no id or no check"
}

// Places no file tool may write, inside the folder or outside it: the folder this add-on is installed in (its code,
// its settings, and any other plug-in there), its log, and whatever its settings add under "protect" (such as the
// agent app's own configuration file).
const PROTECTED = [HERE, ...(LOG ? [LOG] : []),
  ...(Array.isArray(SETTINGS.protect) ? SETTINGS.protect : []).map((p) => real(resolve(HERE, String(p))))]

// CORE-4: records are written only by fos_log, never by an app's file tool.
const RECORDS_RULE = { id: "CORE-4", reason: "a record that can be rewritten cannot be trusted later" }
// CORE-9: the add-on is a check, and a member able to change it could switch it off.
const OWN_FILES_RULE = { id: "CORE-9", reason: "a member who can rewrite the checks can make the record say anything" }

function note(entry) {
  if (!LOG) return
  try {
    appendFileSync(LOG, JSON.stringify({ at: new Date().toISOString(), tool_id: TOOL_ID, ...entry }) + "\n")
  } catch (e) {
    // a log that cannot be written never blocks the work
  }
}

if (BROKEN) {
  console.error("[" + TOOL_ID + "] not running as set up: " + BROKEN + ". Every file-tool write will be refused.")
  note({ event: "not_running", reason: BROKEN })
}

// A path as a file tool gives it: its real place (abs), and its place in the organization's folder ("records/x.jsonl",
// in lower case, as key() reads it), or null for anything outside the folder.
function target(p) {
  const abs = real(resolve(ORG, String(p)))
  const rel = relative(ORG.toLowerCase(), abs.toLowerCase())
  const inside = rel !== "" && !UP.test(rel) && !isAbsolute(rel)
  return { abs, path: inside ? key(rel) : null }
}

function onDisk(abs) {
  try {
    return readFileSync(abs, "utf8")
  } catch (e) {
    return ""
  }
}

function edited(text, oldText, newText, every) {
  if (oldText && text.includes(oldText)) return every ? text.split(oldText).join(newText) : text.replace(oldText, newText)
  return text + "\n" + newText // the edit cannot apply as given: check the new text at least
}

// A patch, file by file: the files it adds or changes, with the lines it adds to each; the files it deletes; and,
// for a file it moves, both the old name (which goes) and the new one (which gets what the patch adds).
function patchItems(patch) {
  const out = []
  let cur = null
  for (const line of patch.split(/\r?\n/)) {
    const m = line.match(/^\*\*\* (Add File|Update File|Delete File|Move to):\s*(.+?)\s*$/i)
    if (m) {
      const what = m[1].toLowerCase()
      if (what === "move to" && cur) {
        cur.op = "moved_from"
        cur = { ...target(m[2]), op: "write", added: cur.added }
      } else {
        cur = { ...target(m[2]), op: what === "delete file" ? "delete" : "write", added: [] }
      }
      out.push(cur)
    } else if (cur && line.startsWith("+") && !line.startsWith("+++")) {
      cur.added.push(line.slice(1))
    }
  }
  return out.map((i) => ({ abs: i.abs, path: i.path, op: i.op, content: i.op === "write" ? i.added.join("\n") : "" }))
}

// What a file tool would do on disk: a list of {abs, path, op, content}.
function wouldWrite(tool, args) {
  const name = String(tool || "").toLowerCase()
  if (name === "patch" || name === "apply_patch") return patchItems(String(args.patchText || args.patch || ""))
  const p = args.filePath || args.file_path || args.path
  if (!p) return []
  const t = target(p)
  if (name === "write") return [{ ...t, op: "write", content: String(args.content ?? "") }]
  if (name === "edit") {
    return [{ ...t, op: "write", content: edited(onDisk(t.abs), args.oldString ?? "", args.newString ?? "", args.replaceAll) }]
  }
  if (name === "multiedit" && Array.isArray(args.edits)) {
    let text = onDisk(t.abs)
    for (const e of args.edits) text = edited(text, e.oldString ?? "", e.newString ?? "", e.replaceAll)
    return [{ ...t, op: "write", content: text }]
  }
  return []
}

// The rule's own check: a program that reads {"path": ..., "content": ...} on its standard input and prints
// {"violations": [...]}. An empty list lets the write through.
function breaches(rule, item) {
  try {
    const out = execFileSync(rule.check[0], rule.check.slice(1), {
      input: JSON.stringify({ path: item.path, content: item.content }), encoding: "utf8", timeout: 60000, windowsHide: true,
    })
    return (JSON.parse(out).violations || []).map(String)
  } catch (e) {
    note({ event: "check_error", rule: rule.id, path: item.path, error: String(e).slice(0, 300) })
    return SETTINGS.on_check_error === "refuse" ? ["the check for " + rule.id + " could not run"] : []
  }
}

// A rule's applies_to, read like the paths it is compared with: "work/" covers everything in work/.
function covers(rule, path) {
  if (!rule.applies_to) return true
  const scope = key(rule.applies_to)
  return path === scope || path.startsWith(scope + "/") || (!String(rule.applies_to).endsWith("/") && path.startsWith(scope))
}

// The same instruction to record the refusal ends every refusal, bare or reasoned.
const RECORD_IT = "Record this as a decline with enforced_by " + TOOL_ID + "."

function refusal(rule, found) {
  if (SETTINGS.refusal === "bare") return "Refused. Nothing was written. " + RECORD_IT
  return "Refused by the organization's enforcement add-on " + TOOL_ID + ": this write breaks " + rule.id +
    (rule.reason ? " (its reason: " + rule.reason + ")" : "") + (found.length ? ". Found: " + found.join("; ") : "") +
    ". Nothing was written. " + RECORD_IT + " If the rule is wrong for this case, propose a change to it (AGENTS.md, CORE-2)."
}

function refuse(tool, item, rule, found) {
  note({ event: "refused", tool, op: item.op, path: item.path, rule: rule.id, found })
  throw new Error(refusal(rule, found))
}

export const RefuseWrites = async () => ({
  "tool.execute.before": async (input, output) => {
    const tool = input && input.tool
    if (!FILE_TOOLS.has(String(tool || "").toLowerCase())) return
    if (BROKEN) {
      note({ event: "refused", tool, reason: BROKEN })
      throw new Error("Refused. The enforcement add-on " + TOOL_ID + " is not running as set up: " + BROKEN +
        ". Nothing was written. Tell the founder.")
    }
    const items = wouldWrite(tool, (output && output.args) || {})
    for (const item of items) {
      if (PROTECTED.some((place) => within(place, item.abs))) {
        refuse(tool, item, OWN_FILES_RULE, ["a file tool writing to the add-on's own files"])
      }
      if (item.path === null) continue // outside the organization's folder: not this add-on's to judge
      if (SETTINGS.records !== false && (item.path === "records" || item.path.startsWith("records/"))) {
        refuse(tool, item, RECORDS_RULE, ["a file tool writing in records/"])
      }
      if (item.op !== "write") continue // a deletion, or the old name of a moved file: no content to check
      for (const rule of RULES) {
        if (!covers(rule, item.path)) continue
        const found = breaches(rule, item)
        if (found.length) refuse(tool, item, rule, found)
      }
    }
    if (items.length) note({ event: "allowed", tool, paths: items.map((i) => i.path) })
  },
})
