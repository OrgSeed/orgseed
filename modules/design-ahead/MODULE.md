# Module: design-ahead

**For.** Letting the founder set structure before the first incident rather than after it. Organizations often learn their rules from failure. A founder who knows how organizations fail can choose some of that structure in advance.

**Adds.** `org/DESIGN_AHEAD.md`: the founder's dated choices, made against the general failure classes below. Corrections (module `memory`) are tagged with a failure class, so the organization can later see which classes it designed against and which it met anyway.

**Works with.** `memory` (corrections carry a `failure_class`), every other module (a design-ahead choice usually switches a module on or adds a rule or check).

**Costs.** One sitting, early on, and a review when corrections cluster in a class.

## General failure classes

These are general classes of failure in organizations whose members include AI agents, drawn from the authors' own experience of such organizations, not from a literature. The founder may add, merge or drop classes.

| ID | Class | Typical form |
|---|---|---|
| FC-1 | Invented specifics | A citation, name, date or number stated with confidence and not checked |
| FC-2 | Summary drift | A real source carrying a summary that does not match it |
| FC-3 | Scope creep | A bounded request expanded without asking |
| FC-4 | Act-then-report | An action beyond the task taken and announced afterward |
| FC-5 | Lost context | A framing or decision the founder made earlier, dropped or replaced |
| FC-6 | Assumed decision | Something treated as decided that the founder never decided |
| FC-7 | Status inflation | "Done" or "verified" used for what was planned or estimated |
| FC-8 | Silent omission | Work accurate in each sentence that leaves out what matters |
| FC-9 | Boundary leak | Material leaving the folder, or entering a channel, against the records policy |
| FC-10 | Silent monitor failure | A check, tool or watcher that stopped working and reported nothing |
| FC-11 | Unannounced member change | A model changed in a slot without a record |
| FC-12 | Stale pointers | Boot files pointing to a superseded plan |
| FC-13 | Over-binding | Rules applied where their purpose does not hold, or crowding out ideas |
| FC-14 | Unrun code | Code written by a member run, or relied on, without approval or a known-answer test |
| FC-15 | Data unseen | An analysis built before anyone looked at the actual data |

## Rules

### DA-1 Walk the classes with the founder early
rule: Within the first few sessions, go through the failure classes with the founder. For each, record in org/DESIGN_AHEAD.md one of: a structure chosen now (as a proposal), "accept the risk", or "decide later", with the date.
why: structure chosen from knowledge before an incident costs less than structure learned from the incident.

### DA-2 Tag every correction with a class
rule: When recording a correction, give its failure class, or "other" with a one-line description.
why: tagged corrections show which classes the organization's design held against and which it did not.

### DA-3 Revisit when a class repeats
rule: When two corrections share a class that DESIGN_AHEAD.md marked "accept" or "decide later", raise it with the founder as a numbered decision.
why: a repeated failure is evidence that the earlier choice should be reconsidered.

### DA-4 Let the founder's own knowledge lead
rule: Ask the founder which of the classes they have seen in human organizations they know, and how those organizations handled them. Propose structure drawn from their answer before proposing your own.
why: the founder's knowledge of organizations is the reason to design ahead at all.

### DA-5 After a freeze, log every change and its kind
rule: Once a design is frozen (a study's plan, or a design the founder declares fixed), record every later change in records/deviations.jsonl: what changed, whether it was forced from outside (for example, a model retired or changed by its producer), a correction, or a choice, whether any results it could touch had been seen, and what it may do to them. Do not make a chosen change once its effect on a result can be seen.
why: a frozen design is only worth its freeze if every later change is visible with its reason; AI members add changes nobody in the organization chose, because producers change their models.

## Grounding

This module is here so that the founder can set structure before the first incident rather than after it: organizations often learn their rules from failure, and a founder who knows how organizations fail can choose some of that structure in advance. No theory is claimed for it, because none has been read for it. It is therefore a design guess, which a scholar may theorize and test, for example by running organizations with it on and with it off and comparing their records. Its `lit:` lines, where it has any, are leads unless they say read (`docs/LITERATURE.md`).
