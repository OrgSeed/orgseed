"""Bring this folder back in line with its witness, without losing anything. The founder runs it.

Usage:
  python scripts/fos_sync.py           show how this folder stands to its witness, and offer to sync
  python scripts/fos_sync.py --check   show it only; change nothing (anyone may run this)

An organization has one working copy: this folder. Its witness holds the history that the founder's
close-outs pushed. This folder can fall out of line with it in three ways:
  - behind: another copy of the organization was closed out. Copies are not supported (one working
    copy per organization; docs/RECORDS.md), but they happen;
  - split: this folder has commits the witness refused or never got (a member committed, or a push
    failed after another copy had pushed);
  - replaced: this folder's history shares no commit with the witness's.
A sync returns this folder to the witness's last close-out and carries this folder's own work forward:
  - records added here since the last common close-out are kept, after the witness's, when they
    cannot collide with records the witness gained since; otherwise they are set aside, never merged;
  - other files changed here are kept, unless the witness changed the same file since; then the
    witness's version stays, and this folder's version is set aside;
  - lines edited or removed in records come back from the witness (records only grow).
Before anything changes, everything in this folder that differs from the witness is copied to
<witness>/set_aside/<UTC time>/before_sync/, with a manifest. The sync is recorded as a 'sync' event
naming what was kept and what was set aside. Nothing is discarded silently.

Like the close-out, it runs only in a terminal (--test-answers y,n is for the seed's self-test).
Standard library only; no network beyond the witness folder.
"""
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402
import fos_witness as W  # noqa: E402

TEST = {"answers": None}
TAKE_FROM_WITNESS = (L.BIRTH_FILE, "view/org_view.html", "org/RULES_IN_FORCE.md")


def say(text=""):
    print(text)


def ask(prompt):
    if TEST["answers"] is not None:
        a = TEST["answers"].pop(0) if TEST["answers"] else "n"
        print("%s %s   [test answer]" % (prompt, a))
        return a.strip().lower()
    while True:
        try:
            a = input(prompt + " ").strip().lower()
        except EOFError:
            return "n"
        if a in ("y", "yes", "n", "no"):
            return a[0]
        print("  Please answer y or n.")


def show(rev, rel):
    return L.head_bytes(rel, rev) if rev else None


def names(code_out):
    code, out = code_out
    return {x.strip() for x in out.splitlines() if x.strip()} if code == 0 else set()


def mine_since(base, tip):
    """Paths where this folder (working tree, untracked files included) differs from `base`, or from the
    witness's tip when there is no common commit."""
    paths = names(L.git("diff", "--name-only", "--no-renames", base or tip))
    paths |= names(L.git("ls-files", "--others", "--exclude-standard"))
    return sorted(p for p in paths if not p.startswith(".fos-lock"))


def ensure_tip(witness, rel):
    """Make the witness's tip readable here (a fetch into refs/remotes/witness/; the folder is not changed)."""
    if L.git("cat-file", "-e", rel["tip"] + "^{commit}")[0] == 0:
        return True
    branch = L.witness_branch(witness["history"])
    L.git("fetch", "-q", witness["history"], "+refs/heads/%s:refs/remotes/witness/%s" % (branch, branch))
    return L.git("cat-file", "-e", rel["tip"] + "^{commit}")[0] == 0


def record_lines(data):
    return [x for x in (data or b"").replace(b"\r\n", b"\n").split(b"\n") if x.strip()]


def max_seq(lines):
    n = 0
    for raw in lines:
        try:
            o = json.loads(raw)
        except ValueError:
            continue
        if isinstance(o, dict) and isinstance(o.get("seq"), int):
            n = max(n, o["seq"])
    return n


def plan(rel):
    """What a sync would keep and set aside. rel is from L.witness_relation()."""
    tip, base = rel["tip"], rel.get("base")
    moved_on = base != tip                       # the witness gained commits since the common one
    theirs = names(L.git("diff", "--name-only", "--no-renames", base, tip)) if base and moved_on else set()
    p = {"keep_files": [], "aside_files": [], "keep_lines": {}, "aside_lines": {}, "mine": mine_since(base, tip)}
    for path in p["mine"]:
        cur = L.read_bytes(path)
        if path.startswith("records/") and path.endswith(".jsonl"):
            tgt = record_lines(show(tip, path))
            known = set(tgt) | set(record_lines(show(base, path)))
            top = max_seq(tgt)
            new = [x for x in record_lines(cur) if x not in known]
            keep, aside = [], []
            for raw in new:
                try:
                    o = json.loads(raw)
                    fits = isinstance(o, dict) and isinstance(o.get("seq"), int) and o["seq"] > top
                except ValueError:
                    fits = False
                (keep if fits and base and not moved_on else aside).append(raw)
            if keep:
                p["keep_lines"][path] = keep
            if aside:
                p["aside_lines"][path] = aside
        elif path in TAKE_FROM_WITNESS:
            continue
        elif base and path not in theirs:
            p["keep_files"].append(path)
        else:
            p["aside_files"].append(path)
    return p


def describe(rel, p):
    state = rel["state"]
    head = {"behind": "This folder is behind its witness by %d close-out(s): another copy of this organization was "
                      "closed out." % rel.get("n", 0),
            "diverged": "This folder and its witness split at commit %s: this folder has %d commit(s) the witness "
                        "never accepted%s." % ((rel.get("base") or "?")[:12], rel.get("n", 0),
                                               ", and the witness has %d this folder lacks" % rel["behind_n"]
                                               if rel.get("behind_n") else ""),
            "unrelated": "This folder's history shares no commit with its witness: it was replaced.",
            "ahead_bad": "This folder has %d commit(s) the witness refused (see the check)." % rel.get("n", 0),
            }.get(state, state)
    lines = [head, "A sync returns this folder to the witness's last close-out (%s) and:" % rel["tip"][:12]]
    kl = sum(len(v) for v in p["keep_lines"].values())
    al = sum(len(v) for v in p["aside_lines"].values())
    lines.append("  keeps %d record line(s) added here%s" % (kl, (" (" + ", ".join(sorted(p["keep_lines"])) + ")") if kl else ""))
    lines.append("  keeps %d other changed file(s) here%s" % (len(p["keep_files"]), (": " + ", ".join(p["keep_files"][:8]))
                                                            if p["keep_files"] else ""))
    lines.append("  sets aside %d record line(s)%s" % (al, (" (" + ", ".join(sorted(p["aside_lines"])) + ")") if al else ""))
    lines.append("  sets aside %d file(s)%s" % (len(p["aside_files"]), (": " + ", ".join(p["aside_files"][:8]))
                                               if p["aside_files"] else ""))
    lines.append("Everything that differs from the witness is first copied into the witness folder, so nothing is lost.")
    return "\n".join(lines)


def back_up(witness, rel, p):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    dest = os.path.join(witness["folder"], "set_aside", stamp)
    os.makedirs(os.path.join(dest, "before_sync"))
    deleted = []
    for path in p["mine"]:
        data = L.read_bytes(path)
        if data is None:
            deleted.append(path)
            continue
        out = os.path.join(dest, "before_sync", *path.split("/"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(data)
    manifest = {"state": rel["state"], "witness_tip": rel["tip"], "folder_head": rel.get("head"), "base": rel.get("base"),
                "kept_files": p["keep_files"], "set_aside_files": p["aside_files"], "deleted_here": deleted,
                "kept_record_lines": {k: len(v) for k, v in p["keep_lines"].items()},
                "set_aside_record_lines": {k: [x.decode("utf-8", "replace") for x in v] for k, v in p["aside_lines"].items()},
                "note": "before_sync/ holds every file of the organization's folder that differed from the witness, as "
                        "it was just before the sync. Nothing here was merged into the organization."}
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    return dest


def run_sync(witness, rel, p):
    """Back up, return to the witness's tip, carry forward what plan() keeps, and record the sync."""
    dest = back_up(witness, rel, p)
    keep_bytes = {path: L.read_bytes(path) for path in p["keep_files"]}
    code, out = L.git("reset", "-q", "--hard", rel["tip"])   # safe: everything that differs is copied above
    if code != 0:
        say("Could not return to the witness's history: %s. Nothing else was changed; the copies are in %s."
            % (out, dest))
        return 1
    for path, data in keep_bytes.items():
        full = L.path(path)
        if data is None:
            if os.path.exists(full):
                os.remove(full)
            continue
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data)
    with L.RecordsLock():
        for path, kept in p["keep_lines"].items():
            data = L.read_bytes(path) or b""
            with open(L.path(path), "ab") as f:
                if data and not data.endswith(b"\n"):
                    f.write(b"\n")
                f.write(b"".join(x + b"\n" for x in kept))
    kl = sum(len(v) for v in p["keep_lines"].values())
    al = sum(len(v) for v in p["aside_lines"].values())
    rel_dest = os.path.relpath(dest, os.path.dirname(L.ROOT)).replace("\\", "/")
    L.append_record("event", {
        "type": "sync", "captured_by": "sync_script",
        "summary": "Brought this folder in line with its witness (%s, at %s): kept %d record line(s) and %d file(s); "
                   "set aside %d record line(s) and %d file(s) in %s" % (rel["state"], rel["tip"][:12], kl,
                                                                      len(p["keep_files"]), al, len(p["aside_files"]),
                                                                      rel_dest),
        "refs": [rel_dest], "witness_tip": rel["tip"], "folder_head_before": rel.get("head")}, writer="fos_sync")
    say("Done. This folder now starts from the witness's close-out %s." % rel["tip"][:12])
    say("Copies of everything that differed are in %s (manifest.json lists what was kept and set aside)." % dest)
    if al or p["aside_files"]:
        say("Set-aside work is not part of the organization. To bring any of it back, have a member record or propose "
            "it again in this folder.")
    return 0


def main(argv):
    if "--test-answers" in argv:
        i = argv.index("--test-answers")
        TEST["answers"] = [a for a in (argv[i + 1] if i + 1 < len(argv) else "").split(",") if a]
    check_only = "--check" in argv
    witness = L.find_witness()
    rel = L.witness_relation(witness)
    state = rel["state"]
    if state in ("unknown", "empty"):
        say("No witness history can be read from here (%s)." % ("none found" if not witness else state))
        return 0 if check_only else 1
    if state == "equal":
        say("This folder is in line with its witness (%s)." % rel["tip"][:12])
        return 0
    if state == "ahead":
        problems = L.history_problems()
        if not problems:
            say("This folder has %d close-out commit(s) the witness does not hold yet; the next close-out pushes "
                "them (or: git push witness)." % rel["n"])
            return 0
        say("This folder has %d commit(s) that the witness refuses:" % rel["n"])
        for prob in problems:
            say("  - " + prob)
        rel = dict(rel, state="ahead_bad")
    if not ensure_tip(witness, rel):
        say("The witness's history could not be read into this folder; nothing was changed.")
        return 1
    p = plan(rel)
    say(describe(rel, p))
    if check_only:
        return 1
    if TEST["answers"] is None and not (sys.stdin.isatty() and sys.stdout.isatty()):
        say("A sync changes the folder's history, so it runs only in a terminal you are typing in, never from an agent "
            "app. Run: python scripts/fos_sync.py")
        return 3
    if "--yes" not in argv and ask("Sync now?") != "y":    # --yes: the close-out has just asked the founder
        say("Nothing was changed.")
        return 1
    return run_sync(witness, rel, p)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
