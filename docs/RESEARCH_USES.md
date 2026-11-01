# Research uses: the seed as an instrument

DRAFT. For researchers. Members do not need to read this file, and a study should keep its own materials (tasks, answer keys, scoring rules) outside the organization's folder, so that members are not shaped by how they will be scored.

The seed can be used in two ways: to do research with (an organization working toward a founder's goal), and to do research on human–AI organizing itself. This file is about the second.

## What the seed lets a study vary

| What | How | Where |
|---|---|---|
| Structure, piece by piece | Switch any module on or off, in any combination; add or remove single rules, checks or roles | `org/config.json` (`modules`, `checks`, `roles`) |
| Who holds a role | Put a different model in a slot; give a role several instances on models from different producers | `roles[].instances[].slot` |
| Whether rules carry reasons | `settings.rule_reasons`: `shown` or `hidden` (module and founder rules; the core rules in AGENTS.md always show reasons, so a study of reasons needs its own variant of AGENTS.md) | `org/config.json`, `scripts/fos_rules.py` |
| Whether a fuller journal is kept | The `record-keeping` module, on or off, while the record-keeping core stays the same | `modules/record-keeping/` |
| Who checks whom | Maker and checker roles, and whether the checker comes from a different producer | `checks[]` |
| Whether the core claim rule applies at all | A research configuration made at birth (`fos_init.py <folder> --study <file>`), with CORE-13 and its checks switched off | `org/STUDY.json` |

## A research configuration: when "off" has to mean off

In a founder's own organization the core is always on, and the core includes a claim rule (CORE-13) with mechanical checks. A study comparing structure with no structure needs that rule truly absent in its baseline arm, not merely unused. `python scripts/fos_init.py <folder> --study <study.json>` makes such an organization, and nothing else can:

- the study file names what is switched off (today only `CORE-13`; nothing in the record-keeping core can be), the study's name, and whether it is exploratory or confirmatory;
- right after the birth commit, a third commit (`[STUDY] ...`) applies a change the seed fixes in advance: the rule's text leaves `AGENTS.md`, and the two lines of `onboarding/START.md` that ask for claims lines become neutral. `org/STUDY.json` records the change, with each changed file's SHA-256, and a `study_configured` event records the act;
- the check confirms that `org/STUDY.json` is the one made at birth before it switches any check off; a copy placed in an ordinary organization switches nothing off and fails the check. The check's summary, and the view's frame, say "research configuration" in every session;
- the birth hash is still the seed's tree, so the configuration is one commit away from the seed, and anyone can see exactly what differs.

The founder-facing default is unchanged: the option appears only here and in `scripts/fos_init.py`, never in the boot file or the onboarding.

## What it records in every configuration

The record-keeping core, the same whatever modules are on: the witnessed git history (written only by the founder's close-out, and refused by the witness if rewritten), proposals, decisions with the question as asked and the reply word for word, the founder's signatures with what the founder was shown, declines, claims, drills, and session events (`docs/RECORDS.md`). Every record says who wrote it (`captured_by`) and on which model, producer, agent app and host (`identity`), so members' own accounts can be kept apart from independent captures.

This version has no script that drafts, from the folder, the list of facts a report on a study with language models should give. Such a list is filled in by hand from `org/config.json`, the launches on record and `seed.json`, writing `unknown` where the folder has no answer. One item cannot be recovered afterwards, the agent app's own instructions, so a launch can keep their hashes (`python scripts/fos_launch.py <instance> ... --app-instructions <files>`).

A comparison between conditions is best made on a record kept identically under every condition and beyond the members' reach, the witnessed history first; the members' own records are then evidence of how the organization worked, with their faithfulness measured against it [opinion].

## Each element as a design proposition (exploratory; not a theory)

The elements are written as design propositions in Romme's form: "In situation S, to achieve consequence C, do A" (Romme 2003, *Organization Science*, p. 564; read). Here the situation is the same for every element: an organization whose AI members were shaped by a producer before they joined it, in ways its founder cannot alter. The effect we expect of each element is ours. The works cited studied people; none of them looked at members made by an outside producer, and none says how such members would differ in conduct. Ouchi comes closest. He treats a mixed membership as a matter that explicit rules and monitoring can manage: the bureaucratic form "can typically take in a heterogeneous assortment of people and effectively control them" (Ouchi 1979, p. 841; read). Whether that still holds when members' formation lies wholly outside the organization is open, and a study of this seed can ask it.

Two activities stay apart. Design is what happens when an organization is grown from the seed; testing is turning one element on or off and reading what the record shows. Romme is plain that "A full integration of the design and science modes is thus not feasible" (Romme 2003, p. 567).

## Expected directions, element by element

The table only says where each element's expectation is written, together with the opposite outcome. All of them are ours and hedged; none is a finding.

| Element | In the seed | Expectation and the opposite outcome |
|---|---|---|
| One written claim standard for all members | CORE-13; module `claim-discipline` | `modules/claim-discipline/MODULE.md`, Grounding |
| That standard, enforced by a tool | an enforcement add-on in the agent app, registered as a tool | `docs/ENFORCEMENT.md`, Grounding |
| A check held in a role, by an instance on the maker's producer or on another | module `review` (REV-1, REV-2) | `modules/review/MODULE.md`, Grounding |
| Where decisions go, and who holds which rights | the core; module `decision-rights` | `modules/decision-rights/MODULE.md`, Grounding |
| Which producers fill which roles | module `membership` | `modules/membership/MODULE.md`, Grounding |
| A rule that comes with its reason | module `norms`; `settings.rule_reasons` | `modules/norms/MODULE.md`, Grounding |
| The record no member can edit | the record-keeping core; module `record-keeping` | `modules/record-keeping/MODULE.md`, Grounding (nothing expected of conduct) |
| One member through whom a decision is routed (a liaison or lead) | not in this version: no ready role card, though a founder can define any role (`docs/ROLES.md`) | `modules/decision-rights/MODULE.md`, Grounding |

The remaining six modules (`boundaries`, `charter`, `design-ahead`, `engagement`, `memory`, `tool-making`) claim no theory, because none has been read for them. Each one's Grounding section gives the design reason it is there, taken from the module itself, and calls it a design guess that a study may theorize and test, for example by switching the module on or off and reading what the record shows.

Things a study would want to keep apart:
- **Claims versus ideas.** Structure may be expected to reduce variation in claim discipline (unsourced claims, dropped qualifiers) without reducing variation in framing and ideas. A fall in the variety of ideas would be a cost, not a success.
- **Rival readings.** Members may interpret one set of rules in different ways, in which case adding rules could widen differences instead of narrowing them [opinion; compare work on the appropriation of technology structures, DeSanctis & Poole 1994 and Orlikowski 1992, both Organization Science, lead].
- **Placement of accountability.** Where accountability sits in a multi-agent design, and whether that matters differently across model families, is a question one recent study takes up (arXiv:2607.25446 [lead]).
- **Persuasion versus enforcement.** A rule members read is different from a rule a program enforces. In this seed the record-keeping core is enforced outside the members' reach (the witness, the founder's close-out); the founder's and the modules' rules only persuade, except where an enforcement add-on in the agent app blocks the writes that would break one (`docs/ENFORCEMENT.md`). A study can shift a rule from one kind to the other and compare. It should report, for each organization, the add-on's registry row with its `covers` field, or that there was no add-on, and count refusals from the add-on's own log rather than from the declines members recorded, which can be incomplete. Every refusal asks for a decline in the same words, whatever else its message says, so that the record differs between conditions only where the message does.
- **Self-report.** Member-written records may be more or less complete depending on the model. Measure their completeness against an independent capture (the witnessed history, a runner or observer outside the folder, the founder's transcripts) before comparing models on them.

## What a study adds outside the folder

Tasks and their source material; answer keys, sealed until scoring; a scripted human where the founder's influence should be held constant; an observer or runner that keeps the full exchange; codebooks and a scoring specification; and a plan fixed before the main runs. None of these ship in the seed. A study can put out its scripted founder (the full script, unchanged) together with the organizations that came of it, as data next to the seed and never within its tree. Anyone can then run the script again with a member they pick and set the records side by side; the members' words will differ, and are not what is compared.

## Other questions the records can speak to

- Does the organization remember what its members cannot? (cold-recall scores, `records/recall.jsonl`)
- Do corrections end in structure, and does structure chosen in advance prevent the failures it was chosen for? (`records/corrections.jsonl` with failure classes; `org/DESIGN_AHEAD.md`)
- Do founders who see progress and declines stay engaged? (engagement counts from the records; behaviour only)
- Do roles fade when nobody exercises them? (dormant-role flags)
- Who frames decisions, and does real authority drift toward whoever drafts the options? (`framed_by` in decisions)
- Once invited, do members suggest changes, and on what basis? (`records/proposals.jsonl`, its `grounding` field checked against `sources/`)
