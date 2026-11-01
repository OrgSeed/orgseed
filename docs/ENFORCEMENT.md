# Enforcement: what the seed enforces, and how a rule can be

DRAFT. For people and agents.

Some rules a member only reads; others a program holds to. An organization should know which of its rules are which, and its record should show it.

## What the seed holds to by itself

The record-keeping core. The witness turns back rewrites and deletions in the history; `fos_log` alone adds records, one checked line at a time; and the founder's close-out checks the records, puts back what was deleted or rewritten, and asks for each signature (`docs/RECORDS.md`, `docs/SECURITY.md`). No member can turn these off.

## What it leaves to persuasion

Everything else: the founder's rules (`org/OUR_RULES.md`), norms, the modules' rules, and the core rules outside the record-keeping core. Members read them, with their reasons. The check can report some breaches after the fact (CK-1 finds a quotation missing from its saved source, for example), but it only reports; it never stops a write.

## Enforcing a rule with an enforcement add-on *[our term]*

An enforcement add-on is code that runs inside the agent app and turns back, before it happens, a write that would break a rule the founder names. It is always one app's code, since each app has its own way of showing code a tool call before the call runs. Under `modules/tool-making/MODULE.md` it counts as a tool: a capability built into the agent app that the organization comes to depend on. Its tier follows from the module's table. With no log, it reads the folder and decides which writes in it go ahead: tier 2 [ours: the table has no row for turning writes back, and tier 2 is the nearest]. With a log, it writes a file outside the folder, which alters the machine beyond the folder: tier 4. The checks it runs are programs of their own, each registered as a tool at its own tier. Like any tool it is proposed, decided, tested and registered. One app's add-on is in `addons/opencode/`, as an example of the form; none is required.

Besides a tool's usual fields (`id`, `path`, `tier`, `status`, `adopted_by`), its row in `org/TOOLS.json` carries:

| Field | Meaning |
|---|---|
| `kind` | `"enforcement add-on"` |
| `agent_app`, `agent_app_version` | Which app it runs in, and the version it was tested with |
| `enforces` | The IDs of the rules whose breaking writes it turns back |
| `covers` | The channels it can see: the app's file tools, and whether the shell too (for example `"file tools; shell: no"`) |
| `refusal` | Its message: `"bare"`, or `"reasoned"` (the rule, why it exists, and how to propose a change) |
| `code_sha256` | The SHA-256 of its code, which the check recomputes from `path` |

A row might read:

```
{"id": "refuse-writes", "kind": "enforcement add-on", "path": "addons/<app>/<file>", "tier": 2,
 "status": "active", "agent_app": "<app>", "agent_app_version": "<version>", "enforces": ["OUR-1"],
 "covers": "file tools; shell: no", "refusal": "reasoned",
 "code_sha256": "<sha256>", "builder": {"instance": "<instance>"}, "tester": {"instance": "<other instance>"},
 "adopted_by": "D-...."}
```

Each time the add-on turns a write back, its message asks the member to record a decline as usual (`records/declines.jsonl`), with the add-on's tool ID in its `enforced_by` field; the request is the same whatever else the message says. The check warns **UNDECLARED ENFORCEMENT** when a decline names an add-on with no row of this kind in testing, active, paused or retired (a row in testing covers the founder's own trial of the add-on), and also warns when such a row leaves out what it covers or the hash of its code. The check sees only the declines members recorded. Every refusal is counted in a log that the add-on writes beyond the folder, out of the members' reach; compare the two before relying on the declines. An organization with no add-on has none of its own rules enforced, and its records show no decline from one.

## What a refusal should say [ours]

The rule, why it exists, and that the rule itself can be changed through a proposal (CORE-2). For example: "Refused: this write breaks OUR-1, which exists because .... If the rule does not fit this case, propose a change to it." A message that says only "refused" applies the same rule more harshly.

## Limits

- An add-on sees only what passes through it. A shell is another way to write: an add-on watching the app's file tools does not see a shell command that writes the same file. Say in the row what it covers, and record whether the app's shell was on.
- The check only reports. A write that went round the add-on shows up later, in the check or in the records, if it shows up at all.
- An add-on is tied to one app, often to one version of it; another app needs its own.
- None of the seed's scripts depends on an add-on.

## Grounding

**On the literature.** Adler and Borys count enforcement as part of formalization's degree: "the extent of formalized rules governing work behavior and the extent to which they are enforced" (Adler & Borys 1996, p. 77; read). Degree and type vary separately, so that "a procedure designed with an enabling intent and embodying enabling features can be implemented coercively" (p. 76). Of coercive design they say that "any deviation from standard procedure is seen as suspect", and that, as a result, "covert and inefficient 'work-arounds' abound" (p. 71). Of enabling design: "Breakdowns and repairs signal to the organization problems with the formal procedures and become opportunities for improvement" (p. 71). Where organization and employees want different things, "the enabling type of formalization is unavailable" (p. 80). Ouchi expects control that leans on monitoring, evaluating and correcting in an explicit way to draw an "unenthusiastic, purely compliant response" (Ouchi 1979, p. 841; read).

**What this design expects.** [ours] When reading a claim standard is not enough, a tool can turn back the write that breaks it, and its message can give the rule, its reason, and the way to propose a change (CORE-2). Members may then differ in claim discipline less than under the written rule. Yet where the rule cuts across what a member's producer built into it, the answer may be bare compliance, or a way round through a channel the tool cannot see, and differences between members could widen. Nothing we have read says this; it is a reading for a study to test. The refusal's wording is where the enabling type comes in: refusing without a reason is the same rule applied coercively (p. 76).

**The other side.** A tool sees only the channels it sits in, and a shell is one more channel. A refusal without a reason leaves the member nothing to act on [ours]; it is enabling procedures that make "the rationale of the rules" clear (p. 72). Whether an AI member does anything with a reason it is given remains open.
