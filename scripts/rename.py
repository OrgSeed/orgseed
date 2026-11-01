"""Rename the seed: list every place its name appears, or change it everywhere at once.

Usage:
  python scripts/rename.py --list [--prefix]
  python scripts/rename.py "New Name" [--prefix new] [--dry-run]

The name lives in seed.json and in as few other places as possible. --list prints every file and
line where it appears (and, with --prefix, every use of the scripts' "fos_" prefix). Renaming
replaces the name in every text file of the seed; with --prefix it also renames scripts/fos_*.py
and every reference to them. Run it on the seed, not on an organization, and commit the result as
one change. Git history is never rewritten: commits made before the rename keep the old name.
Standard library only; no network.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402

PREFIX = "fos"
PREFIX_RX = re.compile(r"(?<![A-Za-z0-9])%s_" % PREFIX)


def text_files():
    code, out = L.git("ls-files", "-co", "--exclude-standard")
    if code == 0:
        rels = [x for x in out.splitlines() if x.strip()]
    else:
        rels = []
        for d, dirs, fs in os.walk(L.ROOT):
            dirs[:] = [x for x in dirs if x not in (".git", "__pycache__")]
            rels += [os.path.relpath(os.path.join(d, f), L.ROOT).replace("\\", "/") for f in fs]
    out = []
    for rel in sorted(rels):
        data = L.read_bytes(rel)
        if data is not None and b"\0" not in data[:4096]:
            out.append(rel)
    return out


def occurrences(needle_rx):
    hits = []
    for rel in text_files():
        for i, line in enumerate((L.read_text(rel, "") or "").splitlines(), 1):
            if needle_rx.search(line):
                hits.append((rel, i, line.strip()))
    return hits


def history_mentions(name):
    code, out = L.git("log", "--all", "--format=%an%n%cn%n%B")
    return out.count(name) if code == 0 else None


def main(argv):
    args = [a for a in argv[1:]]
    seed = L.seed_info()
    old = seed.get("name", "")
    with_prefix = "--prefix" in args
    if "--list" in args:
        hits = occurrences(re.compile(re.escape(old)))
        print("The name %r appears %d time(s) in %d file(s):" % (old, len(hits), len({h[0] for h in hits})))
        for rel, i, line in hits:
            print("  %s:%d: %s" % (rel, i, line[:120]))
        n = history_mentions(old)
        if n is not None:
            print("Git history mentions it %d time(s) (author names and messages); history is never rewritten." % n)
        if with_prefix:
            ph = occurrences(PREFIX_RX)
            print("The scripts' prefix %r appears on %d line(s) in %d file(s)." % (PREFIX + "_", len(ph), len({h[0] for h in ph})))
        return 0
    if not args or args[0].startswith("--"):
        print(__doc__)
        return 2
    new = args[0].strip()
    if not new or "\n" in new or '"' in new or new == old:
        print("Give a new name, different from %r, without quotes or line breaks." % old)
        return 2
    new_prefix = args[args.index("--prefix") + 1] if with_prefix and args.index("--prefix") + 1 < len(args) else None
    if with_prefix and (not new_prefix or not re.fullmatch(r"[a-z][a-z0-9]*", new_prefix)):
        print("--prefix needs a short lowercase word, e.g. --prefix org")
        return 2
    dry = "--dry-run" in args
    changed = 0
    for rel in text_files():
        text = L.read_text(rel, "")
        new_text = text.replace(old, new)
        if new_prefix:
            new_text = PREFIX_RX.sub(new_prefix + "_", new_text)
        if new_text != text:
            changed += 1
            print("  %s %s" % ("would change" if dry else "changed", rel))
            if not dry:
                with open(L.path(rel), "w", encoding="utf-8", newline="\n") as f:
                    f.write(new_text)
    if new_prefix:
        for fn in sorted(os.listdir(L.path("scripts"))):
            if fn.startswith(PREFIX + "_") and fn.endswith(".py"):
                target = new_prefix + "_" + fn[len(PREFIX) + 1:]
                print("  %s scripts/%s -> scripts/%s" % ("would rename" if dry else "renamed", fn, target))
                if not dry:
                    if L.git_ok():
                        subprocess.run(["git", "-C", L.ROOT, "mv", "scripts/" + fn, "scripts/" + target], capture_output=True)
                    if os.path.exists(L.path("scripts/" + fn)):
                        os.replace(L.path("scripts/" + fn), L.path("scripts/" + target))
    print("%s %d file(s). Review the change, then commit it as one step." % ("Would change" if dry else "Changed", changed))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
