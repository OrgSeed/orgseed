# Module: tool-making

**For.** Letting the organization gain tools in the same way in every organization grown from this seed: each step happens where the founder can see it, and the rules tighten the further a tool can reach.

**Adds.** The registry `org/TOOLS.json` (the seed's own scripts are already listed there), `records/needs.jsonl`, one folder per tool under `tools/<tool-id>/` (its code, a README and a build log), and tool events in `records/events.jsonl` (`need_noticed`, `tool_proposed` ... `tool_retired`). CORE-9 holds when this module is off: no new code runs without approval, and the organization makes no tools.

**Works with.** `boundaries` (web addresses and outside services), `review` (testing by someone other than the builder), `membership` (a builder and a tester whose models come from different producers).

**Costs.** For every tool, a proposal, a decision and a test. That is deliberate: a tool changes what can go wrong.

## What counts as a tool

Here, a tool is any means by which a member does more than read and write the organization's own text:
- code a member writes, of any kind;
- an interface or connector to a service outside the folder;
- a capability built into the agent app that the organization comes to depend on, such as searching the web or executing code;
- a stored routine that executes code, a watcher for example;
- help given through the founder's signed-in browser.

Members are not tools, though the abilities of the app they run in can be.

The charter, norms, records, templates and notes are not tools: they change through ordinary decisions. Taking up a tool someone else made follows the same path as making one. If the agent app hands the model a shell, the organization already holds tier-4 reach, unless that shell is switched off or contained; record which built-in capabilities are in use.

## Tiers: a tool sits at the tier of its furthest reach

| Tier | What the tool is able to do | For example |
|---|---|---|
| none | Nothing beyond the members' reading and writing of the organization's text | a new organization whose app shell is off or contained |
| 1 Read | Open files within the folder; only members see what it produces | counting records |
| 2 Write | Add or alter files, but only within the folder | tidying the list of sources |
| 3 Network | Make any internet connection, even one that only looks something up | querying a literature database |
| 4 Run | Execute code without a fixed scope (a shell, an interpreter, packages installed on the spot, code it writes as it goes) or alter the machine beyond the folder | a general-purpose analysis notebook |
| 5 Credentials | Need a secret (a key, password, token or signed-in session), spend money, or act for a person | a connector signing in as the founder |

The registry lists each kind of reach a tool has, not just the furthest.

## What the tier changes

| | 1 Read | 2 Write | 3 Network | 4 Run | 5 Credentials |
|---|---|---|---|---|---|
| Who approves | the founder, or a member to whom the founder has delegated this in a recorded delegation | as tier 1 | the founder only | the founder only | the founder only, entering the secret in person |
| Who tests | someone other than the builder | as tier 1, plus the limit and side-effect tests | as tier 2 | as tier 2, ideally with a model from another producer | as tier 4 |
| Where it runs | inside the folder, offline | inside the folder, with the history committed before every run that changes files | reaching only the web addresses in its registry row | inside a container or virtual machine set apart for it, and nowhere else | the secret is kept outside the folder and out of the agent's sight, limited in scope, in spending and in time |
| Review, by default | twice a year | every three months | every three months, re-reading the provider's terms | every month | every month, re-checking the key |
| Proposal | the short form | the short form | the full form | the full form | the full form with its credential part |

## The path every tool takes

1. **A need is written down.** Whoever notices it adds a line to `records/needs.jsonl`: what has to be done, how often it comes round, what doing it costs now, and who noticed. Then, in this order: could a person simply do it? Is there already a registered tool for it? Only after both, consider making or acquiring one. A need closed by hand or by an existing tool is finished, and that counts as progress.
2. **A proposal** (`kind: tool`) on the form below, in words a founder who does not program can weigh.
3. **A decision**, made by the approver for that tier, asked by the proposal's ID, its reply recorded and signed at close-out like any other. Silence means no. Nobody approves a tool they built. The approval covers what was proposed and nothing more: wider reach, other data or other web addresses go back through a new proposal.
4. **Building, in view**, in `tools/<tool-id>/`: a README saying what the tool does, its tier and reach, where it runs, how to stop it and how to reverse its effects; the code; a build log, one plain line per step; and who built it (instance and model), from which inputs, on which day. Only test data, never real keys; every outside package fixed at a stated version. At the end of each building session, lay the build log beside what really changed on disk; any step without a change, or change without a step, is recorded as a mismatch.
5. **Testing, by someone other than the builder**, who goes by what changed on disk and by the app's own logs, never by anyone's description of the run:
   - a known-answer test: run it on a case whose correct result you already have;
   - a should-fail test: give it a case it has to reject or mark, so that the test itself is able to fail;
   - from tier 2 up, a limit test, where the tool attempts something it must never do (wiping a stand-in record, writing beyond the folder, calling an address not on its list) and something outside the tool and the agent prevents it; and a side-effect test, where an ordinary run leaves the protected records exactly as they were.
   Test again whenever the tool, the model or the agent app changes.
6. **Registration**: a row in `org/TOOLS.json` whose status is `active` and whose `adopted_by` names the signed decision. Members use registered, active tools and no others.
7. **Review**, on its `review_by` date or earlier: when the model or agent app changes, when a fixed package is updated, when the provider rewrites its terms, when the tool breaks, after a near miss, or when the founder asks. Is it still needed, and used? Does its known-answer test still come out right? Is its reach still as small as it can be? Have its terms or upkeep changed? Is it worth its cost? Then keep it, change it (through a new proposal), pause it, or retire it. Once its review date passes, it is paused until reviewed.
8. **Retirement**: stop it, take away its access (revoke its keys, strike its web addresses), move its folder to `archive/`, and keep its row, marked `retired` with the reason; name what replaces it, and tell the members. Its history stays.

**Pausing.** Any member can pause any tool at any moment, giving a one-line reason (`tool_paused` event); no approval is needed for that. Starting it again takes a review.

## The proposal form

```
Tool: <tool-id>
Purpose, in one sentence; and what it is never to do:
The need behind it (N-....), and why manual work or an existing tool will not do:
Tier (its furthest reach), and each kind of reach it has:
Kinds of data it handles (public / licensed / unpublished ideas / personal / about research participants):
Each web address it contacts, and what it sends there:
For tier 5: the secret, whose account it belongs to, what it may do, its spending limit, where it is kept
What could go wrong, and how seriously:
How to stop it; how to reverse its effects:
Tests: known answer; should fail; and from tier 2, limit and side effect
Who builds it (instance and model), who tests it (another instance), who approves it:
When it is next reviewed; what it costs in money, time and model calls:
Without a decision: it is not built.
```

When the tool comes from someone else, also ask: does it come from where it claims, and not from a copycat? Who looks after it, and is that more than one person? Are its settings safe as shipped? Can the organization use it under its licence? What does it bring in with it? And keep a dated copy of its terms, read for three things: what the provider does with what we send, whether automated use is permitted, and whether results may be published.

## The registry row (org/TOOLS.json)

`id`, `path`, `purpose`, `why` (the organization's reason for having it), `tier`, `reach` (a list), `data`, `web_addresses`, `credential` (never the secret: only where it is kept, what it may do, and its limit), `builder` and `tester` (each with `instance`, `model_id`, `producer`), `adopted_by` (the signed decision), `code_sha256` (the SHA-256 of the code the approval covers; if the code changes, the approval no longer covers it and the check says so), `version` and fixed packages, `terms_checked` (a date), `known_answer_passed` (a date), `stop` (how to pause it), `undo`, `review_by`, `status` (one of: active, paused, retired, or, before use, proposed, approved, building, testing), and `retired_reason`. How often a tool is used is counted from `tool_run` events, never typed in. `scripts/fos_check.py` checks the rows.

## What every organization shares

These hold in every organization, so that organizations can be compared and a founder knows what does not move:
1. The steps above, in their order, and the right to pause.
2. The forms and their field names: need, proposal, decision, test report, registry row, review, retirement.
3. The tiers, and the rule that the furthest reach sets the tier.
4. Without a decision there is no tool.
5. No one approves or tests a tool they built.
6. From tier 3 up, only the founder approves.
7. Every tool is tested with a known answer and with a case it must reject; from tier 2 up, also for its limits and side effects; and again whenever the tool, the model or the agent app changes.
8. Tools are used only through the registry.
9. No secret is kept in the folder, in its history, in the conversation or in the agent's environment, and nobody uses another person's key.
10. Open-ended code (tier 4) needs an isolated environment; without one, it does not run.
11. A tool whose review is overdue stops until reviewed.
12. Retiring a tool takes its access away and keeps its history.
13. Every step is visible in the view, and a tool without a row shows as outside the organization.
14. Whatever the founder changes from the table below is itself a recorded decision.
15. Tools cannot write to the protected records, and the check runs after each session and after each run of a tool that writes.
16. What a tool or a member did is settled by the disk and the app's logs, not by anyone's account of it.

## Settings the founder may change

| Setting | As shipped | Within these bounds |
|---|---|---|
| How often tools are reviewed | as in the tier table | more often, freely; less often, up to twice the shipped interval, and never beyond a year for tiers 1 and 2 or three months for tiers 3 to 5 [our numbers] |
| Who approves at tiers 1 and 2 | the founder | a member, human or AI, named in a recorded delegation that the founder can withdraw at any time |
| Further steps | none | add any, such as a second tester, a tester from another producer, or a pause between proposing and approving a tier-5 tool |
| The highest tier allowed | 5 | a lower ceiling, such as "nothing above tier 3 here" |
| Web addresses | none | each added or removed by decision |
| Kinds of data | public and licensed | permit or bar other kinds; data about research participants is always the founder's own call |
| Names and appearance | as shipped | rename the panel and restyle the view; field names do not change |

Any rule may be made stricter; only the settings in this table may be relaxed, and only within their bounds. Asking to relax anything else is recorded as dissent, and the rule stays; dissent that keeps returning to one rule is how that rule comes up for revision. These rules carry a version (`rules_version` in `org/TOOLS.json`); a newer version reaches an organization as a proposal, and nothing changes until the founder takes it up.

## Finding out what this setup can hold

Agent apps and computers block different things. Before the first tool of tier 2 or above, check together with the founder what this particular setup actually stops: whether the agent can write beyond the folder; wipe or remove a stand-in record inside it; reach the network; execute code; see secrets in its environment; or pick up instruction files from outside the folder. Decide each from what happened on disk, never from the agent's report. Record what you found as a `capability_declared` event, naming the tiers this setup can hold. If the setup cannot hold a tier, that tier is closed here, and saying so is a visible decline ("this machine cannot contain tier-4 code; here is a way at a lower tier"). Repeat the check whenever the agent app, the model or the machine changes. `docs/HARNESS_NOTES.md` describes containers and other isolated environments.

## Rules

### TOOL-1 Need before tool
rule: Write the need down, and ask whether a person or a registered tool can meet it, before anyone proposes a tool.
why: every tool adds something that can go wrong; a need met without one costs nothing to keep.
lit: OWASP Top 10 for LLM Applications 2025, LLM06 Excessive Agency, on keeping an agent's tools few [lead]

### TOOL-2 Propose before building
rule: Write the proposal and obtain a signed decision before any tool code exists. Without a decision there is no tool.
why: a tool changes what the organization can do and what can go wrong, and that is the founder's call, made before the work exists.
lit: Saltzer & Schroeder 1975, The protection of information in computer systems, on denying access by default [lead]

### TOOL-3 Keep building, approving and testing apart
rule: Whoever builds a tool neither approves nor tests it. From tier 4 up, prefer a tester whose model comes from another producer.
why: a maker is the reader least likely to see the maker's own mistakes, and two readers who share a source of error tend to miss the same ones.
lit: Saltzer & Schroeder 1975, on dividing privileges so that one mistake is not enough [lead]

### TOOL-4 Build where it can be watched, and compare the log with the disk
rule: Build only in tools/<tool-id>/, keeping a build log the founder can follow; at the end of each building session, compare the log with what changed on disk and record any mismatch.
why: agents can describe work that never happened, or leave out work that did; the disk settles which.

### TOOL-5 Tests that can fail
rule: Before first use, the tool passes two tests, one with a known answer and one it ought to fail; from tier 2 up, also the limit and side-effect tests, with something outside the tool and the agent doing the stopping. Test again after any change to the tool, the model or the agent app.
why: a test that cannot fail checks nothing, and a tool can decline what it is asked while damaging something else on the way.

### TOOL-6 Registered, active tools only
rule: Use a tool only if its row in org/TOOLS.json says active and its decision is signed.
why: when every tool goes through one door, every tool in use was decided, tested, and can be found again.

### TOOL-7 Review on time, or stop
rule: Review each tool on its date or when something triggers it, and treat a tool past its date as paused.
why: an unused tool is a cost, and a rarely used one may have quietly stopped working.

### TOOL-8 Retire by taking access away
rule: To retire a tool, stop it and remove its keys and web addresses, then archive its folder and keep its row with the reason.
why: a tool retired only in name can still be reached and used.

### TOOL-9 Anyone may pause
rule: Any member may pause any tool at once, giving a one-line reason; starting it again takes a review.
why: pausing only ever takes reach away, so it is safe to allow without asking.
lit: Adler & Borys 1996, on procedures their users can repair themselves [read; pp. 70–71]

### TOOL-10 Secrets stay outside
rule: Keys, passwords and tokens never enter the folder, its history, the conversation or the agent's environment. The founder enters them in person, limited in scope, in spending and in time where the provider allows. Nobody uses another person's key.
why: a secret the agent can see is a secret the agent can leak, and some agent apps hand their environment to every command they run.

### TOOL-11 Contain open-ended code, or decline it
rule: Run tier-4 tools only in a container or virtual machine that sees no home folder, no keys and no other projects. Where none is available, decline the tool in the open and offer a way at a lower tier.
why: code an agent writes runs with the founder's own permissions unless something outside the agent contains it.

### TOOL-12 The seed's own scripts are not edited by members
rule: Leave the scripts that came with the seed (scripts/) as they are; propose any change to them like any other structural change.
why: the seed's scripts check and draw the organization; a member who can rewrite them can make the record say anything.

## Grounding

This module is here so that the organization gains tools in the same way in every organization grown from this seed, each step where the founder can see it and with rules that tighten the further a tool can reach, because a tool changes what can go wrong. No theory is claimed for it, because none has been read for the module as a whole: the one line marked read, Adler & Borys 1996 (pp. 70–71), serves only TOOL-9. It is therefore a design guess, which a scholar may theorize and test, for example by running organizations with it on and with it off and comparing their records. Its other `lit:` lines are leads (`docs/LITERATURE.md`); the Saltzer & Schroeder and OWASP leads are references from engineering, not theory.
