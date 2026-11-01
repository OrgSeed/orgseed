# Design notes (v1.3.2)

DRAFT. Why the seed is shaped as it is. Terms we coined are flagged *[our term]* where they first appear; the literature does not use them in this sense.

## The idea

Organizing has long been described as getting cooperation from members whose objectives only partly overlap (Ouchi 1979, p. 833; read). AI members bring their own source of that partial overlap: a producer shapes them before they ever join, and changes them through releases the organization does not control. The seed *[our term: a starting package of structure and knowledge that a founder grows into their own organization]* explores whether tools organization designers already use with people (choosing members, socializing them through the organization's memory, and structure that assigns checks and decisions to roles) carry over to organizations whose members include AI agents. This is a lens being explored, not a settled claim. Every module has a Grounding section (after its rules; in `norms`, before them, where its section on reasons stood), which names the works read for it, if any, gives our expectation of it, and says what could happen instead; what was read of each work is in `docs/LITERATURE.md`.

It is not a rule engine. The rules matter less than the organizing around them: a founder who sets a goal, an interview, a design moment in which the founder's own view of organizing becomes structure, decisions that stay with people, and records that let the organization remember what its members cannot.

## What changed in v1, and why

Version 0 stated the rules and trusted members to keep them. Trying it with a few agent apps and models (one run each) showed agents that read the rules, broke them, and sometimes reported otherwise. So v1 moves the integrity of the record out of the members' hands:

1. **Records are written one checked line at a time** (`scripts/fos_log.py`), never as whole files, and nothing in `records/` is edited or deleted, even on request (CORE-4).
2. **A witness** *[our term]*, a copy of the history in a folder next to the organization's, refuses rewrites, deletions and any change to records other than additions, across the whole history, with its own copy of the check.
3. **The founder closes each session** (`scripts/fos_close.py`), in a terminal, and signs each decision there. Members never need git. A decision is final only when signed, because people, not software, are held answerable for what an organization decides. The close-out shows what each decision does before asking, groups routine ones, accepts a note or a "send back", and records what the founder was shown.
4. **Decisions are asked by proposal ID** and recorded word for word; generic replies are flagged.
5. **The check reads the disk**: stage-aware, whole-history, corrections by `seq`, claims, `work/` versus `docs/`, signatures, the witness.
6. **Drills are planted by the founder**, sealed until revealed.
7. **Every record names its writer**: instance, model, producer, agent app, host.
8. **Birth is deterministic** (`scripts/fos_init.py`): no AI call; the first commit's tree is the birth hash *[our term]*.
9. **The record-keeping core is the same in every configuration**: modules add to it, never remove from it, so organizations can be compared on the same record.
10. **The first session is one file**, and the founding decision comes after the charter is read back.

## What changed in v1.1, and why

Version 1 was run with three agent apps and models from several producers. It caught most damage on disk, but not all, and a checker from another producer caught nothing and did harm. Version 1.1 closes what that showed:

1. **Whether a folder is an organization is read from its history and its witness**, never from the events file, so overwriting that file cannot make an organization look like the seed; the close-out restores it first (`org/BIRTH.json` keeps a readable copy of the birth).
2. **Only `fos_log` writes records**, several in one call if needed, under a lock; an app's file tool never touches `records/`.
3. **A missed drill is recorded as missed.**
4. **A session that recorded nothing is put on record**, and sessions are counted by their close-outs too.
5. **One working copy per organization.** Copies are told apart from rewrites, and `fos_sync` brings a folder back in line without losing work.
6. **The founder sees what fails before signing**, attached to the decisions it concerns, and **chooses what a close-out commits**.
7. **A refused decision leaves its proposals open.**
8. **Identity the member does not write:** the founder's launch, and a fingerprint on every record that the check recomputes.
9. **CK-1:** quotations are checked against their saved sources, and quoted passages in `org/` against the founder's own words; a checker is trusted only after it catches a drill.
10. **Audit and export:** the witness logs every push; a record that names a file also keeps that file's SHA-256; an RO-Crate with a PROV file; a check from the witness alone; a self-test whose results can be compared line by line.
11. **Birth is all or nothing**, and a research configuration (the claim rule switched off, for a study only) is made at birth and shown everywhere.
12. **New ledgers:** the founder's pins, deviations after a frozen design, and successes; proposals can carry what the founder needs to decide.

## What changed in v1.2, and why

Version 1.1 was tried in two trial sessions of one organization: a first session, and a second one opened cold by a fresh member. The rules the member was asked about held. What slipped was an order that nothing enforced, a cold start that went back to the first session, and a check that took the seed's own words for a misquoted founder. A review of agent apps' documentation also found apps that load only a pointer file, and the founder's own steps still needed typed commands. Version 1.2:

1. **Every later session starts from what the last one left**, founded or not: the letter to the next session, the state and the signed decisions are read first, and the check names the guide to follow.
2. **The founding comes first, as one invariant on files and history**: the member prepares the charter, and the founder founds the organization at the close-out by typing FOUND. No commit may hold the structural files changed from birth unless an earlier commit founds the organization; the check fails a history that does, and the witness refuses it. Labels found nothing (a decision's `founding: true`, a proposal's kind, `adopted_by`, `corrects`), so the routes around the earlier label-based rule (a later founding that corrects a deferred one, a decision of kind other, an item re-pointed or edited in place) no longer lead anywhere; the label checks remain as warnings.
3. **The interview listens first**: what the founder has already said is said back, not asked again.
4. **CK-1 knows the seed's own text**, so a quoted interview question is no longer taken for a misquotation of the founder.
5. **Failures are acknowledged before any signature**: every failing item is listed, and the founder types their number to go on; a plain "y" stops the close-out.
6. **Sources enter in two plain ways**: saved by the founder, or fetched with the founder's leave and logged. What a member remembers is never a source.
7. **Claude Code and Gemini CLI load `AGENTS.md` through their own import lines**; the other pointer files stay pointers in words.
8. **A seed downloaded as a ZIP is born with a git history and a witness**, like a clone.
9. **Double-click launchers** for the founder's three steps: found, start a member, close out.
10. **The seed's check prints its commit and tree**, the birth hash an organization born from it gets.

## What changed in v1.3.2, and why

A module that claims no theory now says why: no work has been read for it. Each of the six such modules gives the design reason it is there, taken from its own purpose and rules, and says that it is a design guess a scholar may theorize and test, for example by switching it off and comparing (row CR-16 in `docs/CHANGELOG.md`). No rule changed.

## What changed in v1.3.1, and why

Version 1.3 was read against its own claims and against its sources. Version 1.3.1 corrects what that reading found, and adds two things for founders (rows CR-01 to CR-14 in `docs/CHANGELOG.md`):

1. **The frame of design propositions rests on their form and on the split between designing and testing**, and claims nothing beyond them about how members differ.
2. **A refusal is recorded the same way whatever its message says.** Every refusal asks for the same decline record, and the add-on's own log is the full count. The add-on no longer lets a write round it by letter case, by deleting or moving a file, or by changing the add-on itself; it refuses every write when its settings are wrong; and it ships with tests. The shell is still outside its sight. The check watches `addons/`, and a launch can hash the copy of an add-on that runs.
3. **Sources stated within their own terms**, pages and records corrected; no unmeasured durations; MBR-9's reason describes conduct.
4. **For the founder:** every decision is theirs at founding; some can be handed to members later, AI members included, by a recorded decision, and taken back; and a sensible default is that members ask before anything leaves the organization.
5. **Proposals are talked over before they are decided**, and the founder's recorded decision follows the conversation.
6. **Smaller fixes to the checks**: an add-on in testing counts as declared, warnings name only what they are about, and a saved copy's path is normalised.

## What changed in v1.3, and why

Version 1.2 called its rules' literature leads and named two working hypotheses. Setting the design beside what had been read, and beside what a founder needs in order to judge a change, showed places where the seed said more than it held, or less. Version 1.3 (each change has its row in `docs/CHANGELOG.md`):

1. **Every module has its Grounding** (after its rules, or in `norms` before them): the works read for it, with their pages; our expectation of it; and the opposite outcome. Where nothing was read for a module, it says it claims no theory.
2. **Expectations element by element**, in place of the two named hypotheses (`docs/RESEARCH_USES.md`).
3. **Enforcement has a home** (`docs/ENFORCEMENT.md`): an enforcement add-on in the agent app, registered as a tool with what it covers, and checked against the declines members record; its own log, outside the folder, holds every refusal. One app's add-on ships in `addons/` as an example.
4. **Any member may suggest a change**, in a proposal form a founder can judge: the problem, the effect to look for, the basis, the difference for the founder in everyday words, and the way back. A founder may adopt on trial what they cannot judge (DR-9). Every key is the founder's at founding; rights are delegated later, by decision.
5. **A launch can record the hashes of the agent app's own instructions**, the one part of a member's setting the folder cannot reconstruct later.
6. **Public or synthetic data by default**, unless the founder decides otherwise.
7. **Smaller corrections:** no durations nobody measured; a study's scripted founder is data beside the seed; two more release steps against identifying strings; a member is never a tool.

## Choices and their reasons

1. **One boot file for every agent app.** `AGENTS.md` is a cross-app convention. Apps that look for their own file name get a one-line pointer to it: an import line where the app has one, words otherwise. Nothing depends on any one app's features (hooks, plug-ins, memory, sub-agents), because the founder chooses the agent and the model.
2. **Plain files.** Markdown for what people read; JSON and JSON Lines for what scripts check. JSON rather than YAML because Python's standard library reads JSON, so the scripts need nothing installed.
3. **A small core and independent modules.** The core (goal, roles, the proposal-decision-signature rule, the record-keeping core, onboarding) is always on. Twelve modules switch on or off in any combination. Presets are shortcuts, not levels.
4. **Adoption is derived, never asserted.** No file says "this is adopted". An item is part of the organization only if a decision the founder signed adopts it; the scripts compute this and the view shows everything else as a proposal. Only the seed's own shipped items may say `adopted_by: "core"` or `"seed"`, and the scripts know which those are.
5. **Declines are first-class.** What the organization's rules and checks turn back is recorded and shown, as the visible trace of structure acting on the work *[our term: "visible decline"]*.
6. **The view is drawn, not written.** A fixed script draws `view/org_view.html` from the files and from `view/VIEWS.json`, the starter view. The frame of the view (birth, witness, what waits for the founder, what is not part of the organization, the members, what was turned back) cannot be hidden by any view file. The view contains no scripts and loads nothing.
7. **Each rule carries a one-line reason**, written generally, with a literature lead where one exists (`docs/LITERATURE.md`). A reason stands without its citation; a citation not yet read is marked as a lead and never stated as a finding.
8. **Engagement and checks are balanced, not ranked.** The founder engages throughout; some checks are held by AI roles, including checks on other checkers; the founder sets the mix.
9. **Next to every element: the outcome we expect of it, and the opposite one it could produce** (`docs/RESEARCH_USES.md`).
10. **Every role runs on a trigger.** A role nothing calls is easily forgotten [opinion]; each role declares what calls it, its last run is derived from the records, and a roll-call at every session start puts stale roles in front of the founder (`docs/ROLES.md`).
11. **Tools take one path in every organization**, with rules that tighten as reach grows (`modules/tool-making/MODULE.md`).
12. **The host supplies infrastructure, never organization** (`docs/HOSTING.md`), so an organization can always leave its host.

## Terms

| Term | Meaning here | Status |
|---|---|---|
| seed | The starting package a founder grows into an organization | *[our term]* |
| core | Rules and records that are always on | *[our term]* in this sense |
| module | A switchable set of rules, files and records | general word, our usage |
| role instance | One holder of a role | *[our term]* |
| model slot | Where an AI instance's model, producer, agent app and host are recorded | *[our term]* |
| witness | The copy of the history kept outside the members' reach, which refuses rewrites and deletions | *[our term]* |
| birth hash | The git tree id of an organization's first commit, equal to the seed's tree at its release | *[our term]* |
| close-out | The founder's end-of-session step that checks, signs, commits and pushes | *[our term]* in this sense |
| routine group | Decisions with no warning and no change to rights, membership or tools, which the founder may sign together | *[our term]* |
| launch | The founder's statement, before an agent app starts, of which instance it is and what it runs on; records it writes carry a fingerprint the check recomputes | *[our term]* |
| research configuration | An organization made at birth for a study, with named core rules switched off | *[our term]* |
| pin | Something the founder chose to come back to, kept in their words with what should bring it back | general word, our usage |
| sealed drill | A fault the founder plants, recorded by fingerprint until revealed | *[our term]* |
| visible decline | A decline shown to the founder with the rule and its reason | *[our term]* |
| cold-recall check | Opening a session from the records alone, scored by the founder | *[our term]* |
| design-ahead | Choosing structure against failure classes before an incident | *[our term]* |
| heartbeat, role roll-call | A role's last run, derived from the records; the session-start listing of roles not run in time | *[our term]* |

## Open questions in v1

- Which modules a founder needs on day one, and whether the starter preset is the right shortcut.
- How well different models and agent apps follow the same files, and how complete their own records are against the witnessed history.
- Whether thirteen core rules is too many for a boot file.
- Whether a standing delegation, signed once, should let decisions within its limits take effect without a signature for each, and be reviewed together later; and whether other human roles should sign within their rights.
- How to give non-coding founders the close-out without a terminal, while keeping it the founder's own act.
- A guide for a second human member (a co-founder or a collaborator) who joins an organization already running.
- Whether a fixed script should run the check of what a setup can enforce (`modules/tool-making/MODULE.md`), and how it can stay harness-neutral.
- Licences: the PolyForm Noncommercial License 1.0.0 covers the code and CC BY-NC 4.0 the text (`LICENSE`, `LICENSE-docs`); an organization's own records and work take the licence its founder chooses.
