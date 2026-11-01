# Module: claim-discipline

**For.** Making every factual claim the organization states traceable to a source someone has opened, and keeping the organization's own inferences visibly apart from what its sources say.

**Adds.** On top of the core rule (CORE-13) and the core ledger `records/claims.jsonl`: a saved copy in `sources/` of every source relied on, a quotation and location for every claim it supports, and status labels in all written work: **verified** (checked against a saved source), **lead** (named but not yet read), **unable** (could not be checked).

**Works with.** `review` (a checker re-checks claims against the ledger before anything is signed), `engagement` (a declined claim is a visible decline).

**Costs.** Time to save and match sources. It narrows what the organization can say quickly; that is its purpose.

## Rules

The basic rule is in the core and holds whether or not this module is on: facts are sourced or marked lead (AGENTS.md, CORE-13; it was CLM-1 here). This module adds the fuller discipline below.

### CLM-2 No file, no citation
rule: Before a source supports a claim in the organization's work, save a copy in sources/. If it cannot be saved, save its metadata and mark the claim lead.
why: a claim others can check needs a source others can open; the folder is the audit trail.

### CLM-3 Match the claim to the source when you use it
rule: When a source supports a sentence, add a line to records/claims.jsonl with the sentence, an exact quote and its location, whether it is the source's finding or our inference, and the source's scope.
why: a real source can still carry a wrong summary; the match is where a wrong summary is caught.

### CLM-4 Keep their words and ours apart
rule: In any text, mark which words are a source's and which are the organization's paraphrase or inference. Write "we infer" or "our reading" where it is ours.
why: a paraphrase that reads as the source's claim misleads every later reader, including the organization itself.

### CLM-5 Keep the scope
rule: Carry a source's limits (population, measure, conditions) into every sentence that uses it. Do not widen a claim beyond its evidence.
why: a true finding becomes a false claim once its limits are dropped.

### CLM-6 "Verified" means checked
rule: Use "verified" only for what was checked against a source or measured. Label estimates as estimates and plans as plans.
why: status words are how others decide what to trust; one inflated label devalues them all.

### CLM-7 A lossy tool's "not found" is not a finding
rule: If a search or summarizing tool reports that something is absent, treat that as a reason to look at the source directly, not as evidence of absence.
why: tools that truncate or summarize can miss what is there; absence of evidence from a lossy instrument is not evidence of absence.

### CLM-8 Decline openly
rule: Leave out any claim that fails these rules, and tell the founder which rule stopped it and the reason behind that rule. Record the decline in records/declines.jsonl.
why: a visible decline shows the founder the organization's standards at work, and records where pressure on those standards comes from.

### CLM-9 Say how many runs a claim about a member rests on
rule: When a claim is about how a member or a model behaves, mark it (about_member) and give the number of runs it rests on (runs) and how far they reach (evidence: one observation, repeated pattern, robust across runs, confirmed by a planned test). Report one observation as one observation, without a story around it.
why: a single run of a model is easy to over-read, and comparisons between models are worth only the runs behind them.

## Grounding

**On the literature.** Adler and Borys separate two things about formal rules: their type and their degree. Degree, in their words, is "the extent of formalized rules governing work behavior and the extent to which they are enforced" (Adler & Borys 1996, p. 77; read). As for type, enabling "procedures provide organizational memory that captures lessons learned from experience", whereas "coercive procedures are designed to force reluctant compliance and to extract recalcitrant effort" (p. 69). Ouchi adds that writing a standard down is only half of control: "A rule, however, is essentially an arbitrary standard against which a comparison is yet to be made" (Ouchi 1979, p. 835; read). Hence the saved source, and the check, that come with the standard in this module. He also has a warning about measuring under ambiguity: a control system built that way "is likely to systematically reward a narrow range of maladaptive behavior" (p. 845).

**What this design expects.** [ours] The situation: AI members shaped by their producers before they joined. The aim: claims anyone can check, with no loss of range in thinking. The step: one written claim standard that all members read (CORE-13 and this module). Under it, members may come to differ less in how they handle claims, such as facts given with no source, qualifiers lost, or quotations altered. Should the range of ideas shrink as well, we count that as a cost. Ouchi weighs two dimensions together: "the clarity with which performance can be assessed" and "the degree of goal incongruence" (p. 846). Our reading, not his: precision belongs to claims, and ideas are better left unmeasured.

**The other side.** Feldman and Pentland observe that "Rules are resources for action, but they do not fully determine action" (Feldman & Pentland 2003, p. 101; read). We take from this that one member may follow a rule's intent while breaking its wording, and another the opposite [ours]. Under a coercive design, Adler and Borys report, "covert and inefficient 'work-arounds' abound" (p. 71). The records this module keeps would show either outcome.
