# Session start (every session after the first)

For the AI agent, once `AGENTS.md` has been read, in every session after the first, whether or not the organization is founded yet. Do these steps before taking up any request.

## 1. Read what the last session left, before anything else

Whatever the stage, read these first, in this order:
1. `org/LETTER_TO_NEXT_SESSION.md`: what the member who closed the last session wanted the next one to know.
2. `org/STATE.md`: where things stand, and what waits for the founder's close-out.
3. The decisions the founder signed: each line of `records/signatures.jsonl` with `"answer": "signed"` names one; read its question and the founder's words in `records/decisions.jsonl`.

If you can run Python, `python scripts/fos_check.py --resume` prints all three, then the decisions not yet signed and the proposals still open. This is the organization's memory of every earlier session. Build on it: do not ask again what it already answers, such as the founder's consent to the records, the goal and why it matters, or a decision already taken.

**If the organization is not founded yet** (`python scripts/fos_check.py` says `stage: born`; the letter says so too), no close-out has founded it: an earlier session stopped before the founding decision, or the founder did not type FOUND at its close-out. Do not start the first session again. Do steps 2 to 6 below, then take up `onboarding/START.md` at the first step the records do not show as done: usually step 7 (the charter, read back) or step 8 (the founding decision). Ask the founding decision before any other adoption (AGENTS.md, CORE-2), even when the founder raises a module or a role first: write it as a proposal, and name it in the founding question. A founding decision the founder did not found at a close-out (not signed, or sent back) is asked again as a new decision. Structure prepared for the founding stays in the folder, uncommitted, until the founder types FOUND at a close-out.

## 2. Say which instance you are

If the founder launched this app as an instance (`FOS_LAUNCH` is set, or the folder holds `.fos_launch.json`), that launch names your instance. Otherwise look at the roles in `org/config.json`: with one AI instance, that instance is you; with several, ask the founder which one you hold today. State in one line: the instance, your model ID, its producer, your agent app and its host, as your app reports them (CORE-6); for anything your app does not show, ask the founder and use the answer, marked as the founder's. Then compare with the latest `session_start` this instance wrote. If it names a different model, open with that, naming both models in full: the one the role last ran on and the one it runs on today. A change of model in a slot is a proposal and a decision.

Record the start: `python scripts/fos_log.py event type=session_start summary="..."` (the next session label is filled in). Do this before any work, even if the founder asks for something at once: the check flags any session that changes files without a recorded start, and the close-out puts the gap on record.

## 3. Check the disk

If you can run Python, run `python scripts/fos_check.py` and tell the founder what it says in plain words, failures first. Do not explain failures away and do not repair records yourself: the founder's close-out offers the repairs. In particular, say:
- if decisions from an earlier session were never signed (the last close-out did not run): they are proposals again; ask whether to put them to the founder again, by ID;
- if the check reports anything as UNWITNESSED, deleted, rewritten or not part of the organization.
If you cannot run Python, say so; the founder can run the check, or see the same state in `view/org_view.html`.

## 4. Role roll-call

Go through the roles in `org/config.json`, or run `python scripts/fos_roles.py`. Tell the founder about every role that is overdue, has never run, or has no trigger, and ask for each: **revive** it (give it a working trigger), **merge** it into another role, **retire** it, or **keep** it as it is. Each change is a proposal and a decision (CORE-12). Then run the roles triggered by `session_start`, and any `every_n_sessions` role whose turn has come.

Read the open pins too (`records/pins.jsonl`, or `python scripts/fos_roles.py`): things the founder chose to come back to. Raise any whose moment has come.

The drill role belongs to the founder. When it is due, remind the founder that they may plant a drill (`python scripts/fos_drill.py plant`, in their terminal). Never plant one yourself, and never guess what a planted drill is.

## 5. Read the rest of the organization, not a transcript

Read in this order: `org/GOAL.md`; the rules in force (`org/RULES_IN_FORCE.md`); `org/OUR_RULES.md`; then the record of what actually happened: the latest 30 lines of `records/decisions.jsonl`, `records/proposals.jsonl`, `records/declines.jsonl` and `records/events.jsonl`. The rules say how the organization means to work; the records show how it has worked. Earlier sessions are known only through these files and those in step 1; do not look for transcripts.

## 6. Tell the founder what the organization knows

Before new work, summarize:
1. The goal, quoted from the founder.
2. Decisions since the founder was last here, quoted and dated, and whether each was signed.
3. What only the founder decides, and who signs.
4. Promises outstanding, the members' and the founder's.
5. Where the work stands: finished, turned back or redirected, and next, setbacks included.
6. Proposals waiting for a decision, by ID.
7. Changes to the organization since the founder's last visit: modules, roles, models in slots, tools.

Then ask the founder to correct anything wrong or add anything missing. With the memory module on, the founder may score this summary (`onboarding/SECOND_SESSION.md`).

## 7. Work

If the organization is not founded yet, the work starts with preparing the founding (step 1); the founder founds it at the close-out. With the engagement module on, follow its session shape (`modules/engagement/MODULE.md`). Otherwise take up what the founder asks, within the rules in force. Suggestions are welcome too: when something ought to work another way, write it up as a proposal (CORE-2), with what a structural change asks for, and open it with the founder as a question to discuss before you ask for a decision. End with `onboarding/CLOSE_OUT.md`.

## Triggers: the moments that call roles

In any agent app, these moments call roles. At each one, run the roles whose `trigger.on` matches, or say why not, and record a `role_ran` event naming the role in `refs`:
- `session_start`: the start of every session (this file, step 4).
- `close_out`: the end of every session (`onboarding/CLOSE_OUT.md`).
- `event`: when the event named in `trigger.when` happens (for example, before the founder signs a deliverable, after a draft is finished, before anything is sent). Check for these whenever you finish a piece of work.
- `every_n_sessions`: at session start, when that many sessions have passed since the role last ran.
- `founder_call`: when the founder asks for the role.
- `schedule`: only if the founder has set up a scheduler outside this folder; otherwise treat it as `every_n_sessions`.

## Several instances in one folder

Instances may work in separate sessions or side by side, in this one folder; never in a copy of it (a copy's records collide with this folder's). Each writes only its own records, with its own identity, and never overwrites another instance's work. A checker never checks work its own instance made. If the check says this folder is BEHIND THE WITNESS, another copy was closed out: tell the founder, who runs `python scripts/fos_sync.py`.
