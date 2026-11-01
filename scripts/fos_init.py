"""Create a new organization from this seed. No AI, no network: the same command gives the same start.

Usage:
  python scripts/fos_init.py <new-folder> [--from <revision>] [--witness <folder>] [--no-witness]
                                         [--study <study.json>]
  python scripts/fos_init.py --ask         asks for a name, and makes the organization next to the seed's folder
                                           (what the double-click launcher Found-an-organization runs)

What it does:
  1. Copies the seed's files, exactly as committed at <revision> (default: the current commit),
     into <new-folder>. Uncommitted changes in this folder are not copied.
  2. Starts a git repository there and commits the files as its first commit,
     "[SEED] born from <name> <version>". That commit's tree id is the birth hash: it equals the
     seed's tree at <revision>, so anyone can check that the organization started identical to
     the seed (git rev-parse <revision>^{tree} in the seed's repository).
  3. Creates the witness next to the new folder (<new-folder>-witness): a copy of the history
     kept outside the members' reach, which refuses rewrites and deletions.
  4. Records the birth (a 'born' event naming the seed, its revision and the birth hash) and the
     witness, commits that as "[BIRTH] ...", and pushes both commits to the witness.
Then open <new-folder> in your agent app and say: "Read AGENTS.md and follow it."

--study is for research only, never for a founder's own organization: it makes the organization a
research configuration in which named core rules are switched off (today only CORE-13, the claim rule,
and its checks), in a third commit, "[STUDY] ...", right after the birth. The study file holds
{"name": ..., "switch_off": ["CORE-13"], "status": "exploratory" or "confirmatory", "note": ...}.
The change to the boot and onboarding files is fixed by the seed (fos_lib.STUDY_SWITCHES), recorded in
org/STUDY.json and a study_configured event, and shown by the check and the view. Nothing in the
record-keeping core can be switched off.

It checks first that every path will fit on this machine, builds everything in a short staging folder, and
only then moves the organization and its witness into place, so a failure leaves nothing half-made.

Nothing about you goes into these first commits: your name, goal and charter come later, through
the founding session, as your own decisions.

A seed downloaded as a ZIP has no history of its own (no .git), and may even sit inside some other
repository. Then, if git is installed, it copies the seed's files from this folder, computes the birth
hash from them, and still makes the new organization's git repository, its two first commits and its
witness, exactly as from a clone; only --from <revision> needs a clone.
Without git at all, it copies the seed's files from this folder, computes the birth hash itself, and
makes a witness folder that keeps dated copies of records/. Install git for the full record.
Standard library only; no network.
"""
import contextlib
import fnmatch
import io
import json
import os
import re
import tempfile
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402
import fos_witness as W  # noqa: E402

SEED_ID = {"GIT_AUTHOR_NAME": "seed", "GIT_AUTHOR_EMAIL": "", "GIT_COMMITTER_NAME": "seed", "GIT_COMMITTER_EMAIL": ""}


def run(args, cwd=None, env=None, data=None):
    r = subprocess.run(args, cwd=cwd, env=env, input=data, capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", "replace").strip(), r.stderr.decode("utf-8", "replace").strip()


def seed_env():
    stamp = "%d +0000" % int(time.time())
    return dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp, **SEED_ID)


def commit_all(target, message, executable=()):
    run(["git", "-C", target, "add", "-A"])
    exe = sorted(executable)
    for i in range(0, len(exe), 100):     # mode 100755 whatever this machine's file system keeps
        run(["git", "-C", target, "update-index", "--chmod=+x", "--"] + exe[i:i + 100])
    code, tree, err = run(["git", "-C", target, "write-tree"])
    if code != 0:
        raise SystemExit("git write-tree failed: %s" % err)
    parent = run(["git", "-C", target, "rev-parse", "--verify", "--quiet", "HEAD"])[1]
    args = ["git", "-C", target, "commit-tree", tree] + (["-p", parent] if parent else [])
    code, commit, err = run(args, env=seed_env(), data=message.encode("utf-8"))
    if code != 0:
        raise SystemExit("git commit-tree failed: %s" % err)
    run(["git", "-C", target, "update-ref", "refs/heads/main", commit])
    return tree, commit


def git_available():
    """True when git can be run on this machine (whether or not this folder is a repository)."""
    if os.environ.get("SEED_NO_GIT") == "1":     # the self-test's way of simulating a machine without git
        return False
    try:
        return subprocess.run(["git", "--version"], capture_output=True).returncode == 0
    except OSError:
        return False


def _same_folder(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def seed_has_history():
    """True when this seed folder is the top of its own git repository and has a commit (a clone). False for a
    downloaded copy (a ZIP has no .git), and for a copy that sits inside some other repository: that
    repository's history is not the seed's."""
    if not (L.git_ok() and L.has_head()):
        return False
    code, top = L.git("rev-parse", "--show-toplevel")
    return code == 0 and bool(top.strip()) and _same_folder(top.strip(), L.ROOT)


def ignored(rel, patterns):
    parts = rel.split("/")
    for pat in patterns:
        if pat.endswith("/"):
            if any(fnmatch.fnmatch(p, pat[:-1]) for p in parts[:-1]):
                return True
        elif any(fnmatch.fnmatch(p, pat) for p in parts):
            return True
    return False


def files_without_git():
    pats = [ln.strip() for ln in (L.read_text(".gitignore", "") or "").splitlines()
            if ln.strip() and not ln.startswith(("#", "!"))]
    out = {}
    for d, dirs, fs in os.walk(L.ROOT):
        dirs[:] = [x for x in dirs if x != ".git"]
        for fn in fs:
            rel = os.path.relpath(os.path.join(d, fn), L.ROOT).replace("\\", "/")
            if not ignored(rel, pats):
                with open(os.path.join(d, fn), "rb") as f:
                    out[rel] = L.canonical_bytes(rel, f.read())
    return out


def write_files(org, files, executable=()):
    for rel, data in files.items():
        p = os.path.join(org, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        if rel in executable and os.name != "nt":
            os.chmod(p, 0o755)


BIRTH_ABOUT = ("This folder is an organization born from the seed named below. scripts/fos_init.py wrote this file "
               "once, at birth, and nothing edits it. The history (the [BIRTH] commit) and the witness hold the same "
               "birth, so it survives even if records/events.jsonl is damaged.")


def record_birth(target, seed, source_commit, tree, witness_rel):
    L.ROOT = target   # the new organization's own records
    born = {"name": seed["name"], "version": seed["version"], "source_commit": source_commit, "tree": tree}
    L.append_record("event", {"type": "born", "captured_by": "init_script", "session": "S000",
                              "summary": "Born from %s %s; birth hash (seed tree) %s" % (seed["name"], seed["version"], tree),
                              "seed": born}, writer="fos_init")
    with open(L.path(L.BIRTH_FILE), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"about": BIRTH_ABOUT, "seed": born}, f, indent=1, sort_keys=True)
        f.write("\n")
    if witness_rel:
        L.append_record("event", {"type": "witness_created", "captured_by": "init_script", "session": "S000",
                                  "summary": "Witness created outside the organization's folder", "refs": [witness_rel]},
                        writer="fos_init")


MAX_PATH = 259          # Windows' limit on a path, unless long paths are switched on for the machine
ROOM_FOR_WORK = 40      # deeper files an organization may add later (work/, sources/, tools/)
WITNESS_DEPTH = 110     # the longest paths written inside the witness folder (git's own, and set-aside copies)


def long_paths_enabled():
    if os.name != "nt":
        return True
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SYSTEM\\CurrentControlSet\\Control\\FileSystem")
        return winreg.QueryValueEx(key, "LongPathsEnabled")[0] == 1
    except OSError:
        return False


def path_problems(target, witness, rels):
    """Paths too long for this machine, found before anything is created."""
    if long_paths_enabled() or not rels:
        return []
    out = []
    deepest = max(rels, key=len)
    need = len(target) + 1 + len(deepest) + ROOM_FOR_WORK
    if need > MAX_PATH:
        out.append("the organization's folder needs room for paths of about %d characters (for example %s/%s and "
                   "work added later), and this machine allows %d" % (need, target, deepest, MAX_PATH))
    if witness and len(witness) + WITNESS_DEPTH > MAX_PATH:
        out.append("the witness folder (%s) needs room for paths of about %d characters, and this machine allows %d"
                   % (witness, len(witness) + WITNESS_DEPTH, MAX_PATH))
    return out


STUDY_ABOUT = ("A research configuration, made at birth for a study, never for a founder's own organization. The "
               "core rules named in switch_off, and their checks, are switched off; the seed fixes exactly what that "
               "changes in the boot and onboarding files (files_changed, with their SHA-256 after the change). The "
               "record-keeping core is the same as in every organization.")


def apply_study(org, study, seed_tree):
    """Make the staged organization a research configuration: the seed's fixed changes, org/STUDY.json, an event."""
    L.ROOT = org
    texts = {}
    for spec in [L.STUDY_SWITCHES[r] for r in study["switch_off"]]:
        for rel in ["AGENTS.md"] + [x[0] for x in spec["replace"]]:
            texts[rel] = L.read_text(rel)
    changed = L.study_transform(texts, study["switch_off"])
    digests = {}
    for rel, text in sorted(changed.items()):
        with open(L.path(rel), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        digests[rel] = L.file_sha256(rel)
    doc = {"about": STUDY_ABOUT, "name": study.get("name", "unnamed study"), "switch_off": study["switch_off"],
           "switched_off_means": {r: L.STUDY_SWITCHES[r]["about"] for r in study["switch_off"]},
           "status": study.get("status", "exploratory"), "note": study.get("note", ""), "seed_tree": seed_tree,
           "files_changed": digests}
    with open(L.path(L.STUDY_FILE), "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    L.append_record("event", {"type": "study_configured", "captured_by": "init_script", "session": "S000",
                              "summary": "Made a research configuration for the study %r: %s switched off (%s)"
                                         % (doc["name"], ", ".join(study["switch_off"]), doc["status"]),
                              "refs": [L.STUDY_FILE]}, writer="fos_init")


def build_with_git(org, wit, seed, source_commit, seed_tree, files, witness_rel, study=None, executable=()):
    """Build the organization and its witness in a staging folder (org, wit), from files ({path: bytes}: the
    seed's commit, or a downloaded copy's files); executable names the files kept with mode 100755. Raises on
    any failure."""
    write_files(org, files, executable)
    run(["git", "init", "-q", "--initial-branch=main", org])
    for key, value in (("core.autocrlf", "false"), ("core.longpaths", "true")):
        run(["git", "-C", org, "config", key, value])
    revision = source_commit or "none (a downloaded copy with no history; the birth hash is computed from its files)"
    tree, first = commit_all(org, "[SEED] born from %s %s\n\nSeed revision: %s\nBirth hash (seed tree): %s\n"
                             % (seed["name"], seed["version"], revision, seed_tree), executable)
    if tree != seed_tree:
        raise RuntimeError("the new organization's first tree (%s) differs from the seed's (%s)" % (tree, seed_tree))
    if wit:
        quiet = io.StringIO()
        with contextlib.redirect_stdout(quiet):
            if W.setup(wit) != 0:
                raise RuntimeError("the witness could not be created: %s" % quiet.getvalue().strip())
        run(["git", "--git-dir", os.path.join(wit, "history.git"), "config", "core.longpaths", "true"])
        run(["git", "-C", org, "remote", "add", "witness", witness_rel + "/history.git"])
    record_birth(org, seed, source_commit, seed_tree, witness_rel)
    commit_all(org, "[BIRTH] birth record: born from %s %s, seed tree %s\n" % (seed["name"], seed["version"], seed_tree))
    if study:
        apply_study(org, study, seed_tree)
        commit_all(org, "[STUDY] research configuration: %s switched off\n\nFor a study only. org/STUDY.json says what "
                        "changed and why.\n" % ", ".join(study["switch_off"]))
    if wit:   # pushed by path: the remote names the witness where it will be, not where it is being built
        code, out, err = run(["git", "-C", org, "push", "-q", os.path.join(wit, "history.git"), "main"])
        if code != 0:
            raise RuntimeError("the witness refused the first push:\n%s" % (out + err))


def build_without_git(org, wit, seed, files, tree, witness_rel, executable=()):
    write_files(org, files, executable)
    if wit:
        for sub in ("snapshots", "drills"):
            os.makedirs(os.path.join(wit, sub), exist_ok=True)
    record_birth(org, seed, None, tree, witness_rel)
    if wit:
        L.write_local_settings({"witness": witness_rel})
        quiet = io.StringIO()
        with contextlib.redirect_stdout(quiet):
            if W.snapshot(org, wit) != 0:
                raise RuntimeError("the first dated copy could not be made: %s" % quiet.getvalue().strip())


def _rmtree(p):
    def unlock(func, path, _):
        os.chmod(path, 0o700)     # git keeps its object files read-only
        func(path)
    if os.path.exists(p):
        shutil.rmtree(p, onerror=unlock)


NAME_OK = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _.-]{0,39}")


def ask_target():
    """The new organization's folder, from a name the founder types: next to the seed's folder."""
    parent = os.path.dirname(L.ROOT)
    seed = L.seed_info()
    print("Found a new organization from %s %s. No AI is involved." % (seed.get("name"), seed.get("version")))
    print("It is made next to this folder, in %s, with its witness beside it." % parent)
    while True:
        try:
            name = input("A short name for the new organization's folder [my-organization]: ").strip()
        except EOFError:
            return None
        name = name or "my-organization"
        if not NAME_OK.fullmatch(name) or name.endswith((".", " ")):
            print("  Please use letters, digits, spaces, '-', '_' or '.', up to 40 characters, starting with a letter "
                  "or digit.")
            continue
        target = os.path.join(parent, name)
        if os.path.exists(target) or os.path.exists(target + "-witness"):
            print("  %s (or its witness) already exists; choose another name." % target)
            continue
        return target


def main(argv):
    args = [a for a in argv[1:]]
    if L.stage_info()["stage"] != "seed":
        print("This folder is an organization born from the seed, not the seed itself. A new organization is founded "
              "from the seed's own folder.")
        return 1
    if "--ask" in args:
        target = ask_target()
        if not target:
            print("No name was given; nothing was created.")
            return 1
        args = [target] + [a for a in args if a != "--ask"]
    if not args or args[0].startswith("-"):
        print(__doc__)
        return 2
    target = os.path.abspath(args[0])
    rev = args[args.index("--from") + 1] if "--from" in args else "HEAD"
    want_witness = "--no-witness" not in args
    witness = os.path.abspath(args[args.index("--witness") + 1]) if "--witness" in args else target + "-witness"
    seed_root = L.ROOT
    if os.path.exists(target) and os.listdir(target):
        print("%s already exists and is not empty; choose a new folder" % target)
        return 1
    if os.path.commonpath([seed_root, target]) == seed_root:
        print("the new organization must be outside the seed's folder")
        return 1
    if want_witness and os.path.exists(witness):
        print("%s already exists; choose another witness folder (--witness) or remove it" % witness)
        return 1
    seed = L.seed_info()
    witness_rel = os.path.relpath(witness, target).replace("\\", "/") if want_witness else None
    use_git = git_available()
    from_history = use_git and seed_has_history()
    if "--from" in args and not from_history:
        print("--from needs the seed's history (a clone made with git); this copy has none, so it can only be born "
              "from its files as they are")
        return 1
    study = None
    if "--study" in args:
        try:
            with open(args[args.index("--study") + 1], encoding="utf-8-sig") as f:
                study = json.load(f)
        except (OSError, ValueError, IndexError) as e:
            print("the study file could not be read: %s" % e)
            return 1
        bad = [r for r in study.get("switch_off") or [] if r not in L.STUDY_SWITCHES]
        if not study.get("switch_off") or bad:
            print("a study may switch off only %s (asked: %s)" % (", ".join(L.STUDY_SWITCHES), study.get("switch_off")))
            return 1
        if study.get("status", "exploratory") not in ("exploratory", "confirmatory"):
            print("a study's status is exploratory or confirmatory")
            return 1
        if not use_git:
            print("a research configuration is confirmed through the history, so it needs git")
            return 1
    files, source_commit, executable = None, None, []
    if from_history:
        code, source_commit, err = run(["git", "-C", seed_root, "rev-parse", rev + "^{commit}"])
        if code != 0:
            print("revision %s not found in the seed: %s" % (rev, err))
            return 1
        seed_tree = run(["git", "-C", seed_root, "rev-parse", rev + "^{tree}"])[1]
        dirty = run(["git", "-C", seed_root, "status", "--porcelain", "--untracked-files=no"])[1]
        if dirty and rev == "HEAD":
            print("note: this seed folder has uncommitted changes; they are not copied (the commit is)")
        code, listing, err = run(["git", "-C", seed_root, "ls-tree", "-r", "-z", "--full-tree", source_commit])
        entries = []
        for item in listing.split("\0"):
            if not item:
                continue
            meta, _, rel = item.partition("\t")
            mode, kind, sha = meta.split()
            if kind != "blob" or mode not in ("100644", "100755"):
                print("the seed holds %s (%s), which a new organization cannot copy" % (rel, mode))
                return 1
            entries.append((rel, sha))
            if mode == "100755":
                executable.append(rel)
        rels = [rel for rel, _ in entries] + [".git/objects/xx/" + "x" * 38]
    else:
        files = files_without_git()
        executable = [rel for rel in files if L.is_executable_path(rel)]
        tree = seed_tree = L.git_tree_id(files, executable)
        rels = list(files) + ([".git/objects/xx/" + "x" * 38] if use_git else [])
    problems = path_problems(target, witness if want_witness else None, rels)
    if problems:
        print("stopped before creating anything: these paths would be too long on this machine.")
        for p in problems:
            print("  - " + p)
        print("Choose a folder with a shorter path (for example C:\\orgs\\my-organization), or switch on long "
              "paths for Windows and try again.")
        return 1
    # Everything is built in a staging folder with short paths, then moved into place, so that a failure
    # anywhere leaves nothing half-made behind.
    stage = tempfile.mkdtemp(prefix="fos-init-")
    s_org = os.path.join(stage, "o")
    s_wit = os.path.join(stage, "w") if want_witness else None
    moved = []
    try:
        if use_git:
            if from_history:
                blobs = W.read_blobs(["-C", seed_root], [sha for _, sha in entries])
                files = {rel: blobs[sha] for rel, sha in entries}
            build_with_git(s_org, s_wit, seed, source_commit, seed_tree, files, witness_rel, study, executable)
        else:
            build_without_git(s_org, s_wit, seed, files, tree, witness_rel, executable)
        if os.environ.get("SEED_SELFTEST") == "1" and os.environ.get("SEED_INIT_FAIL") == "1":
            raise RuntimeError("stopped on purpose by the self-test, just before moving into place")
        if os.path.isdir(target):
            os.rmdir(target)                 # empty, checked above
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.move(s_org, target)
        moved.append(target)
        if want_witness:
            os.makedirs(os.path.dirname(witness), exist_ok=True)
            shutil.move(s_wit, witness)
            moved.append(witness)
    except Exception as e:  # leave nothing half-made: undo whatever reached its place
        for p in moved:
            _rmtree(p)
        print("stopped: %s\nNothing was created at %s%s." % (e, target, (" or " + witness) if want_witness else ""))
        return 1
    finally:
        _rmtree(stage)
    if use_git:
        print("Born: %s" % target)
        if from_history:
            print("  birth hash (seed tree): %s, from %s %s at %s" % (seed_tree, seed["name"], seed["version"],
                                                                     source_commit[:12]))
        else:
            print("  birth hash (seed tree): %s, from %s %s, a downloaded copy with no history (the tree is computed "
                  "from its files)" % (seed_tree, seed["name"], seed["version"]))
        print("  witness: %s" % (witness if want_witness else "none (--no-witness)"))
        if study:
            print("  RESEARCH CONFIGURATION for the study %r: %s switched off (org/STUDY.json). For a study only."
                  % (study.get("name"), ", ".join(study["switch_off"])))
    else:
        print("Born without git: %s" % target)
        print("  birth hash (computed seed tree): %s" % tree)
        print("  witness: %s (dated copies of records/)" % (witness if want_witness else "none"))
        print("  Install git to keep the full history; until then the close-out keeps dated copies.")
    print("Next: open %s in your agent app and say: \"Read AGENTS.md and follow it.\"" % target)
    print("At the end of each session, close out in that folder: double-click Close-out (Close-out.cmd on Windows, "
          "Close-out.command on macOS), or run python scripts/fos_close.py from a terminal there.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
