# Replay: specification (not yet built)

DRAFT. The replay shows an organization growing, commit by commit, from its own history. It needs no agent, no account and no network: one HTML file a reader opens.

## Inputs

- A clone of the organization's witness (`<organization>-witness/history.git`), so that only witnessed history is replayed.
- A **pinned tag** (for example `replay-end`) marking the last commit included.
- Nothing else. Transcripts, chat logs and files outside the repository are never inputs.

## Build

1. List commits from the root to the tag in order (`git rev-list --reverse <tag>`).
2. For each commit, read the organization's files **as they were at that commit**, straight from git (`git show <commit>:<path>`), not from the working folder.
3. Run the same parsing as `scripts/fos_render.py` on that snapshot: modules, roles and slots, decision rights, open proposals, decisions, rules in force with reasons, declines, tools, state, letter.
4. Parse the commit itself: subject `[TYPE]`, trailers (`docs/RECORDS.md`, Commit messages), author, time, files changed; and the signatures added in it, with what the founder was shown.
5. Store, per commit, the snapshot (or its difference from the previous one) and the commit data, as JSON embedded in the HTML.
6. Write one self-contained `replay.html`. A small inline script drives the scrubber; a content-security policy forbids any network access. Target size under 5 MB; if larger, store differences only.
7. Put the tag name and its commit hash in the footer. Building twice from the same tag must give the same file: no build time in the output, stable ordering everywhere.

## What the reader sees

- **A timeline** scrubbed by session and by commit, with play and step controls.
- **The organization as of the selected commit**: the panels of the view (goal and movement, modules, members and origins, decision rights and queue, rules and declines, tools, memory).
- **This change**: the commit's type, files touched, and trailers, including the decision that authorized it, who decided, under which right, and who framed the question.
- **Filters** by commit type (decisions, structure, declines, corrections, tools, work).
- **A members strip**: which model held which role instance over time, with each swap marked.
- **Totals so far**, counted from the records: the founder's decisions; rules the founder wrote; times the founder overrode a member or a check; things declined or redirected; corrections that led to a structural change; tools adopted; recall scores.

## Honesty in the replay

- Drills are marked DRILL everywhere they appear, with the seal and, once revealed, the description.
- Each decision shows whether the founder signed it, with any note, and what the founder was shown.
- The footer states that every commit shown came from the witness.
- Each event may be marked *planned* (scheduled in advance to exercise a feature) or *arose* (happened in the course of work), from the event's `origin` field. Declines are never planned.
- Declined and open proposals appear on the timeline as proposals; they never appear as part of the organization.
- Anything structural that lacks an authorizing decision is shown as *not part of the organization*, never hidden.
- If history was ever rewritten, the replay shows where and links to the record of why (`docs/RECORDS.md`, Commit messages).

## Checks before a replay is shared

- `scripts/fos_check.py` passes at the tag.
- The full history, not only the tag, has been scanned for material that must not leave (the founder's records policy).
- The replay rebuilds identically from the tag.
