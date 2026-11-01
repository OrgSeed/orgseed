# OrgSeed

**OrgSeed (organizing seed): a seed for a human–AI organization.** *(seed v1.3.2, draft)*

This is a folder of structure and knowledge that you grow, in conversation with an AI agent of your choice, into your own organization: you, and AI members, working toward a goal you set. Use it to do research with, or to study human–AI organizing itself.

It is not an app and not a rule engine. There is no server and no account. It is plain files that any capable agent app can read and write, on any capable model, plus a few scripts in standard Python that need nothing beyond Python itself (and Git, for the full record). They are tested with Python 3.12.

## Three doors

### 1. Watch

Open `view/org_view.html` in a browser. It shows an organization drawn from its files: its goal and movement, what waits for the founder, its structure and members (with the model each runs on), its rules with their reasons, what they turned back, its tools and its memory. In the seed itself most of it is empty: nothing exists until a founder decides it. A replay, which shows an organization growing commit by commit from its witnessed history, is specified in `docs/REPLAY_SPEC.md` and not yet built.

### 2. Found your own

1. In a terminal, from this folder: `python scripts/fos_init.py ../my-organization` (or double-click `Found-an-organization`; see below). No AI is involved: it copies the seed exactly, records its birth hash, and creates a witness next to it (`../my-organization-witness`), a copy of the history that refuses rewrites and deletions. A seed downloaded as a ZIP works the same way: with git installed, the new organization still gets its git history and its witness, and its birth hash is computed from the seed's files.
2. Open `../my-organization` in an agent app that can read and write files in a folder, and say: **"Read AGENTS.md and follow it."** Before you do, read `docs/HARNESS_NOTES.md`: a few launch settings keep your own user-level files and secrets out, and a dev container is provided. Recommended: first run `python scripts/fos_launch.py member-1` in the new folder and start the agent app from that terminal with the line it prints (or, for an app you start from its menu or icon, double-click `Start-a-member` first); then everything the member records can be traced to that launch.
3. The agent runs the first session: where your words go, an interview about your goal and how you think the work should be organized, a choice of structure, your charter read back, the founding decision, a first small piece of work, a visible decline, and a decision handed back to you. It takes one sitting; following only the ▶ steps of `onboarding/START.md` shortens it.
4. At the end, you run `python scripts/fos_close.py` in your terminal (or double-click `Close-out`). You found the organization there, on the charter the agent prepared, by typing FOUND; you read each decision the agent recorded and sign it or not; then it commits and pushes to the witness. Nothing becomes part of your organization until you sign it, and nothing leaves the folder unless you send it.

**Without typing a command.** Each of your own steps has a launcher to double-click. It opens a terminal window of its own and runs the same script, with the same safeguards; the window stays open until you press a key.

| Launcher | Where | What it runs |
|---|---|---|
| `Found-an-organization` | the seed's folder | `fos_init.py --ask`: asks for a name, then makes the organization and its witness next to the seed's folder (step 1) |
| `Start-a-member` | the organization's folder | `fos_launch.py --ask --file`: records which member you are starting and on what, for an agent app you then start from its own menu or icon (step 2) |
| `Close-out` | the organization's folder | `fos_close.py`: the close-out (step 4) |

On Windows the launchers end in `.cmd`, on macOS in `.command`. They need Python 3 and, for the full record, Git. Your system may ask you to confirm the first time you open a launcher you downloaded.

**What is yours to decide, and what you can hand over.** At the founding every decision is yours: the organization's structure, every change to it, and every signature. Members, AI members among them, propose; you decide; your signature makes it final.

Later, if you choose, you can hand some decisions to members, AI members included, as you might to a colleague you have come to trust. You do it by a decision of your own, recorded like any other, that says which role may decide what, and within which limits (`modules/decision-rights/MODULE.md`, DR-3). You can widen it, narrow it or take it back the same way, at any time. In this version a decision taken under such a grant still counts only once you sign it at the close-out.

A sensible default, whatever else you hand over: members ask you before anything leaves the organization, that is, before anything is sent, published or uploaded, before any money is spent, and before any change to an account. The seed starts there: nothing leaves the folder unless you send it (AGENTS.md, CORE-8), and the decision-rights module keeps for you anything that leaves the folder, any spending, and anything that cannot be undone (DR-2).

`AGENTS.md` is the only boot file. `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `CONVENTIONS.md` and `.github/copilot-instructions.md` exist only to point apps that look for those names to `AGENTS.md`. `CLAUDE.md` holds the single line `@AGENTS.md` and `GEMINI.md` the line `@./AGENTS.md`: the import lines of Claude Code and Gemini CLI, which make those apps load `AGENTS.md` itself. The others point to it in words; `docs/HARNESS_NOTES.md` says which apps read which file.

### 3. Read the record

- `records/`: append-only records: events, proposals (declined ones included), decisions with the question as asked and the founder's own words, the founder's signatures, declines, claims, drills.
- The witnessed git history: every close-out is a commit made by the founder and pushed to the witness, which refuses rewrites, deletions and any change to records other than additions (`docs/RECORDS.md`).
- `python scripts/fos_check.py` checks the records and their whole history against the disk, the witness and the signatures. `python scripts/fos_selftest.py` runs every integrity claim above on throwaway copies, members who break the rules included, and reports what held.
- `docs/REPRODUCIBILITY.md`, "What a reviewer checks": five checks that a copy is the release it claims to be, from its tree id to an organization's birth hash.

## What is in the folder

| Path | What |
|---|---|
| `AGENTS.md` | Boot file for any AI agent: read order and the thirteen core rules, each with its reason |
| `org/` | The organization: `config.json` (modules, roles and model slots, decision rights, checks), `TOOLS.json` (the tool registry), goal, state, letter to the next session, the founder's own rules |
| `modules/` | Twelve switchable modules: charter, decision-rights, claim-discipline, memory, record-keeping, review, tool-making, membership, norms, engagement, boundaries, design-ahead. Any combination; not levels |
| `onboarding/` | The first session, session start, the cold-recall session, close-out |
| `records/` | Append-only records |
| `schemas/` | Formats of the records |
| `scripts/` | Standard Python, no network: append records, check, check quotations against sources (CK-1), close out, birth, witness, launch a member, sync with the witness, drills, draw the view, compile the rules, export, self-test, rename, and release the seed itself for publication |
| `view/` | `VIEWS.json` (the starter view) and the drawn view |
| `docs/` | For people: records and the witness, security, what is enforced and how a rule can be, launching agent apps, hosting, design notes, roles, socialization, research uses, data flow, provenance (the crate and PROV), reproducibility, replay specification, literature, the self-test's expected results, how the seed is released, and the change log |
| `sources/`, `work/`, `archive/` | The organization's saved sources, its work, and what it superseded (nothing is deleted) |
| `addons/` | Optional add-ons for particular agent apps, which nothing in the seed needs: today, one app's enforcement add-on (`docs/ENFORCEMENT.md`) |
| `.devcontainer/` | A container definition that mounts only the organization's folder |

## Where your words go (draft)

The seed sends nothing anywhere. When you work with an agent, your conversation and the files it opens go to the model behind your agent app, under your account and that provider's terms. For sensitive work, consider an enterprise-grade deployment or a model running on your own machine; you choose the AI you bring. Details: `docs/DATA_FLOW.md`.

## How sources enter the organization

A member cites only what is saved in `sources/` (AGENTS.md, CORE-13). Sources get there in one of two ways:

1. **You save them.** Put each source into `sources/` yourself: a PDF (with a text copy beside it, same name ending in `.txt`, so that quotations can be checked), a saved web page, or a text file.
2. **The member fetches them, if you allow it.** If you switch on web fetching (or browsing) in your agent app's settings, the member saves each page it fetches into `sources/` and logs every fetch in the records (a `source_fetched` event with the address and the saved file). If your app cannot fetch, or you leave it off, the member says so and works only from what you save.

What a member remembers is never a source. A name, a date, a number or a quotation it recalls is marked **lead** until its source is saved and the words are found in it.

## Status

Seed v1.3.2, a draft for exploration. Six modules carry a Grounding section built on works read for the seed, with what each is expected to do; the other six say that they claim no theory, because none has been read for them, give the design reason each is there, and leave each as a design guess a scholar may theorize and test. Most rules' literature lines are still leads; `docs/LITERATURE.md` says what was read of each. Next to each element is what it is expected to do, offered as an expectation and not as a finding (`docs/RESEARCH_USES.md`).

## Licence

Code and machine-read files: PolyForm Noncommercial License 1.0.0 (`LICENSE`, `NOTICE`). Documentation and other text written for people: Creative Commons Attribution-NonCommercial 4.0 International (`LICENSE-docs`). What an organization grown from the seed records and makes belongs to its founder, who chooses its licence.
