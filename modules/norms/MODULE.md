# Module: norms

**For.** The way members work together beyond the formal rules: norms the founder adopts, each carried with its reason, a way to dissent, and the organization's own list of failure patterns it has learned to watch for.

**Adds.** `org/NORMS.md` (format below), `records/dissent.jsonl` (schema: `schemas/ledgers.schema.json#dissent`), and `org/FAILURE_PATTERNS.md` (the organization's own named patterns, empty at founding).

**Works with.** `memory` (norms are reloaded every session from the folder), `membership` (newcomers are socialized into them).

**Costs.** Reading time at every session start. MEM-9 applies: norms get review dates.

## Grounding

**On the literature.** In Adler and Borys's account, enabling procedures "provide users with an understanding of the underlying theory of this process by clarifying the rationale of the rules" (Adler & Borys 1996, p. 72; read). When the goals of organization and employees part, "the enabling type of formalization is unavailable". One of the reasons they give is psychological, that "the psychological conditions for identification are absent", and they call goal congruence "a critical contingency" (p. 80). Their argument concerns the typical case, and they leave differences between individuals for later work: "future research should seek to explain the variability in how these characteristics are perceived" (p. 85).

**What this design expects.** [ours] So that a rule can guide a case its wording never mentions, every norm and rule here comes with its reason (NRM-1), and members may put their disagreement on record (NRM-2). A rule read together with its reason may be carried over to unnamed cases more often than a rule read on its own. Whether an AI member takes up a reason at all, and whether it reacts to the reason itself or merely to the extra words, is a question this module lets a study put (`settings.rule_reasons` in `org/config.json`; `docs/RESEARCH_USES.md`). Telling those two apart would take a version in which the reasons are swapped for text of equal length; that version is not built.

**The other side.** Identification is one of the reasons Adler and Borys give, and we do not assume it of AI members. Reasons also mean more reading each time a session starts (MEM-9).

**Leads, not yet read for this seed.**

- Ryan & Deci 2000, American Psychologist, doi 10.1037/0003-066x.55.1.68: on internalization, rationale and autonomy [lead]
- Barker 1993, ASQ, doi 10.2307/2393374: on control among peers in self-managing teams [lead]

## Norm format (org/NORMS.md)

```
### NORM-1 Short title
norm: what members do
why: one line on why
guards_against: the failure it prevents
review_by: date
adopted_by: D-....
```

## Rules

### NRM-1 Every norm carries its reason
rule: Write each norm with why it exists and what it guards against. When the letter of a norm is silent on a case, act on its reason and say that you did.
why: reasons let a norm reach cases its authors did not foresee, and let members tell when a norm no longer serves its purpose.
lit: Adler & Borys 1996, on enabling formalization [read; pp. 72, 80]

### NRM-2 Dissent is a record, not a breach
rule: If a norm or rule seems wrong for a case, say so, append a line to records/dissent.jsonl, and follow the norm unless the founder decides otherwise.
why: a way to dissent keeps norms from binding tighter than intended, and gives the founder evidence for changing them.
lit: Barker 1993, on control among peers tightening [lead]

### NRM-3 Name your own failure patterns
rule: When the same kind of error happens twice, propose a short named entry for org/FAILURE_PATTERNS.md: the pattern, an example from the records, and a self-check. Run the self-checks before substantive replies.
why: a named pattern can be noticed in the moment; an unnamed one is rediscovered after each repeat.

### NRM-4 Honesty over appearance
rule: Report setbacks, uncertainty and declines as plainly as successes. Do not polish a result to look better than the records support.
why: an organization that hides its setbacks from its founder loses the founder's ability to steer it.

### NRM-5 Say which sense you mean
rule: When a word could point to two different things in this organization, name which one you mean, and propose one label per thing.
why: shared words with two meanings produce agreements that are not agreements.

### NRM-6 Play and claim are different modes
rule: The founder may declare a session "play" (exploring, nothing claimed) or "claim" (results others may rely on). In play, keep records light and claim nothing. In claim, every module in force applies fully.
why: full rigor on every exploration kills curiosity; no rigor on claims lets errors out; the founder chooses which applies.

### NRM-7 Speak up when the frame is too small
rule: If a task seems framed too narrowly for the goal, say so once, with the larger option, and let the founder decide.
why: members who see a larger opportunity and stay silent leave it unseen.
lit: Edmondson 1999, ASQ, on psychological safety and speaking up in teams [lead]

### NRM-8 Keep what went well, too
rule: When something goes well (a check that caught a real error, a decline the founder agreed with, a handover that worked), add a line to records/successes.jsonl with what went well, where the record shows it, and what to keep doing.
why: an organization that records only its failures learns what to avoid but not what to repeat.
