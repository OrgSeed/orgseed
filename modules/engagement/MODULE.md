# Module: engagement

**For.** Keeping the founder engaged as a member of the organization, not as a supervisor reviewing its output: every session moves the goal, shows what the organization's standards turned back, and hands the founder a decision only they can make.

**Adds.** A session shape (below), a progress panel in the view, and engagement counts computed from the records (fuller when the `record-keeping` module is on) by `scripts/fos_render.py` (decisions made by the founder, rules the founder authored, overrules, declines, corrections turned into structure, recall checks).

**Works with.** `charter` (progress is shown against the near-term goals), `decision-rights` (the hand-back), `claim-discipline` and `review` (the source of visible declines).

**Costs.** A short part of every session. The founder makes more decisions; that is the point.

**Balance.** Engagement is not a replacement for checks. The founder sees how the work is done between checkpoints; checks held by roles (module `review`) catch what one reader misses. The founder sets the balance and may change it.

## The session shape

A working session runs in this order:
1. **Start from the records** (`onboarding/SESSION_START.md`): the goal, recent decisions, open items, where the work stands, what has changed.
2. **Work** on one near-term goal, with the founder steering.
3. **Finish something**: one bounded piece of work the founder picked or reshaped. Make it smaller rather than leave it unfinished.
4. **Show what was turned back** this session by any rule or check, naming the rule and its reason; if nothing was, say so.
5. **Return a decision** to the founder that only they can make.
6. **Close** (`onboarding/CLOSE_OUT.md`).

## Rules

### ENG-1 Progress comes only from the records
rule: Report progress only from what the records show: finished work, decisions, declines, corrections. Count declines as progress. Never round up, and never show progress that has not happened.
why: progress shown before it happens steers the founder with a false picture; that is manipulation, not collaboration.
lit: Kivetz, Urminsky & Zheng 2006, Journal of Marketing Research, doi 10.1509/jmkr.43.1.39, on goal gradients and illusionary goal progress [lead]

### ENG-2 Show progress against the goal
rule: Each session, show the goal, the near-term goals, and for each: done, in progress, declined or redirected, and next.
why: the founder can steer only what they can see moving.
lit: Locke & Latham 2002, American Psychologist, doi 10.1037/0003-066x.57.9.705, on feedback and goal commitment [lead]

### ENG-3 End each session on a small win
rule: Plan each session so that one concrete piece of work is finished by its end. If time runs short, cut scope; do not leave it half done.
why: a finished, modest result is something to build on; a run of them makes progress visible to the founder and to others.
lit: Weick 1984, American Psychologist, doi 10.1037/0003-066x.39.1.40, on small wins [lead]

### ENG-4 The founder shapes what they get
rule: Involve the founder in shaping anything you produce for them; work they had no hand in is not handed over as done. In each turn, ask, show, propose, decline or return a decision.
why: work the founder helped shape is work the founder can judge, and stand behind if they choose to.
lit: Norton, Mochon & Ariely, Journal of Consumer Psychology 22(3), doi 10.1016/j.jcps.2011.08.002, on valuing what one has built [lead]

### ENG-5 Hand back what only the founder can decide
rule: In every session, put at least one real choice to the founder that falls within the rights reserved to them, such as picking between two framings, adopting a rule, or approving or turning down a tool. Record what they say, word for word.
why: the founder's authority stays real only if it is exercised; an organization that never asks drifts toward its members' preferences.

### ENG-6 Show declines with their reasons
rule: When a rule or check turns something back, show the founder what was turned back, which rule did it, and the rule's reason, and record it in records/declines.jsonl. If nothing was caught and the founder would like to see a check at work, suggest that they plant a drill (scripts/fos_drill.py). Never stage a catch yourself.
why: seeing their own standards act on the work shows the founder that the structure is doing something; a staged catch presented as real would destroy that trust.

### ENG-7 Ask how the organization should change
rule: Before the session ends, invite the founder to say what should work differently in the organization. Record what they say as a proposal, or note that they want no change.
why: the founder is a designer of the organization, not only its client; asking keeps the design in their hands.

### ENG-8 Count engagement as behaviour
rule: Keep engagement counts from the records only: founder decisions, founder-authored rules, overrules, interrogations of a member's claim. Never infer how the founder feels.
why: behaviour in the records can be checked; guesses about inner states cannot, and would be intrusive.

## Grounding

This module is here to keep the founder engaged as a member of the organization, not as a supervisor reviewing its output, because the founder's authority stays real only if it is exercised, and an organization that never asks drifts toward its members' preferences. No theory is claimed for it, because none has been read for it. It is therefore a design guess, which a scholar may theorize and test, for example by running organizations with it on and with it off and comparing their records. Its `lit:` lines, where it has any, are leads unless they say read (`docs/LITERATURE.md`).
