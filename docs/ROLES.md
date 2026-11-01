# Roles, instances and model slots

DRAFT. For people and agents.

- A **role** is a position in the organization: what it is for, what it decides, which checks it holds. Roles persist when their holders change.
- A **role instance** *[our term]* is one holder of a role. A role may have any number of instances. The founder role normally has one; an AI role may have several, for example two checkers that read the same draft independently.
- A **model slot** *[our term]* is where an AI instance's model is recorded: the model ID, its producer, where the ID came from, the agent app, and the host that serves the model (AGENTS.md, CORE-6 defines the three). Instances of one role may sit on models from different producers.

```
"roles": [
  {"id": "founder", "kind": "human", "instances": [{"id": "founder", ...}], ...},
  {"id": "member", "kind": "ai", "instances": [{"id": "member-1", "slot": {...}}], ...},
  {"id": "checker", "kind": "ai", "why_admitted": "an independent second reading",
   "instances": [
     {"id": "checker-a", "slot": {"producer": "<producer A>", "model_id": "<id>", ...}, "adopted_by": "D-0007"},
     {"id": "checker-b", "slot": {"producer": "<producer B>", "model_id": "<id>", ...}, "adopted_by": "D-0007"}
   ], "adopted_by": "D-0007"}
]
```

**Which instance am I?** The founder says so before the app starts: `python scripts/fos_launch.py <instance>`, run in the founder's own terminal, records the launch (the instance, and the model, producer, agent app and host the founder chose) and prints one line to set where the app is started. Every record that app writes through `fos_log` then carries the launch and a fingerprint that the check can recompute from the copy kept in the witness folder, so a record is attributed by something the member did not write. Without a launch, an agent learns its instance at session start (`onboarding/SESSION_START.md`): if there is one AI instance, it is that one; otherwise the founder says; and its records are reported as not verified. Each event, decision and commit names the instance and the model, so the records show who did what on which model.

**Changing the model in a slot** is a structural change: a proposal (`kind: "model_slot"`), a decision, a `model_swap` event. The role, its rules and its records stay; the holder changes. With the `membership` module on, the new holder runs a probation task first and the outgoing one writes a handoff.

**Several instances at once.** Instances may work in separate sessions or, in agent apps that allow it, side by side, always in the organization's one folder (`docs/RECORDS.md`, section 5a): never in a copy of it. Each appends only its own records, with its own identity, and never overwrites another instance's work (`onboarding/SESSION_START.md`).

**The drill role.** The seed ships one role held by the founder: `drill`, triggered every three sessions. Its holder plants a known fault with `scripts/fos_drill.py`, sealed until revealed, so the organization can tell a check that finds nothing from a check that has stopped working. A member never holds it.

**Human roles beyond the founder.** A role of kind `human` can have instances for other people (a co-founder, a collaborator). Decisions they make count as human decisions only within the rights the founder has given their role (the scripts do not apply this yet: only the founder role can sign, so a co-founder's decision is kept as a human decision and waits for the founder's signature).

## Every role runs on a trigger

Roles defined only in a document can fade: nobody remembers to call them, and after a while the organization chart describes an organization that no longer exists [opinion; compare the distinction between a routine as written and as performed, Feldman & Pentland 2003 [lead], and formal structure decoupled from activity, Meyer & Rowan 1977 [lead]]. Roles that keep working are tied to something that calls them without anyone having to remember. So every role declares (AGENTS.md, CORE-12):

| Field | Meaning |
|---|---|
| `trigger.on` | What calls it: `session_start`, `close_out`, `event`, `every_n_sessions`, `founder_call`, or `schedule` |
| `trigger.when` | In words: which event, how many sessions, or which schedule |
| `output` | Where its work goes (a records file, a folder) |
| `expected_every_sessions` | How often it should run; `null` for roles that run only on call |
| `card` | Optional: a file holding the role's brief, so any capable agent can fill the role the same way each time |
| `instances` | Its holders, each with a model slot |

The triggers are conventions written into `AGENTS.md` and the onboarding checklists, so they work in any agent app. Where an app or the founder's machine offers automatic triggers (a scheduler, an app's own event hooks), the founder may wire a role to one as an approved tool; the convention still holds without it.

**Heartbeat** *[our term]*. A role's last run is read from `records/events.jsonl`: the last event whose actor is one of its instances, or a `role_ran` event naming it. It is derived, never typed in by hand.

**Role roll-call** *[our term]*. At every session start (`onboarding/SESSION_START.md` step 4, or `python scripts/fos_roles.py`), the agent lists each role that has not run within its expected interval, has never run, or has no trigger, and asks the founder whether to **revive** it (re-wire its trigger), **merge** it into another role, **retire** it, or **keep** it.

**Retiring and merging.** Each is a proposal and a decision, like creating a role. The role moves from `roles` to `retired_roles`, never deleted:

```
"retired_roles": [
  {"id": "scout", "title": "Scout", "end": "absorbed", "absorbed_into": "member",
   "retired_by": "D-0021", "reason": "not run in eight sessions; its search duty fits the member's work"}
]
```

## Role card template (optional, at the path in the role's `card` field)

```
# Role card: <title>
Purpose: what this role is for
Trigger: what calls it, in words
Does, each time: the steps
Output: where its work goes, in what form
Decides alone: ...   Must hand back: ...
Checks it holds: ...
Standing direction from the founder: (quoted, with decision IDs)
Notes from earlier runs: (lessons; added by holders after each run)
When several instances work at once:
  Write only: (this instance's own files, and records through fos_log)
  Hand back: (a short, fixed summary: what was done, counts, what is uncertain; the rest stays in the files)
  Verdict word, for a review: pass, findings or fail
  Budget: (time or model calls); anything added beyond it names what it replaces
```
