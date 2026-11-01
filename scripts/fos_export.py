"""Export the organization as one file that carries its whole history.

Usage:
  python scripts/fos_export.py [<output.bundle>] [--zip]

Writes, outside the organization's folder (by default next to it):
  <name>-export-<UTC time>.bundle               a git bundle: every commit, so every record, file and the view
  <name>-export-<UTC time>.bundle.RELOCATION.md what the bundle is, what it leaves behind, how to open it
  <name>-export-<UTC time>.zip (with --zip)     the files as last committed, without history, for people
                                                who do not use git
To open the bundle elsewhere: git clone <file>.bundle <new-folder>. Then give the organization a new
witness there: python scripts/fos_witness.py setup <new-folder>-witness, and
git remote add witness <new-folder>-witness/history.git (or let the next close-out offer to).

What is never in an export: anything not committed (run the close-out first), keys and anything
else the ignore list keeps out, agent-app state, the witness folder, sealed drill descriptions,
and transcripts. Exports are made from the committed history, never by copying the folder.
Standard library only; no network.
"""
import datetime
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402
import fos_check as C  # noqa: E402


def run(args):
    r = subprocess.run(args, capture_output=True)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace").strip()


def main(argv):
    if not (L.git_ok() and L.has_head()):
        print("An export needs git and at least one commit. Run the close-out first (python scripts/fos_close.py).")
        return 1
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = os.path.basename(L.ROOT)
    args = [a for a in argv[1:] if not a.startswith("--")]
    out = os.path.abspath(args[0]) if args else os.path.join(os.path.dirname(L.ROOT), "%s-export-%s.bundle" % (name, stamp))
    try:
        inside = os.path.commonpath([L.ROOT, out]) == L.ROOT
    except ValueError:
        inside = False
    if inside:
        print("Write the export outside the organization's folder, so it never enters its history.")
        return 1
    code, status = L.git("status", "--porcelain")
    pending = [ln for ln in status.splitlines() if ln.strip()]
    code, branch = L.git("branch", "--show-current")
    branch = branch.strip() or "HEAD"
    code, msg = run(["git", "-C", L.ROOT, "bundle", "create", out, "HEAD", branch, "--tags"])
    if code != 0:
        print("git bundle failed: %s" % msg)
        return 1
    code, verify = run(["git", "-C", L.ROOT, "bundle", "verify", out])
    if code != 0:
        print("the bundle did not verify: %s" % verify)
        return 1
    tip = L.git("rev-parse", "HEAD")[1].strip()
    count = L.git("rev-list", "--count", "HEAD")[1].strip()
    born = L.stage_info()["birth"] or {}
    seed = born.get("seed") or {}
    R = C.run_checks()
    lines = [
        "# Relocation note",
        "",
        "This file travels next to `%s`. It is not part of the organization." % os.path.basename(out),
        "",
        "- Organization folder: %s" % name,
        "- Exported: %s (UTC)" % stamp,
        "- Commits: %s, ending at %s on branch %s" % (count, tip, branch),
        "- Born from: %s %s; birth hash (seed tree) %s" % (seed.get("name", "?"), seed.get("version", "?"), seed.get("tree", "?")),
        "- Record format version: %s" % L.config().get("format_version", "?"),
        "- Check at export: %s" % ("FAILED (%d)" % len(R.fails) if R.fails else "OK, %d warning(s)" % len(R.warns)),
        "",
        "## Left behind",
        "",
        "- %d uncommitted change(s) in the folder%s" % (len(pending), " (run the close-out and export again to include them)" if pending else ""),
        "- keys and other files the ignore list keeps out, agent-app state, and machine-local settings",
        "- the witness folder, the sealed drill descriptions in it, and any transcripts kept there",
        "",
        "## Opening it elsewhere",
        "",
        "1. `git clone %s <new-folder>`" % os.path.basename(out),
        "2. Give it a new witness: `python scripts/fos_witness.py setup <new-folder>-witness`, then",
        "   `git remote add witness <new-folder>-witness/history.git` (or let the next close-out offer to).",
        "3. On a new machine, re-approve any tool the organization runs: what was safe to run on the old machine",
        "   is decided again on the new one.",
        "4. Members whose models are not available there become vacant seats; filling one is a decision.",
        "",
    ]
    with open(out + ".RELOCATION.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("wrote %s (%s commits)" % (out, count))
    print("wrote %s" % (out + ".RELOCATION.md"))
    if pending:
        print("note: %d uncommitted change(s) are not in the export; run the close-out first" % len(pending))
    if "--zip" in argv:
        zpath = out[:-len(".bundle")] + ".zip" if out.endswith(".bundle") else out + ".zip"
        code, msg = run(["git", "-C", L.ROOT, "archive", "--format=zip", "-o", zpath, "HEAD"])
        print(("wrote %s (files as last committed, no history)" % zpath) if code == 0 else ("zip failed: %s" % msg))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
