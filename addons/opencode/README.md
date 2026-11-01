# An enforcement add-on for OpenCode (a reference, not a requirement)

DRAFT. For founders who want one of their rules enforced, and for researchers who need to see exactly what "enforced" meant. Read `docs/ENFORCEMENT.md` first.

**Optional, and one app's.** The seed works with any agent app, and nothing in it needs this add-on. This one is for one app, OpenCode, and is tied to how that app lets a plug-in see a tool call before it runs. Another app needs its own.

## What it does

Before each of the app's file tools runs (`write`, `edit`, `multiedit`, `patch`, `apply_patch`), it works out which files the tool would write, delete or move, and what each written file would hold afterwards. Then it:

- refuses any write to its own files: the folder it is installed in (its code, its settings and any other plug-in there), its log, and any file or folder its settings list under `"protect"`, such as the app's own configuration file (CORE-9: a member who could change a check could switch it off);
- refuses any write, deletion or move that touches `records/` (CORE-4: only `fos_log` writes records), unless its settings say `"records": false`;
- for each rule in its settings, runs that rule's check on what a written file would hold, and refuses the write if the check reports a breach.

Paths are read as the file system reads them: without regard to letter case, on every system (on Windows and on macOS's usual disks `Records/` is `records/`); through links and junctions; and, on Windows, without a name's trailing dots or spaces and without a `:stream` suffix. On Linux this also refuses a folder that differs from `records/` only in case, which is the safer mistake.

**If its settings are wrong it refuses everything.** When the settings cannot be read, name no organization folder, name a folder with no `AGENTS.md` in it, put the log inside the organization's folder, or hold a rule with no ID or no check, the add-on says so in the app's console and in its log (if it has one), and refuses every file-tool write, inside the folder or outside it, with a message that says it is not running as set up. A mistake in the settings then shows at the first write instead of letting every write through unseen.

A refusal reaches the member as the tool's answer, and every refusal ends with the same instruction: record the decline, with `enforced_by` set to the add-on's tool ID. With `"refusal": "reasoned"` it also names the rule, its reason and what was found, and says that a change to the rule may be proposed (CORE-2). With `"refusal": "bare"` it says only "Refused. Nothing was written." before that instruction. Nothing is written either way, so the two settings differ only in the rule, the reason and the route to a change.

**Counting refusals.** A decline in `records/declines.jsonl` exists only if the member recorded it, and a member may not. The add-on's own log (`"log"`, a file outside the organization's folder) has a line for every write it refused or let through, so it is the full count; the members' declines are their account of it. Where refusals have to be counted, set `log`.

## Its reach, and its blind spots

- **Covers:** the app's file tools named above: for the rules and `records/`, the files inside the organization's folder; for its own files, wherever they are.
- **Does not cover:** the shell. A command the member runs in a shell (if the app gives it one) can write any file, its own files and `records/` included, and this add-on does not see it. Nor does it see tools by other names, or judge files outside the folder other than its own. Record this in the registry row: `"covers": "file tools; shell: no"`, and record whether the app's shell was on.
- A rule's check that cannot run lets the write through and is logged, unless `"on_check_error": "refuse"` is set.

## Files

- `refuse_writes.js`: the add-on. SHA-256 at this release: `e05226b2300bcd91b59c14264518a68553f3048c1484acfbc4e96de9c98388fb`.
- `test_refuse_writes.mjs`: its tests, run with Node.js alone (`node test_refuse_writes.mjs`, from this folder); no agent app or model is involved, and nothing outside a temporary folder is touched.
- `refuse_writes.json`: its settings, which you write, beside the installed copy. For example:

```
{"organization": "<full path of the organization's folder>",
 "tool_id": "refuse-writes",
 "refusal": "reasoned",
 "records": true,
 "log": "<a file outside the organization's folder, or null>",
 "on_check_error": "allow",
 "protect": ["<the app's own configuration file, for example>"],
 "rules": [{"id": "OUR-1", "reason": "the rule's why, in its own words", "applies_to": "work/",
            "check": ["<program>", "<its arguments>"]}]}
```

A rule's check is any program you approve as a tool: it reads `{"path": ..., "content": ...}` (JSON) on its standard input and prints `{"violations": [...]}`; an empty list lets the write through. For a patch, the check sees the lines the patch adds to that file. A relative path in `log` or `protect` is read from the folder the add-on is installed in.

## Installing and registering it

1. Copy `refuse_writes.js` unchanged, with your `refuse_writes.json` beside it, into the plug-in folder of the configuration home you launch the app with for this organization (`docs/HARNESS_NOTES.md`: a configuration folder of its own; the app's documentation names its plug-in folder). Never put the installed copy inside the organization's folder, where members could edit it.
2. Propose it as a tool and register it in `org/TOOLS.json`, at tier 2 without a log and tier 4 with one (`docs/ENFORCEMENT.md`), with each rule's check registered as a tool of its own, and with the fields in `docs/ENFORCEMENT.md`: `kind` `"enforcement add-on"`, `path` `addons/opencode/refuse_writes.js`, `agent_app` `"OpenCode"`, the app version you tested it with, `enforces` (CORE-4 if `records` is on, and each rule ID), `covers`, `refusal`, and `code_sha256` (the hash above). The check recomputes the hash of the copy in `addons/`, not of the installed copy, which is the one that runs; so install a byte-identical copy, and name the plug-in folder in the launch, `python scripts/fos_launch.py <instance> ... --app-instructions <the plug-in folder> <the app's configuration file>`, which records the installed copy's hash, and its settings' hash, with every launch (`docs/HARNESS_NOTES.md`). Keep the log out of the plug-in folder, or that folder's hash changes at every launch.
3. Test it with a member before the founder relies on it: one write that breaks the rule, one that does not.

## Status

Written for this release. Its tests (`test_refuse_writes.mjs`) call its hook directly, as the app would, with a Node.js runtime (v24), and they pass: writes, edits and patches into `records/`, in any letter case, through `..`, through a link and (on Windows) through a trailing dot or a stream name; patches that delete or move a record; writes that break a rule and writes that keep it; writes to its own code, settings and log, and to a protected file; writes outside the folder (let through) and a shell command (not seen); bare and reasoned messages; a check that cannot run; and five kinds of wrong settings, each refusing every write. It has been run inside OpenCode 1.18.34. Before relying on it, try it in the app with the version you register. It uses the app's `tool.execute.before` hook and refuses by raising an error; apps change, so check the app's current plug-in documentation.
