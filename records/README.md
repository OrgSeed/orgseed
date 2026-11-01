# records/

The organization's records. Every `.jsonl` file here is append-only (AGENTS.md, CORE-4): one JSON object per line, never edited, never rewritten, never deleted, not even on request. A correction or a change of status is a new line that points to the earlier one.

**How to write records:** only with `python scripts/fos_log.py <kind> --json-file <file>` (or `--json -` for standard input, or `key=value` pairs for one short record). A file may hold several records (a JSON list, or one object per line); `batch` mixes kinds, each record naming its kind in `"record"`. They are checked together and written together, or not at all. Never touch a records file with an agent app's file tools, not even to add a line: such tools often write the whole file again. A member who cannot run Python writes the records into a file in `work/` and asks the founder to add them.

Every record carries its own `seq` (its number within its file), `ts` (UTC), `session`, `identity` (who wrote it: instance, model, producer, agent app, host) and `captured_by`. Formats: `schemas/`.

| File | Holds | Written by | In |
|---|---|---|---|
| `events.jsonl` | What happens, in order: sessions, proposals, decisions, changes, work, declines, corrections of records, roles that ran | members; the seed's scripts for `born`, `close_out`, `integrity_repair` | core |
| `proposals.jsonl` | Proposed changes, including declined and open ones | members, founder | core |
| `decisions.jsonl` | The question as asked (with proposal IDs) and the decider's reply in their own words | members, founder | core |
| `signatures.jsonl` | The founder's signature on each decision, or refusal, given at close-out | `scripts/fos_close.py` only | core |
| `declines.jsonl` | What was stopped or turned back, and by which rule or check | members, founder | core |
| `claims.jsonl` | Claims matched to their sources, or marked lead | members | core (CORE-13); fuller with claim-discipline |
| `drills.jsonl` | Drills the founder plants (sealed) and later reveals | `scripts/fos_drill.py` only | core |
| `corrections.jsonl` | What was wrong in the work, and the structural fix | members, founder | memory module |
| `commitments.jsonl` | Promised future work, with owner and trigger | members, founder | memory module |
| `recall.jsonl` | Cold-recall checks at session start | members, founder | memory module |
| `dissent.jsonl` | A member says a rule is wrong for a case | members | norms module |
| `reviews.jsonl` | Runs of checks held by roles | members | review module |
| `needs.jsonl` | Needs noticed, and how each was met | members, founder | tool-making module |
| `pins.jsonl` | What the founder chose to come back to, in their words, and when | members, founder | memory module |
| `deviations.jsonl` | Changes made after a design was frozen, with their kind (forced, correction, chosen) | members, founder | design-ahead module; every study |
| `successes.jsonl` | What went well, where the record shows it, and what to keep doing | members, founder | norms module |

A file whose module is off stays in place, empty or not. Files are never removed: a file no longer used is noted as unused in `org/STATE.md`.

The founder closes each session with `python scripts/fos_close.py`, which checks the records, asks the founder to sign each decision, commits, and pushes to the witness, a copy of the history kept outside the folder that refuses any change to records other than additions (`docs/RECORDS.md`).
