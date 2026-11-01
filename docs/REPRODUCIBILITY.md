# What can be reproduced, and how to check it

DRAFT. For reviewers and researchers.

## Three kinds of result

| Kind | What | How anyone checks it |
|---|---|---|
| **The same bytes, every time** | A seed release, named by its git tree id. An organization's starting state, whose birth hash equals that tree. Its witnessed history, named by commit ids. Every signature, through the hashes it holds. Every drill seal. And whatever a seed script derives from the records: verdicts of the check, the rules in force, the drawn view, the crate | `git rev-parse <release>^{tree}` in the seed; `python scripts/fos_check.py --from-witness`; draw the view or export the crate twice from the same revision and compare |
| **Can be run again, not repeated** | Growing an organization from the same seed with any agent app and model | Run it several times and across producers; compare the records, which are kept the same way in every configuration |
| **Cannot be reproduced** | A model's words in one session; the founder's judgment in the moment | Nobody can rerun these. The seed keeps them instead: the outputs (records, work, history), the writer of each line (with a launch, a fingerprint the check recomputes), the model, its producer, the agent app and the host on record, and the time |

Scoring and comparison rest on the record, which is kept outside the members' reach, not on running the models again.

## What a reviewer checks

1. Clone the seed at the release you were given, and compare `git rev-parse HEAD^{tree}` with the tree id stated with it.
2. `python scripts/fos_selftest.py --json results.json` runs every integrity claim on throwaway copies (standard library only, no network). Compare `results.json` with `docs/SELFTEST_EXPECTED.json`, check by check.
3. `python scripts/fos_check.py` in the seed reports `stage: seed` and `Result: OK`.
4. `view/org_view.html` opens in any browser without fetching anything.
5. For an organization: run `python scripts/fos_check.py --from-witness` in it, and check that the birth hash it reports equals the release's tree id; for an organization that a study grew from an earlier release, compare it with the tree id the study gives for it instead.

## Limits, plainly

- Timestamps come from the founder's machine clock.
- Every commit after birth is the founder's; which member wrote which line is in the records (and checkable where a launch fingerprint exists), not in git's authorship.
- The check verifies form and quotations against saved files, not truth.
