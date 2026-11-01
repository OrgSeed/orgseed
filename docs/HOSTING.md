# Hosting organizations for others: a recipe

DRAFT. This page is a recipe for an institution that wants to run organizations grown from this seed on its own computers, for founders who would rather not install anything. The seed itself offers no hosted instance and runs none. A host that follows this recipe is responsible for its own terms, privacy notice and model contracts.

## The rule behind every step

**The host supplies infrastructure, never organization** (a rule we adopt). A host may supply a login, storage, computing, a chat window and a connection to a model. Everything that makes up an organization stays in the organization's folder: its charter, roles, records, rules, view and history. Then an organization can always leave the host, and anyone can check that it started as the seed does.

## Steps

1. **Build each organization from a tagged release, never by hand.** Run `python scripts/fos_init.py <folder>` from a copy of the seed at the release tag. It makes no model call and uses no network, so every organization born from the same release starts with the same files. Show the founder the birth hash it records, and how to check it: `git rev-parse <tag>^{tree}` in the public seed repository gives the same value. Per-person facts (the account, the login, any key) stay in the host's own storage, outside the organization's folder.
2. **Give each organization its own isolated environment:** its own operating-system user, and a container or virtual machine that sees only its folder, with no access to other organizations, to the host's keys, or to the host's other services, and no network except the model connection.
3. **Keep the witness outside that environment.** Create it with `fos_init` (or `python scripts/fos_witness.py setup <folder>`) in a place the organization's environment cannot write to, and let pushes reach it only through git, so its own check runs on every push. Transcripts, if the host keeps them at all, belong beside it, never inside the organization.
4. **Hold model keys in a gateway**, never in the organization's environment: the agent sees a stand-in address and a per-organization budget, not a key. A founder who brings their own key enters it into the gateway, not into the folder.
5. **Let the founder close each session personally.** The close-out (`scripts/fos_close.py`) is the founder's act: give the founder a terminal, or a page that runs it for the founder at the founder's request, showing exactly what it shows, and never let an agent start it.
6. **Never edit a founder's folder by hand.** Anything the host needs becomes a change to the seed, released and tagged. A new release reaches an existing organization only as a proposal its founder accepts or declines.
7. **Record any operator access inside the organization.** If someone on the host's side must open an organization (the founder asks for help, a security incident, a legal obligation), add an `operator_access` event to that organization's own records (`captured_by: host`), saying who, when and why, and tell the founder.
8. **Export and deletion on request.** `python scripts/fos_export.py` gives the founder one file with the whole history and a note of what it leaves behind. Deletion removes the folder, the witness and backups, by a date the host states in advance.
9. **Set a ceiling for tools, and say it.** On a shared machine, decide which tool tiers the host can contain (for example: no tier 4), and state the ceiling where founders see it. Tools approved on another machine arrive paused after an import and are approved again.
10. **Say plainly what is stored and who can see it.** Before the first session, show the founder what the host keeps, who can open it and when, which model provider sees what, and how to export or delete. Do not promise that nobody can see anything a person on the host's side could see.

## What a host should be able to show

- The birth hash of every organization, and the release it came from.
- That each organization's witness accepts only additions to records, and that each organization's close-outs were run by its founder.
- An access log, kept in each organization's own records.
- That an organization exported from the host opens and passes `python scripts/fos_check.py` on a machine with no host present.
