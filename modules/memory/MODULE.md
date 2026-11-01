# Module: memory

**For.** Carrying what the organization knows from one session to the next, when its AI members carry nothing themselves, and when the next member may be a different model.

**Adds.** `records/corrections.jsonl`, `records/commitments.jsonl`, `records/recall.jsonl`; the cold-recall session (`onboarding/SECOND_SESSION.md`); use of `org/STATE.md`, `org/LETTER_TO_NEXT_SESSION.md` and `archive/`. See `docs/SOCIALIZATION.md` for what persists where.

**Works with.** Every module; memory is what makes the others last beyond a session.

**Costs.** A short step at each close-out. The boot files grow; rule MEM-9 keeps them in check.

## Rules

### MEM-1 One file holds the current state
rule: Keep the current state in org/STATE.md only. Rewrite it at each close-out. Other files may point to it; none may restate it.
why: when state lives in several places, they drift apart and the next session cannot tell which to believe.

### MEM-2 Write to the next session
rule: Before closing, write org/LETTER_TO_NEXT_SESSION.md: what was decided, what was done, what is open, what you would warn a newcomer about. Write it for a reader who remembers nothing.
why: each session's member starts with nothing; a letter from the previous holder is how the role passes on what it learned.
lit: Van Maanen & Schein 1977 (MIT working paper 960-77), on serial socialization, where an experienced member prepares the newcomer [lead]

### MEM-3 Capture by trigger
rule: When something happens, record it where it belongs, at once: a decision in decisions.jsonl, a correction in corrections.jsonl, a promise in commitments.jsonl, the founder's exact words in the record they belong to.
why: what is not written at the moment is reconstructed later from memory, and reconstruction drifts.

### MEM-4 Recall before you re-derive
rule: Before treating an idea, source, rule or tool as new, search the records and the folder for it.
why: an organization that forgets what it settled spends its time settling it again, and may settle it differently.

### MEM-5 Promises need a record
rule: When closing a session, mention future work only if records/commitments.jsonl holds a line for it naming who owns it and what will start it. Do not end with an unowned "next I will...".
why: promises without owners and triggers are forgotten; a ledger of them can be checked.

### MEM-6 Corrections end in a structural fix
rule: When something was wrong, record what was wrong, what is right, who caught it, whether it had already left the folder, and the change to structure that should prevent a repeat ("none yet" is allowed). Propose that change.
why: fixing the instance repairs one error; fixing the structure changes what the organization does next time.
lit: Feldman & Pentland 2003, on routines changing through their performance [lead]

### MEM-7 Never delete; archive
rule: Do not delete files. Move superseded ones to archive/ with a first line naming what replaced them and why. (Records files are never moved or deleted at all: AGENTS.md, CORE-4.)
why: a deleted file takes its history with it; an archived one can still explain how the organization got here.

### MEM-8 When a file is replaced, move the pointers too
rule: When a decision replaces a file or a plan, in the same session update the file, every pointer to it (AGENTS.md read order, org/STATE.md), and mark the old one as superseded.
why: a new plan that the boot files do not point to will be lost to the next session, which will follow the old one.

### MEM-9 Keep the boot short; give each norm a review date
rule: Load in every session only what every session needs. Move the rest behind a pointer. When proposing a norm, give it a date to review it.
why: boot files grow by accretion until members skim them; review dates let the organization forget what no longer serves it.

### MEM-10 Check the disk, not the documents
rule: Before planning a next step, check that what the records and state file say exists actually exists in the folder. Report any gap.
why: documents record what was intended; only the folder shows what is there.

### MEM-11 Park before a pause
rule: Before a long pause or a change of direction, write a re-entry note in org/STATE.md: what is closed, what is open, what is in flight, and what could not be secured.
why: work interrupted without a note is often redone from scratch, or lost.

### MEM-12 Role cards carry their lessons
rule: When a role has a card (its brief, named in the role's card field), read it before running the role, and add what was learned to the card's notes section. Changes to the role's duties, trigger or rights go through a proposal and decision.
why: a role re-invoked from the same card accumulates what earlier holders learned, instead of starting again each time.

### MEM-13 Keep the founder's "later" on a list
rule: When the founder puts something off ("come back to this", "not now"), add a line to records/pins.jsonl with the founder's words exactly and what should bring it back. At each roll-call, read the open pins and raise any whose moment has come.
why: what a person defers in passing is the easiest thing for an organization to lose, and a deferral nobody returns to becomes a decision nobody made.

## Grounding

This module is here to carry what the organization knows from one session to the next, because its AI members carry nothing themselves and the next member may be a different model. No theory is claimed for it, because none has been read for the module as a whole: the one work read for it, Van Maanen & Schein 1977 (pp. 35–37), serves only the letter from one holder to the next (MEM-2) and `docs/SOCIALIZATION.md`. It is therefore a design guess, which a scholar may theorize and test, for example by running organizations with it on and with it off and comparing their records. Its `lit:` lines, where it has any, are leads unless they say read (`docs/LITERATURE.md`).
