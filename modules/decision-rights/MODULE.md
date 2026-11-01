# Module: decision-rights

**For.** Making clear what each member may decide alone, what is reserved to people, what the founder has delegated and with what limits, and which decisions are waiting.

**Adds.** Entries in `org/config.json` under `decision_rights` (`reserved_to_founder`, `delegated`). The decision queue is not a separate file: it is every proposal in `records/proposals.jsonl` with no decision yet. `scripts/fos_render.py` shows it.

**Works with.** `engagement` (each session hands one decision back), `review` (a check may be a decision right held by a role).

**Costs.** A short list to keep current. Without it, the core still reserves all structural decisions to the founder. Delegated decisions are signed by the founder at close-out like any other (AGENTS.md, CORE-3).

**How rights move over time.** When the organization is founded, the founder holds all structural choices and all signing. Later the founder may give rights to roles, human or AI, in grants that are recorded and limited (DR-3), widen them as trust grows, or take them back, each time by a decision. The close-out shows the founder each decision made under a grant, and for now such a decision counts only once the founder signs it. This version has no grant under which decisions would count without a signature each (`docs/DESIGN_NOTES.md`, open questions).

## Rules

### DR-1 Act by default inside the goal and the rules
rule: Do the work the goal needs without asking, as long as it is inside the rules in force and outside the reserved list. Leave a record of what you did.
why: asking permission for every step wastes the founder's attention and stalls work while they are away; the record keeps acting-by-default accountable.

### DR-2 Keep the reserved list short and explicit
rule: The founder decides the reserved list. By default it holds structure, decision rights, anything leaving the folder, spending, signing, and anything that cannot be undone. Never act on a reserved item; queue it.
why: a short explicit list lets members act freely everywhere else; a vague one makes them either timid or reckless.

### DR-3 Delegation names its limits and its holder
rule: A delegated right names the role that holds it, what it covers, its limits, and the decision that granted it. A role instance may use it only within those limits, and records the right used.
why: delegation without limits becomes abdication; delegation recorded by right can be audited and taken back.
lit: Davis, Schoorman & Donaldson 1997, on stewardship versus agency views of those entrusted with decisions [lead]

### DR-4 Record who framed the question
rule: In each decision record, name who framed the question and the options. When you frame options for the founder, include the option you did not prefer and say which you prefer and why.
why: whoever drafts the options shapes the outcome; naming the framer keeps that influence visible.

### DR-5 Route decisions to the founder's attention, not into the stream
rule: At the end of each session, list every open decision as a numbered item, most consequential at the top, each answerable in a sentence. Do not bury decisions in long text.
why: a decision buried in long text is easily missed; a short numbered list keeps the founder's attention on what only they can decide [opinion].

### DR-6 Delegated defaults stand only as adopted
rule: If the founder asks members to choose defaults for a set of open items, choose them, improve each one critically, and present them as one decision. They stand once the founder adopts them; the review is the record.
why: lets the founder delegate a batch of small choices without losing the right to see and reject them.

### DR-7 Supervision is one way to coordinate, not the only one
rule: When proposing how a piece of work is coordinated, consider shared standards, a fixed procedure, a check held by a role, and direct supervision, and say why you propose the one you do.
why: direct supervision is one of several ways to coordinate work, and another may cost less for the task at hand [opinion].
lit: Mintzberg 1980, Management Science, doi 10.1287/mnsc.26.3.322, on coordinating mechanisms [lead]

### DR-8 Hand back with what the founder needs to decide
rule: When a proposal goes to the founder, fill in its background in plain words (the terms, what each option means, what is uncertain), what happens if nobody decides (if_undecided), and what waiting costs (cost_of_waiting). The close-out shows them with the decision.
why: a founder can only own a decision they understand; a decision signed without that is the member's decision with the founder's name on it.

### DR-9 Adopt on trial what you cannot judge
rule: A founder who cannot weigh a proposed change on its merits (because it is technical, or outside what they know) may adopt it for a set number of sessions, naming a date to look at it again. On that date they keep it, alter it or reverse it, and that review is itself a decision.
why: a founder can answer for a change they cannot judge when its effects are visible, its time is limited and the way back is written down; without that, technical proposals tend to be signed, or refused, without being understood.

## Grounding

**On the literature.** For Sah and Stiglitz, part of a decision system's architecture is "who makes which decisions" (Sah & Stiglitz 1984, NBER working paper 1334, p. 1; read), and when one unit alone screens, its no ends the matter (p. 2). Simon makes a related point about design: "sequence and the division of labor between generators and tests can affect not only the efficiency with which resources for designing are used but also the nature of the final design as well" (Simon 1996, p. 130; read). He also reminds the designers of organizations that members "are not passive instruments, but are themselves designers who are seeking to use the system to further their own goals" (p. 153).

**What this design expects.** [ours] The aim is decisions that remain the founder's while members get on with the work. So the core keeps structure and signatures for the founder, DR-1 lets members act without asking inside the rules, and DR-3 lets the founder grant rights in writing, with limits. When a single member routes a decision, the outcome may carry what its producer gave that member; routes that pool several members, or take a majority, may even this out. No ready-made role for such routing ships in this version (`docs/RESEARCH_USES.md`). How rights move is the founder's choice: all of them are the founder's at founding, more can be granted as trust grows, and for now a decision taken under a grant still needs the founder's signature to count.

**The other side.** When everything waits for one person, that person becomes the queue and the only screen; `scripts/fos_render.py` shows where decisions wait. A grant with no limits gives the organization away (the reason behind DR-3). Simon wrote of human members as designers; carrying that over to AI members is our extension, not his.
