# Releasing the seed

DRAFT. For the people who maintain the seed, not for organizations born from it.

The seed is built in its own git history. That history is not what gets published. A release is a new repository holding the files of the seed's last commit, as **one commit** by a neutral author at a fixed date. `scripts/release_export.py` makes it, scans it for identifying strings first, and prints a manifest. The script sends nothing anywhere and adds no remote. Publishing is the separate step described below.

The same seed commit, date, author and message always give the same commit id, so anyone holding the manifest can check that a copy is the release.

## 1. Make the release

0. Delete `scripts/__pycache__/` (and any `*.pyc` file) before any operation that copies the folder: Python's caches record the full path of the folder they were made in. The release itself never copies the folder.
1. In the seed, commit everything, then run `python scripts/fos_selftest.py`.
2. Run, from the seed's folder:

   ```
   python scripts/release_export.py ../release --date <YYYY-MM-DD>T00:00:00Z --terms <private list> --manifest <file outside both folders>
   ```

   - `--date` is required and must be in UTC. Use midnight UTC of the release day, not the time you happen to run it.
   - `--terms` is a list you keep **outside** the seed: your names, your organizations, your projects, places, machine names, account names. The script reads it and never copies it. A JSON list (`block`, `review`, `allow`) or a text file with one pattern per line both work.
   - `--also <word>` adds one more word; `--allow <text>` ignores an exact string that is legitimate.
   - The author defaults to "<seed name> authors <anonymous@example.invalid>". The `.invalid` domain cannot belong to anyone.
3. Read the scan.
   - **BLOCK**: nothing was committed. Fix the seed, commit, and run again with `--replace`.
   - **REVIEW**: read each item. Citations, app names and the licence lines are expected. Anything that points to you is not.
4. Keep the printed manifest (commit id, tree id, every file's SHA-256) outside the release.
5. Open the release folder and read `README.md`, `NOTICE` and `LICENSE-docs` once more. The licence holder must read "The authors (anonymized for review)".
6. Scan it once more, as published: `python scripts/release_export.py --scan ../release --terms <private list>`.

## 2. Choose the owner

A release carries no name. Its owner does: the owner's name is part of every link to the repository. The host also records which account pushed: its activity view "associates these changes with commits and authenticated users" ([GitHub docs](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/using-the-activity-view-to-see-changes-to-a-repository)).

Check the host's terms before choosing. GitHub's Terms of Service (effective April 27, 2026) say: "One person or legal entity may maintain no more than one free Account (if you choose to control a machine account as well, that's fine, but it can only be used for running a machine)." They also say "A Personal Account can be a member of any number of Organizations" ([Terms](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)).

| | A. A neutral owner | B. An existing personal account |
|---|---|---|
| Link | `github.com/<neutral name>/<repository>` | `github.com/<your name>/<repository>` |
| Forms | an organization owned by your existing account; or a separate account, only where the terms allow one | none needed |
| Who pushes, as the host records it | your account (for an organization) or the separate account | your account |
| Double-blind review | works if the repository is private and only the editors get access, or if the editors copy it | works only if the editors copy the files and reviewers never see the link |

For A, a name like the seed's own works well. The lower-case name `orgseed` was free when last checked; check again first.

## 3A. Publish under a neutral owner

1. Create the owner by hand, in a browser: an organization from your existing account, or a separate account if the terms allow it. Leave the profile empty: no real name, photo, bio, location, website or linked accounts. A member's link to an organization is private by default ("By default, your organization membership visibility is set to private", [GitHub docs](https://docs.github.com/en/account-and-profile/concepts/organization-membership)); leave it so.
2. Create an empty repository: no README, no licence, no ignore file, so that the release's commit is the only one. Make it private, with access for the editors alone, if they can take it that way; only people given access can see a private repository and its activity. Otherwise make it public. Leave the description empty or neutral, with no website link.
3. Use a credential made for this repository: a token scoped to it alone, or, for a separate account, its own SSH key.
4. Push from the release folder (never from the seed):

   ```
   git -C ../release remote add origin https://github.com/<neutral name>/<repository>.git
   git -C ../release push origin main
   ```

   The remote lives only in the release folder's settings. The seed stays untouched.
5. Check what arrived: clone the repository into a new folder. Compare its commit id with the manifest (`git rev-parse HEAD`) and scan the clone with `--scan`. The scan will list the clone's remote under REVIEW; that is expected.
6. Send the editors the link and the commit id.

## 3B. Publish under an existing account

Do steps 2 to 6 of 3A under your own account. Two things differ:

- The link names you, and so does the record of the push. The editors see both.
- A copy made with `git clone` writes the link into the copy's `.git/config`. Ask the editors to copy the files without git's folder: the repository page's "Download ZIP" gives a snapshot without the history ("Snapshots don't contain the entire repository history", [GitHub docs](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives)). You can also give them an archive yourself: `git -C ../release archive --format=zip -o <file>.zip main`.

## 4. What undoes it

- **Pushing from the seed**, or adding any remote to the seed's own folder. That publishes the development history: its times, offsets and messages.
- **Editing files on the website.** Each edit becomes a new commit under the account's name, at that time. Fix things in the seed and release again.
- **Annotated or signed tags**, and releases made on the website. An annotated tag records "the tagger name and e-mail" and a date ([git-tag](https://git-scm.com/docs/git-tag)). If you need a tag, make a lightweight one in the release folder (`git tag <name>`), which is only a name for the commit.
- **Commits with your own e-mail.** The host links a commit to whichever account owns the e-mail address in it ([GitHub docs](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/troubleshooting-commits/why-are-my-commits-linked-to-the-wrong-user)). The release's `.invalid` address links to no account.
- **Stars, forks, issues or comments from personal accounts** on the neutral repository. They show those accounts on its page.
- **Sending a copy of a folder** instead of the repository or an archive made by git.
- **Shipping an organization's records unscrubbed.** The `host` and `agent_app` fields in a pilot's or an example's records may give away a machine name or an account. A `record_correction` line does not remove them: records are append-only, and a correction is added beside the line it corrects, which stays (`docs/RECORDS.md`); so do the organization's history, its witness and an export made with `fos_export.py`, which carry every line. Two ways keep the name out. Before the first session's records are written, and so before the founding is committed, give the member's launch and its slot in `org/config.json` neutral values for `host` and `agent_app` (`python scripts/fos_launch.py <instance> --host <neutral value> --agent-app <neutral value> ...`). For records that already hold the name, publish a copy made for the purpose, in which those fields are replaced and the replacement is stated, and keep the organization itself unpublished; no seed script makes such a copy yet. Scan whatever you publish with `--scan` as well.
- The push time is visible on the repository page. It hints at a time of day.

## 5. A fix after publishing

Fix the seed, commit, and run `release_export.py` again with `--replace`. Then either push the new commit with `git push --force origin main`, or delete the repository and create it again. A force-push replaces the branch, but the host may keep the old commit reachable by its id for a while. If the old commit held something identifying, delete the repository instead.
