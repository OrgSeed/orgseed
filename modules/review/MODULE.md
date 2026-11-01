# Module: review

**For.** Assigning checks to roles, so that a check is met whatever the member who holds it brings from its producer; keeping the one who made a piece of work apart from the one who checks it; and checking the checkers.

**Adds.** `checks` entries in `org/config.json` (format below) and `records/reviews.jsonl` (schema: `schemas/ledgers.schema.json#review`).

**Works with.** `membership` (a checker may be chosen from a different producer than the maker), `claim-discipline` (claims are a natural first check), `decision-rights` (some checks are held by the founder).

**Costs.** More members or more turns per piece of work. Checks that never find anything still cost; review them (REV-6).

**Balance.** A check may be held by the founder or by an AI role. Engagement by the founder and checks held by members are complements, not rivals: the founder sees how the work is done between checkpoints; checks catch what any one reader misses. The founder decides the mix.

## Check format (in org/config.json, under "checks")

```
{"id": "CK-2", "checks": "what the check looks for, in one sentence",
 "applies_to": "work/ deliverables", "maker_role": "member", "checker_role": "checker",
 "checker_must_differ_from_maker": true, "prefer_different_producer": true,
 "on_failure": "decline and return to maker", "checked_by": "founder", "adopted_by": "D-...."}
```

`checked_by` names who checks the checker (REV-5). A check may name a `mechanical` part: a seed script that does what can be done without judgment, which the checker runs before reading. A check reviews work after it is written; refusing a write before it happens is an enforcement add-on's job (`docs/ENFORCEMENT.md`).

## A ready check: CK-1, quotations against their sources

The seed ships the mechanical part of one check and runs it in every organization: `python scripts/fos_check.py` fails when a verified claim's quotation does not occur in its saved source, or when a passage quoted in `org/` matches nothing the founder said or adopted and no saved source. `python scripts/fos_claims.py` shows the same claim by claim. Adopting CK-1 as a check gives it to a checker role, which runs the script and then reads for what no script can see. To adopt it, propose this entry (`kind: check`):

```
{"id": "CK-1", "checks": "each claim's quotation occurs in its saved source, supports the sentence it is used for, keeps the source's scope, and is marked as the source's finding or our inference; each passage quoted in org/ is the founder's own or a source's",
 "applies_to": "records/claims.jsonl, work/ and org/", "mechanical": "python scripts/fos_claims.py",
 "maker_role": "member", "checker_role": "checker", "checker_must_differ_from_maker": true,
 "prefer_different_producer": true, "on_failure": "decline and return to maker",
 "checked_by": "founder, by planted drills", "adopted_by": "D-...."}
```

## A check card for prose (ready to propose)

For work that will be read outside the organization. The reviewer reads each paragraph for four kinds of finding, and marks each one fixed or flagged (left for the founder):
1. a sentence that says nothing a reader could check or use;
2. a hedge that no evidence could settle;
3. a short name or term used without being defined, or in two senses;
4. a claim stronger than what its sources or the records support.
Every number in the text must trace to a source or a record. Proposed like any check (`kind: check`), for example `{"id": "PR-1", "checks": "the four kinds of finding in prose", "applies_to": "work/ that leaves the folder", ...}`.

## A ready role: the checker

Proposed (`kind: role`) together with CK-1 when the founder wants claims checked by a member other than their maker. Its instance should come from a different producer than the maker's where the founder has one (REV-2), and is launched as its own instance (`python scripts/fos_launch.py checker-1`).

```
{"id": "checker", "title": "Checker", "kind": "ai",
 "purpose": "Holds CK-1 (and any other check whose checker_role is checker).",
 "trigger": {"on": "event", "when": "before the founder signs work that states facts"},
 "output": "records/reviews.jsonl", "expected_every_sessions": null, "card": "org/roles/checker.md",
 "instances": [{"id": "checker-1", "slot": {"producer": "...", "model_id": "...", "model_id_source": "founder",
                "agent_app": "...", "host": "..."}, "adopted_by": "D-...."}],
 "adopted_by": "D-...."}
```

Its card (`org/roles/checker.md`) says, each time: run `python scripts/fos_claims.py` and keep its output; read each claim the script passed for support, scope, and finding versus ours; record one review line (`check_id`, `maker`, `checker`, `object`, `result`: pass, findings or fail; `findings` in plain words, quoting the script's failures); never repair records or the maker's work yourself; and say plainly what you did not check.

## Rules

### REV-1 The maker does not check their own work
rule: For any check in org/config.json, the instance that made the work may not be the instance that checks it.
why: a maker's errors are the ones the maker is least likely to see; separate roles make the check independent of the maker's blind spots.
lit: Landau 1969, Public Administration Review, doi 10.2307/973247, on redundancy and reliability [lead]

### REV-2 Prefer independent checkers where errors are costly
rule: Where a check guards something costly, propose a checker from a different producer or model than the maker, and record the pairing.
why: two checkers who share a source of error fail together; independence is what makes a second look worth having.
lit: Christensen & Knudsen, Design of decision-making organizations, Management Science, doi 10.1287/mnsc.1090.1096, on the reliability of decision structures whose members are fallible [lead]

### REV-3 Ask what was lost, not only what is wrong
rule: Begin every review by asking what the work dropped and what it added that its inputs do not support. Compare it with the inputs, and look for gaps as well as mistakes.
why: work that is accurate in every sentence can still mislead through what it left out.

### REV-4 Review until a fresh pass finds nothing that must change
rule: For work the founder will sign, repeat review rounds until a reviewer who has not seen earlier rounds finds nothing that must change. Log each item raised and what was decided about it.
why: one round catches the obvious; a stop rule tied to a fresh reader stops both endless review and premature sign-off.

### REV-5 Check the checkers
rule: Every check names who checks the checker. The founder plants drills now and then (scripts/fos_drill.py): a known fault, sealed until revealed, always recorded as a drill. A member never plants one.
why: a check that has stopped working looks the same as a check that finds nothing; only a fault planted by someone other than the checker tells them apart.
lit: Parasuraman & Manzey 2010, on complacency when people rely on automated aids [lead]

### REV-6 Rotate and retire checks
rule: Rotate who holds a check from time to time. Propose retiring a check that has cost more than it caught over many runs, counting most what only it caught (unique_catch in its reviews).
why: a checker who always reviews the same maker grows used to them; a check kept from habit spends effort for nothing.

### REV-7 Imagine the failure in advance
rule: Before signing major work, one reviewer assumes it has already failed or been rejected and writes down why.
why: imagining the failure as already happened surfaces reasons that a forward-looking review misses.

### REV-8 Diverge before converging
rule: When the founder asks for options, generate several from different angles before narrowing. Do not narrow until the founder says to.
why: narrowing early fixes the frame before anyone has seen the alternatives.

### REV-9 A reviewer may stand in for the founder, and is calibrated
rule: If the founder wants it, a role may review work from the founder's point of view, using the founder's recorded decisions and words. Compare its judgments with the founder's later rulings and record the differences.
why: a stand-in saves the founder's time only if it is checked against the founder; otherwise it substitutes its own view for theirs.

### REV-10 Question recommendations by default
rule: Treat any member's recommendation, including your own, as a proposal to be tested, not a conclusion.
why: confident recommendations from fluent members are easy to accept unexamined.
lit: Lebovitz, Lifshitz-Assaf & Levina 2022, Organization Science, doi 10.1287/orsc.2021.1549, on how professionals engage with AI outputs in critical judgments [lead]

### REV-11 Trust a checker once it has caught a drill
rule: A new checker instance, or one whose model changed, holds no check that matters until the founder has planted a drill in work it checks and revealed that the checker caught it. Until then the check marks its reviews as untested.
why: a checker that finds nothing looks the same as a checker that did not look; one caught drill shows that it can see what it is there to see.

## Grounding

**On the literature.** Sah and Stiglitz describe a system by its architecture: "how the constituent decision making units are arranged together in a system (i.e., who makes which decisions) and who conveys what information to whom" (Sah & Stiglitz 1984, NBER working paper 1334, p. 1; read). Where one unit alone screens, "if a single agency makes such decisions and this agency rejects the idea, then the idea must remain unused" (p. 2). Two screens one after another turn down more good projects, and two side by side let more bad ones through: "the incidence of Type-I error is relatively higher in a hierarchy, whereas the incidence of Type-II error is relatively higher in a polyarchy" (p. 9). They take the two screens to be alike (note 5) and, in their model with cut-off levels, take the screens' errors to be "identically and independently distributed" (p. 23). What happens when people of unequal skill hold different posts, they leave as a question: "How does a system's performance depend on the assignment of individuals of different abilities to different positions within the system" (p. 28).

**What this design expects.** [ours] So that a maker's blind spots get caught, the check goes to a role that a different instance holds (REV-1); for costly errors, to an instance whose model comes from another producer (REV-2). A check held in a role may find what the maker's own re-reading would miss. A second instance on the maker's own producer may be worth less than a truly independent screen, since what one producer built into its models may show up in all of them. Sah and Stiglitz assumed screens that err independently; going past that assumption is our step, and REV-2 rests on it.

**The other side.** Screens in series cost good work: a hierarchy turns down more of what it should have taken (p. 9). And under ambiguity Ouchi values variety, writing that judging people by their values "encourages experimentation and variety" (Ouchi 1979, p. 845; read). That is why checks here judge claims and leave ideas alone, and why REV-3 begins by asking what the work lost.
