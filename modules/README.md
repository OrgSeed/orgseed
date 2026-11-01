# modules/

Each folder is one module: a set of rules, files and records the founder can switch on or off. Modules are independent. Any combination is valid, including none (the core alone). They are not levels and have no order.

Each module has one file, `MODULE.md`, with:
- what it is for, what it adds, what it costs, and which other modules it works with;
- its rules, each in this format, so that people and scripts can read them:

```
### ID Short title
rule: what a member does
why: one line on why the rule exists, written generally
lit: a literature lead, if any, marked [lead] until read in full for this seed
```

- a **Grounding** section, outside the rules: the works read for the module, with their pages; the design's expectation of it, marked as ours; and the outcome that would go against it. A module for which nothing was read says that it claims no theory and why, gives the design reason it is there, taken from its own purpose and rules, and says that it is a design guess a scholar may theorize and test.

A module is in force only if `org/config.json` lists it with state `on` and an `adopted_by` that points to a decision the founder signed at close-out (AGENTS.md, CORE-2 and CORE-3). Switching a module on or off is itself a proposal and a decision.

No module can switch off the record-keeping core: the witnessed history, proposals, decisions and signatures, declines, claims and drills are kept the same way in every configuration.

| Module | In one line |
|---|---|
| `charter` | The goal broken into near-term goals, with what success looks like |
| `decision-rights` | What members may decide alone, what is reserved, what is delegated, and the queue of open decisions |
| `claim-discipline` | Beyond the core rule (CORE-13): every source saved, every claim matched to a quotation, every statement labelled by status |
| `memory` | What the organization carries from session to session, and how |
| `record-keeping` | A fuller journal: an event for every kind of activity, not only those the core records |
| `review` | Checks held by roles, with the maker and the checker kept apart, and checks on the checkers |
| `tool-making` | Tools by one path for all: need, proposal, decision, built in the open, tested by another member, registered, reviewed, retired; tiers by reach |
| `membership` | Who joins, in which role, from which producer, and what happens when a model changes |
| `norms` | Norms with their reasons, dissent, and the organization's own list of failure patterns |
| `engagement` | Each session moves the goal, shows its declines, and hands a decision back |
| `boundaries` | What never leaves, which channels may receive what, and the records policy |
| `design-ahead` | General classes of failure, and the founder's choices made before any incident |
