# Records: how the organization keeps a history its members cannot rewrite

For people (founders, researchers), and for agents when a step points here.

## 1. The idea in one paragraph

Agents read rules and can still break them, and their own account of what they did is not always accurate. So the record does not rest on any member's word. Members **act** and write their records in the folder, one checked line at a time; **git** and the disk record what happened; and something outside the members' reach **verifies** it: the witness, a copy of the history in a folder next to the organization that refuses rewrites and deletions, and the founder's close-out, run by a person in a terminal. The founder **signs** each decision there, because people, not software, are held answerable for what an organization decides.

## 2. Writing records

- Every records file (`records/*.jsonl`) holds one JSON object per line and only ever grows. No member edits or deletes a line or a file, even on request (AGENTS.md, CORE-4).
- Records are added with `python scripts/fos_log.py <kind> --json-file <file>`, `--json -` (standard input) or `key=value` pairs. It fills in `seq`, `id`, the time in UTC, the session and the writer's identity, checks the record against its schema, and appends one line. It never re-creates a missing file: a missing records file was deleted, and that has to stay visible.
- `fos_log` is the only route into `records/`. One call may carry several records (a JSON list, or one object per line; `batch` mixes kinds); they are checked in order, each seeing the ones before it, and written only if all fit. Appends take a lock (`.fos-lock`), so members working side by side in the folder never get the same `seq` or mix their lines.
- No member touches a records file with an agent app's file tools, not even to add one line: tools asked to add a line often write the whole file again, and that is how history gets lost. A member who cannot run Python writes its records into a file in `work/`, one JSON object per line, and asks the founder to add them with `python scripts/fos_log.py batch --json-file <file>`.
- **Corrections.** A record written wrongly stays. A `record_correction` event points to it by `seq`, or by line number for a line that is not valid JSON, and says what it should have said. The check then reports it as a corrected defect, not a failure. A wrongly recorded decision is replaced by a new decision whose `corrects` field names the old one; the founder signs the new one. No correction, and no label on a decision, bears on whether the organization is founded (section 5b).
- **Identity.** Every record carries `identity`: the role instance that wrote it and, for an AI member, the model ID, producer, agent app and host (AGENTS.md, CORE-6), and where each came from. A member's own statement of who it is cannot be checked, so the seed offers one the member does not write: the founder's **launch** *[our term]*. `python scripts/fos_launch.py <instance>`, run by the founder before the app starts, records the instance and what the founder chose for it (model, producer, agent app, host) as an `instance_launched` event, and keeps the same launch, with a secret, in the witness folder. The line it prints (`FOS_LAUNCH=...`) is set where the app is started. `fos_log` then fills the identity from the launch and adds a fingerprint (an HMAC-SHA256 of the record keyed by the secret); the check recomputes it from the witness's copy. A record that names a launch it was not written under fails the check; records with no launch are reported as not verified. Without a launch, `fos_log` fills the identity from the instance's model slot in `org/config.json` unless the member states it. Records in a person's name (the founder, or another human role) are written only from that person's own terminal.

## 3. Who writes what

Every record says who wrote it (`captured_by`):

| Record | Written by | Independent of the AI members? |
|---|---|---|
| `captured_by: member` | AI members | No: their own account. With a launch, which instance wrote the line is shown by a fingerprint the member cannot make for another instance |
| `captured_by: founder` | The founder | Of the AI members, yes |
| `close_script` (signatures, close-out events, repairs), `init_script` (birth), `drill_script` (drills) | The seed's own scripts, run by the founder | They run in the founder's terminal; members do not write these values, and the check flags them if they appear elsewhere |
| Commit time, author, files changed, diff | git, at the founder's close-out | Yes, once pushed to the witness |
| The witness's copy of the history | the witness's own check, on every push | Yes, as far as the members cannot reach the witness folder |
| `captured_by: runner`, `observer` or `host` | A program or operator outside the organization | Yes. Not included in the seed; the schema allows one |
| The agent app's transcripts, kept by the founder in the witness folder | The agent app | Yes, if the members cannot reach them |

For research: compare members or configurations on a record kept identically in every case and beyond the members' reach (the witnessed history first). Treat the members' own records as evidence of how the organization worked, and measure how faithful they are against that record (`docs/RESEARCH_USES.md`).

## 4. The witness

`python scripts/fos_init.py <new-folder>` creates the witness at `<new-folder>-witness`, next to the organization's folder:

```
<organization>-witness/
  history.git/   a bare git repository; the close-out pushes here
  snapshots/     dated copies of records/, kept when git is not available
  drills/        the founder's sealed drill descriptions
  transcripts/   a place for the founder to keep agent-app transcripts
  README.txt
```

`history.git` refuses deleting or moving a branch or tag, any push that does not extend the history it holds, any branch but its one branch, merge commits, and any commit, anywhere in the pushed history, that deletes a records file or changes one other than by adding lines at its end. Its settings (`receive.denyNonFastForwards`, `receive.denyDeletes`) and its own copy of the check, `hooks/witness_check.py` (a copy of `scripts/fos_witness.py`), do the refusing; the check in it does not depend on anything in the organization's folder, so editing the organization's scripts cannot weaken it. `python scripts/fos_check.py` confirms each time that the witness still has those settings and that the folder's history still contains everything the witness holds. An organization made some other way can get a witness with `python scripts/fos_witness.py setup <folder-outside>` and `git remote add witness <folder-outside>/history.git`, or by accepting the close-out's offer. Every push attempt, accepted or refused, is logged in the witness folder (`pushlog.jsonl`: when, which refs moved, the reasons for a refusal, and the SHA-256 of the check that decided); the check counts refused pushes and the close-out shows the latest before the founder signs, since a refused push is evidence that someone tried and the structure held.

The witness is as safe as its folder is out of reach. A member working through an agent app's file tools usually cannot open it. A member with a shell on the founder's machine can, if nothing stops it; for real separation, run the agent app in a container that sees only the organization's folder (`docs/HARNESS_NOTES.md`), or keep the witness on another machine.

## 5. The close-out

The founder runs `python scripts/fos_close.py` at the end of each session, in an ordinary terminal. Members never need git. The close-out:
1. checks the records and their history; if a records file was deleted, or earlier lines were changed, since the last close-out, it offers to restore them from the last commit, keeping records added since and setting the changed lines aside in an `integrity_repair` event, so nothing is lost and the damage stays on record. Whether the folder is an organization at all is read from its history (the `[BIRTH]` commit) or, without git, from the witness's dated copies, never from `records/events.jsonl` alone; so a member who overwrites that file, birth record and all, cannot make the folder look like the seed, and the restore comes first. `org/BIRTH.json`, written once at birth, keeps a readable copy of the birth and is restored the same way;
2. marks void any signature line that no completed close-out wrote, and offers to note malformed lines nobody has corrected; if no `session_start` was recorded since the last close-out, it puts that gap on record (an `unrecorded_session` event naming what changed), and if nothing changed at all it asks the founder whether a session took place. Sessions are numbered by their starts and their close-outs, so a session nobody recorded still uses up its number, and roles that are due every few sessions (the drill among them) are counted the same way;
3. shows the state first (the check result, every failing item spelled out and numbered, and every file changed since the last close-out). If anything fails, the founder types the number of failing items before any signature is asked; any other answer, a plain `y` included, stops the close-out with nothing signed, so a script or plan answering its prompts cannot pass over them either. Then it shows each decision not yet signed, with any check failure that concerns what the decision adopts attached to it (such a decision is always asked on its own): the question as asked, the founder's recorded words, what it decides, what signing it makes part of the organization, who recorded it, and any warning (for example a generic reply). Decisions with a warning, an amendment, the founding, or a change to who decides, who is a member or what tools may do are asked one at a time; the rest form a routine group the founder may sign together or go through one by one. While the organization is not founded, the founding is asked first, before any other decision, and on its own: the decision recorded as the founding, the structure prepared for it, and "Found the organization now on this charter? (type FOUND)". Only the founder's FOUND founds it (section 5b); any other answer leaves it unfounded, and then the decisions that adopt structure are not asked: they stay waiting. The answers are `y` (sign), `s` (sign with a note), `n` (do not sign: it stays a proposal) and `b` (send it back to the members with a note, to be reworked and asked again). Each answer becomes a line in `records/signatures.jsonl`, with a hash of the decision line it signs, the note, and what the founder was shown (with a hash of the exact text), so every signature traces to what was reviewed;
4. lets the founder choose what the commit holds. Structural changes that no signed decision adopts are offered to be put back as they were at the last close-out (what they were stays in the record). Changes to the seed's own files and documentation are offered to be put back (a copy of each changed version goes to the witness folder's `set_aside/`) or left out; files outside the organization's folders can be left out. Records and the organization's own folders are always committed, except that, while the organization is not founded, the structural files changed since birth stay in the folder, uncommitted (section 5b). Then it redraws the rules in force and the view, commits as the founder, dated in UTC, with a message drawn from the records (`[CLOSE] S003: 2 signed, 1 not signed`, what each decision adopts, the "Waiting for close-out" list from `org/STATE.md`, anything left out, and trailers), and pushes to the witness. Because the decided list comes from the records, a member who rewrites `org/STATE.md` cannot drop an item from it; the check also warns when `org/STATE.md` no longer names a decision still waiting for a signature.

It refuses to run without a terminal. If the folder's history is out of line with the witness (behind it, split from it, or replaced), the close-out does not commit on top of it: it offers a sync first (`scripts/fos_sync.py`, below), then starts again from the witnessed history. It never advises a reset that would throw work away.

## 5a. One working copy, and the sync

An organization has one working copy: its folder. Several members may work in it, one after another or side by side (each with its own identity; `fos_log`'s lock keeps their records apart). A second copy of the folder, cloned from the witness and closed out on its own, is not supported: two copies number their records the same way (the same `seq`, the same IDs, the same session), so their records cannot be put together without renumbering, and renumbering would break every reference between records. One working copy keeps the record format the same everywhere and leaves the witness one line of history, written only by the founder's close-out.

Copies happen anyway, and pushes fail. `python scripts/fos_check.py` tells the cases apart: **behind** (the witness holds close-outs this folder never had: another copy was closed out), **split** (this folder has commits the witness refused or never got), and **replaced**. The founder's `python scripts/fos_sync.py` brings the folder back in line without losing anything: it first copies everything that differs from the witness into `<witness>/set_aside/<UTC time>/` with a manifest; returns the folder to the witness's last close-out; keeps this folder's added records where they cannot collide with the witness's (otherwise they stay set aside, never merged), and keeps other changed files unless the witness changed the same file; and records a `sync` event naming what was kept and what was set aside. Set-aside work is not part of the organization; a member can record or propose it again.

**Without git.** The close-out still checks and asks for signatures, then saves a dated copy of `records/` in the witness folder's `snapshots/`, and the check compares the records against the latest copy. Structural changes wait in the "Waiting for close-out" list in `org/STATE.md` until git is available.

## 5b. The founding: one invariant on files and history

An organization is founded at a close-out, when the founder types FOUND at its prompt; the signature records the word (`founding: "FOUND"`). The close-out then commits that signature on its own, with the records only (`[FOUND] S001: the founder founded the organization on D-0001`), and the structure prepared for the founding in the next commit. One invariant enforces the order, on the files and the history alone:

> No commit holds the structural files changed from the organization's birth unless an earlier commit founds it.

The structural files are `org/config.json` (all of it but the `organization` block, which holds the name and the founding, and the model slots of role instances, filled in at setup), `org/TOOLS.json`, `view/VIEWS.json`, and `org/OUR_RULES.md`, `NORMS.md`, `CHARTER.md`, `RECORDS_POLICY.md`, `FAILURE_PATTERNS.md` and `DESIGN_AHEAD.md`. The birth is the first commit. A commit founds the organization if it is a `[FOUND]` commit that adds such a signature, written by the close-out, by the founder, for a decision line that commit holds unchanged, adopted by the founder. The check fails a history that breaks the invariant, and the witness refuses a push that would hold one (`STRUCTURE BEFORE FOUNDING`); a sync then returns the folder to the witness, keeping the files. Whether the organization is founded is read from that history, never from `org/config.json` or the decision records: `founding: true` on a decision, a proposal's kind, `adopted_by` or `corrects` found nothing. The check still warns about a decision that adopts structure before the founding, as a reminder of the order the first session follows; the warning decides nothing.

## 6. Signatures

A decision counts only once the founder has signed it. A signature line counts only if the close-out wrote it, it names a decision that still reads exactly as signed (the hash matches), the signer is the founder, and the line is already committed (or, without git, in the latest dated copy). A line written since the last close-out, by anything else, does not count, and the next close-out marks it void. Test signatures, made by the seed's self-test, never count in a real organization.

A signature is only as meaningful as what the signer saw and could change [opinion]. So the close-out shows what each decision does before asking, keeps the number of separate questions small by grouping routine decisions, lets the founder answer with a note or send a decision back rather than only yes or no, and records what was shown. The founder's real work also sits before the signature (the charter and the rules they adopted) and after it (the next session's check).

What this cannot prevent: someone with full use of the founder's own account and terminal can imitate the founder. The design makes that a deliberate act, done outside the members' ordinary tools, rather than something a member can do by writing a line.

## 7. Commit messages

The close-out writes them, so the convention holds without anyone remembering it. Subject: `[TYPE] one-line summary`. Types used by the seed's scripts: `SEED` and `BIRTH` (`fos_init`), `FOUND` and `CLOSE` (`fos_close`). If a founder commits by hand, other types describe the change: `PROPOSE`, `DECIDE`, `STRUCTURE`, `MEMBER`, `RULE`, `TOOL`, `WORK`, `DECLINE`, `CORRECT`, `RECALL`, `SIGN`, `SESSION`, `DRILL`, `VIEW`, `REPAIR`, `RELOCATE`. The check warns about commits that change `records/` without one.

Rules that go with the history:
- No amend, rebase, reset or force-push of commits that contain records; the witness refuses them anyway.
- If a rewrite is ever unavoidable (for example, to remove material that should never have been committed), the founder decides it, and records what was removed, why, when and by whom, in a new commit and in a note kept in the witness folder.

## 8. Transcripts

If the agent app keeps transcripts, the founder keeps them outside the organization's folder (the witness folder's `transcripts/` is the place for them), where members cannot read or edit them. Members never load them: the organization remembers through its records, and the transcripts are an independent account to check those records against. Whether transcripts are ever shared is the founder's decision.
