# Socialization: how the organization brings its members in

DRAFT. For people. Socialization here means the ways an organization brings its members to know and act on its goals, norms and ways of working. With AI members it happens in several places, each with its own reach and limits.

## Where it happens

| Where | What carries over | Who controls it | Limits |
|---|---|---|---|
| **Within a session** | Everything said and read in the session | The members present | Ends with the session. A long session may lose early material as the model's context fills. |
| **Across sessions, through the folder** | Whatever the next member reads at the start: `AGENTS.md`, the rules in force, `org/STATE.md`, the letter to the next session, the records | The organization (the founder and members, by decision) | Only what was written down, and only as well as the next member reads it. Long boot files get skimmed. |
| **Across members and models** | The same folder brings in whichever model holds a role | The organization | How evenly different models take up the same files is an open, testable question (`docs/RESEARCH_USES.md`). |
| **At the producer** | Training and published policies, changed by release | The producer, not the organization | The organization cannot reach it. Where the producer's norms and the organization's differ, the producer's may prevail [opinion]. Watch releases (module `membership`). |
| **In the founder** | The founder remembers, learns and changes | The founder | The founder is brought in too: by the interview, the rules that bind them, the hand-backs and the signing. This is by design and stated openly. |
| **In the agent app** | Some agent apps keep their own memory or settings | The app and its provider | Outside the organization's records and control. The seed does not rely on it (CORE-10), and it can carry content from one organization to another. |

## The seed's choices, dimension by dimension

Van Maanen and Schein describe six tactical dimensions of organizational socialization: collective or individual, formal or informal, sequential or random steps, fixed or variable, serial or disjunctive, and investiture or divestiture. They add that the tactics are not mutually exclusive (Van Maanen & Schein, *Toward a theory of organizational socialization*, MIT working paper 960-77, 1977, pp. 35–37; those pages read, the rest of the paper and its published version not). The table below is **our** reading of where the seed stands on each, and why. None of it is their claim.

| Dimension | The seed's choice [ours] | Where |
|---|---|---|
| Collective or individual | Individual by default (one member per session); collective when a role has several instances reading the same records | `org/config.json` roles; `onboarding/SESSION_START.md` |
| Formal or informal | Formal first (the rules in force, with their reasons), then the record of actual practice: recent decisions, declines and corrections, read at every start, after what the last session left | `onboarding/SESSION_START.md` steps 1 and 5 |
| Sequential or random | Sequential: the same read order and the same opening steps every session, whichever model arrives | `AGENTS.md`, `onboarding/` |
| Fixed or variable | Fixed gates with stated criteria (a new instance passes probation before holding a check; a decision counts only once signed), not open-ended waiting | modules `membership`, `review`; `scripts/fos_close.py` |
| Serial or disjunctive | Serial through text: the outgoing member writes the letter to the next session and role cards carry what earlier holders learned. A model swap is partly disjunctive, so it is announced and recorded | `org/LETTER_TO_NEXT_SESSION.md`; modules `memory`, `membership` |
| Investiture or divestiture | Investiture: the member keeps what its producer gave it, and the organization adds its own rules and reasons on top; nothing tries to strip the member's formation away | `AGENTS.md`, module `norms` |

Some mechanisms in that literature work through a person's feelings or self-image over time. We assume those do not carry over to AI members as mechanisms, and keep only their structural part, such as an explicit gate [opinion].

## How the seed socializes

- **Re-performed every session.** Each session begins by reading the organization's files and opening with what the organization remembers. Bringing a member in is not a one-time event; it is redone each time a member arrives, from the same files.
- **Serial.** The outgoing member writes to the incoming one, so the role passes on what it learned (module `memory`, MEM-2).
- **Tiered.** Some files load every session, some only when a step points to them, and some never (transcripts, kept by the founder outside the folder). What loads every session is kept short.
- **With reasons.** Rules carry their reasons, so a member can act on a rule's purpose where its words are silent (module `norms`, NRM-1).
- **By interview, for the founder.** The first session starts from the founder's own strengths and judgments. In one field experiment, newcomers whose first day began from their own strengths stayed longer, and their customers were more satisfied, six months later than newcomers welcomed with pride in the organization or with skills training alone (Cable, Gino & Staats 2013; abstract and study design read, not the full paper).

## What remains open

- **How complete socialization through files can be.** In Ouchi's account, clans "rely upon a relatively complete socialization process which effectively eliminates goal incongruence between individuals" (Ouchi 1979, p. 833; read). Members formed elsewhere, who forget between sessions, may never get that far [opinion]. Structure that does not depend on members having taken anything in (checks held by roles, decision rights, the witness, the founder's signature) may carry what socialization cannot.
- **Whether producers have reasons to help** an organization bring their models in. The seed assumes not, and keeps all organization-specific learning in the folder.
- **Whether roles fade.** Roles that are not reloaded or exercised may stop shaping what members do, without anyone deciding so [opinion]. The role roll-call flags roles that have not run.
