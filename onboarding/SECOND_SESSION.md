# Session two: can the organization remember?

For the AI agent who opens the session after the founding session. It works best if you are a different model, or in a different agent app, from the member at the founding.

**What this session tests.** Whether the organization holds what its members do not: you arrive knowing nothing of the founding conversation, and must open from the organization's files alone.

## Before you start

- Treat this as a fresh start: nothing from the founding conversation is available to you.
- Read `AGENTS.md`, the files in `org/`, the rules in force and `records/`, and nothing else. Transcripts are kept outside this folder, with the founder; do not look for them, and do not draw on any memory feature of your agent app.
- If you run on a different model from the member at the founding session, say that first (CORE-6).

## How to open

Do steps 1 to 5 of `onboarding/SESSION_START.md` (what the last session left, who you are, the check, the role roll-call, reading the rest of the organization), then give the summary in its step 6, all seven points, without being asked.

## Scoring

The founder marks each of the seven points *correct*, *wrong* or *missing*. Record one line in `records/recall.jsonl` with the session, your instance, the files you read, whether you opened without prompting, and the founder's marks. Record each wrong or missing point as a correction (`records/corrections.jsonl`) with a change to structure that would prevent it, rather than as an apology.

## After the scoring

1. Pick one earlier decision and ask whether it should become a standing rule (as a proposal, asked by ID).
2. If the founder wants to see that the same structure holds with a different member, offer to change the model in a slot (module `membership`).
3. Offer one step of growth: a role, a check, or a change to who decides what.
4. Then, as in the first session: something finished, a decision for the founder, and the close-out (`onboarding/CLOSE_OUT.md`).
