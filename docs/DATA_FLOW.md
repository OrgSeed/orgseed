# Where your words go (draft data-flow note)

DRAFT, not legal advice. For founders, before the founding session.

## What stays on your machine

- The organization's folder: its files, records, sources and history. The seed sends nothing anywhere. Its scripts make no network connections, and its view loads nothing from outside.
- By default, the organization works only with public or synthetic data. Other kinds of data come in only by your decision, recorded like any other (in the records policy, if the `boundaries` module is on).
- The witness: a copy of the history in a folder next to the organization's, which refuses rewrites and deletions, and keeps your sealed drill descriptions and, if you keep them, your agent app's transcripts.

## What goes to an AI provider

- Working with an AI agent here sends your conversation, and the contents of any file the agent opens, to the model your agent app uses. That happens under your account with the app, on its provider's terms.
- Different providers and plans keep inputs for different periods and may or may not use them to improve their services. Read the terms for the plan you use, and keep a dated copy (module `boundaries`, BND-3).
- **Enterprise-grade deployments** are worth considering for sensitive work: in some, the model is served by a host other than its producer, under a contract that limits how inputs are kept and used. This is general advice, not a recommendation of any service. You choose the AI you bring.
- **Local models**, run on your own machine with open weights, keep the conversation on your machine. They may be less capable; the seed works with any agent app that can read and write files.

## What goes elsewhere, only if you decide

- A tool the organization builds that uses the network (tier 3 and up, `modules/tool-making/MODULE.md`) sends what its approving decision allows, to the web addresses listed for it, under that service's terms.
- A copy of the history on another machine or a hosting service, if you choose one.
- Anything you send, publish or share yourself.

## What nobody else sees

The seed has no account, server or telemetry. Nobody associated with the seed sees your organization unless you send it to them.

## Open items for this note

- The seed offers no hosted version. `docs/HOSTING.md` is a recipe for an institution that wants to run instances; any such host needs its own data-flow note.
- Agent apps differ in what they log locally (transcripts, caches). Check where yours keeps them, and keep them outside the organization's folder (`docs/RECORDS.md`, Transcripts; `docs/HARNESS_NOTES.md`).
