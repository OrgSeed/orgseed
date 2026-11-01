"""The witness: a copy of the organization's history kept outside the members' reach.

A witness is a folder next to the organization's folder, never inside it:

  <organization>-witness/
    history.git/   a bare git repository; the founder's close-out pushes here
    snapshots/     dated copies of records/, used when git is not available
    drills/        sealed drill descriptions (scripts/fos_drill.py)
    transcripts/   a place for the founder to keep agent-app transcripts
    README.txt

Whoever pushes, and from whatever agent app, the witness refuses:
  - deleting a branch or a tag, and moving a tag;
  - a push that does not extend the history it already holds (a rewrite);
  - any branch other than its one branch;
  - merge commits, and a history with more than one first commit;
  - any commit, anywhere in the pushed history, that deletes or renames a
    records file (records/*.jsonl), or changes one other than by adding
    lines at its end;
  - in an organization's history, any commit that holds its structural files
    (STRUCTURE_FILES below) changed from its birth while no earlier commit
    founds it: a close-out commit holding the founder's FOUND.

This file is self-contained: standard library only, and it imports nothing
from the organization's other scripts. A copy of it runs inside the witness as
a git hook, so a member who edits the organization's scripts cannot weaken it.

Usage (people and scripts):
  python scripts/fos_witness.py setup <witness-folder> [--branch main]
  python scripts/fos_witness.py verify <witness-folder> [--json]
  python scripts/fos_witness.py check-history <repository> [<revision>]
  python scripts/fos_witness.py snapshot <organization-folder> <witness-folder>
  python scripts/fos_witness.py check-snapshot <organization-folder> <witness-folder>
git itself calls "pre-receive" through the hook; people never need to.

No network.
"""
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

ZERO = "0" * 40
RECORDS = "records/"
HOOK_SCRIPT = "witness_check.py"
DEFAULT_BRANCH = "main"


class GitError(Exception):
    pass


def run_git(args, cwd=None, data=None):
    try:
        r = subprocess.run(["git"] + list(args), cwd=cwd, input=data, capture_output=True)
    except OSError as e:
        raise GitError("git could not be started: %s" % e)
    return r.returncode, r.stdout, r.stderr


def git_text(gp, *args):
    code, out, err = run_git(list(gp) + list(args))
    if code != 0:
        raise GitError("git %s failed: %s" % (" ".join(args), err.decode("utf-8", "replace").strip()))
    return out.decode("utf-8", "replace")


def rev_parse(gp, rev):
    code, out, _ = run_git(list(gp) + ["rev-parse", "--verify", "--quiet", rev])
    return out.decode().strip() if code == 0 and out.strip() else None


def is_ancestor(gp, a, b):
    code, _, _ = run_git(list(gp) + ["merge-base", "--is-ancestor", a, b])
    return code == 0


def read_blobs(gp, shas):
    """Return {sha: bytes} for blob ids, using one git process."""
    shas = [s for s in dict.fromkeys(shas) if s and s != ZERO]
    if not shas:
        return {}
    code, out, err = run_git(list(gp) + ["cat-file", "--batch"], data=("\n".join(shas) + "\n").encode())
    if code != 0:
        raise GitError("git cat-file failed: %s" % err.decode("utf-8", "replace"))
    blobs, i = {}, 0
    while i < len(out):
        j = out.index(b"\n", i)
        head = out[i:j].decode().split()
        i = j + 1
        if len(head) < 3 or head[1] == "missing":
            continue
        size = int(head[2])
        blobs[head[0]] = out[i:i + size]
        i += size + 1
    return blobs


def is_append(old, new):
    """True when new is old with lines added at the end, and nothing else."""
    if not new.startswith(old):
        return False
    if old and not old.endswith(b"\n") and len(new) > len(old) and new[len(old):len(old) + 1] != b"\n":
        return False  # the last line was extended, not followed by a new one
    return True


def check_history(gp, tip, allow_test=None):
    """Check every commit reachable from tip. Return a list of plain-language violations. allow_test: whether a test-mode
    founding counts (None: only in the seed's own self-test; the witness passes its own setting, witness_test_mode)."""
    problems = []
    roots = []
    for line in git_text(gp, "rev-list", "--parents", tip).splitlines():
        parts = line.split()
        if not parts:
            continue
        if len(parts) == 1:
            roots.append(parts[0])
        elif len(parts) > 2:
            problems.append("commit %s is a merge; this history keeps a single line" % parts[0][:10])
    if len(roots) != 1:
        problems.append("the history has %d first commits; it must have exactly one" % len(roots))
    out = git_text(gp, "log", "--reverse", "--no-renames", "--raw", "--no-abbrev", "--format=@@%H", tip, "--", RECORDS)
    changes, commit = [], None
    for line in out.splitlines():
        if line.startswith("@@"):
            commit = line[2:].strip()
        elif line.startswith(":"):
            meta, _, path = line.partition("\t")
            f = meta[1:].split()
            path = path.strip().strip('"')
            if len(f) >= 5 and path.endswith(".jsonl"):
                changes.append((commit, f[4][0], f[2], f[3], path, f[1]))
    needed = [c[2] for c in changes if c[1] == "M"] + [c[3] for c in changes if c[1] == "M"]
    blobs = read_blobs(gp, needed)
    for commit, status, old, new, path, new_mode in changes:
        where = "commit %s, %s" % (commit[:10], path)
        if status == "D":
            problems.append("%s: a records file was deleted or renamed" % where)
        elif status == "T":
            problems.append("%s: a records file changed type" % where)
        elif status in ("A", "M") and new_mode not in ("100644", "100755"):
            problems.append("%s: a records file must be a plain file" % where)
        if status == "M" and not is_append(blobs.get(old, b""), blobs.get(new, b"")):
            problems.append("%s: earlier lines were changed or removed (records only grow)" % where)
    fh = founding_history(gp, tip, allow_test)
    for commit, subject, diffs in fh["violations"][:3]:
        problems.append("STRUCTURE BEFORE FOUNDING: commit %s (\"%s\") holds %s changed from the organization's birth, "
                        "but no earlier commit founds the organization. Structure is committed only after a close-out "
                        "at which the founder founds it by typing FOUND (scripts/fos_close.py)"
                        % (commit[:10], subject[:60], describe_differences(diffs)))
    if len(fh["violations"]) > 3:
        problems.append("STRUCTURE BEFORE FOUNDING: %d more commit(s) like these" % (len(fh["violations"]) - 3))
    return problems


# ---------------------------------------------------------------- founding before structure: one invariant on files and history

# The organization's structure is in these files. No commit may hold them changed from the organization's birth (its
# first commit) unless an earlier commit founds the organization: a close-out commit ([FOUND]) that adds the founder's
# signature with founding "FOUND", typed by the founder at the close-out's prompt (scripts/fos_close.py). What the
# decision records call themselves (founding: true, a proposal's kind, adopted_by) plays no part in it.
STRUCTURE_FILES = ("org/config.json", "org/TOOLS.json", "view/VIEWS.json", "org/OUR_RULES.md", "org/NORMS.md",
                   "org/CHARTER.md", "org/RECORDS_POLICY.md", "org/FAILURE_PATTERNS.md", "org/DESIGN_AHEAD.md")
FOUNDING_WORD = "FOUND"
FOUNDING_SUBJECT = "[FOUND]"
SIGNATURES, DECISIONS, CONFIG = "records/signatures.jsonl", "records/decisions.jsonl", "org/config.json"


class DuplicateKey(ValueError):
    pass


def _one_of_each(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise DuplicateKey("the key %s is written twice in one object" % json.dumps(k, ensure_ascii=False))
        seen.add(k)
    return dict(pairs)


def strict_loads(text):
    """json.loads, refusing an object that holds the same key twice. Python keeps the last copy of a key, while a person
    reading the file may stop at the first, so such a file says two things; the seed reads it as neither."""
    return json.loads(text, object_pairs_hook=_one_of_each)


def duplicate_key(data):
    """What is written twice in a JSON file's bytes ('the key "modules" is written twice in one object'), or None (also
    for a file that is missing or is not JSON at all: other checks report those)."""
    try:
        strict_loads((data or b"").decode("utf-8"))
    except DuplicateKey as e:
        return str(e)
    except (ValueError, UnicodeDecodeError):
        return None
    return None


def _without_slot(inst):
    return {k: v for k, v in inst.items() if k != "slot"} if isinstance(inst, dict) else inst


def structure_part(rel, data):
    """The part of one structural file that is structure, the same whatever its line endings or JSON layout (None for
    a missing file). In org/config.json, everything but the organization block (the name and the founding, which the
    close-out writes) and the model slots of role instances (filled in at setup, onboarding/START.md, step 3). A JSON
    file that holds a key twice is kept as its text, so it never compares equal to the birth's: what it says is not
    clear, so it counts as changed."""
    if data is None:
        return None
    data = data.replace(b"\r\n", b"\n")
    if not rel.endswith(".json"):
        return data
    try:
        obj = strict_loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return data
    if rel == CONFIG and isinstance(obj, dict):
        obj = {k: v for k, v in obj.items() if k != "organization"}
        if isinstance(obj.get("roles"), list):
            obj["roles"] = [dict(r, instances=[_without_slot(i) for i in r["instances"]])
                            if isinstance(r, dict) and isinstance(r.get("instances"), list) else r for r in obj["roles"]]
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def structure_differences(birth, now):
    """[(file, what changed)] for each structural file whose structure differs between two states ({file: part})."""
    out = []
    for rel in STRUCTURE_FILES:
        a, b = birth.get(rel), now.get(rel)
        if a == b:
            continue
        what = "added" if a is None else "deleted" if b is None else "changed"
        twice = duplicate_key(b) if rel.endswith(".json") and b is not None else None
        if twice:
            what = twice + ", so the file says two things"
        elif rel == CONFIG and a is not None and b is not None:
            try:
                ja, jb = strict_loads(a.decode("utf-8")), strict_loads(b.decode("utf-8"))
                keys = sorted(k for k in set(ja) | set(jb) if ja.get(k) != jb.get(k))
                what = ", ".join(keys) or what
            except (ValueError, AttributeError, UnicodeDecodeError):
                pass
        out.append((rel, what))
    return out


def describe_differences(diffs):
    return ", ".join("%s (%s)" % (rel, what) for rel, what in diffs)


def structure_at(gp, rev):
    """{file: structure part} for the structural files as a commit holds them."""
    code, out, err = run_git(list(gp) + ["ls-tree", "-r", "-z", rev, "--"] + list(STRUCTURE_FILES))
    if code != 0:
        raise GitError("git ls-tree failed: %s" % err.decode("utf-8", "replace").strip())
    ids = {}
    for item in out.decode("utf-8", "replace").split("\0"):
        meta, _, rel = item.partition("\t")
        if len(meta.split()) == 3 and rel in STRUCTURE_FILES:
            ids[rel] = meta.split()[2]
    blobs = read_blobs(gp, ids.values())
    return {rel: structure_part(rel, blobs.get(ids[rel])) if rel in ids else None for rel in STRUCTURE_FILES}


def founder_ids(config_bytes):
    """The founder's role instance IDs, as an org/config.json holds them."""
    try:
        cfg = strict_loads((config_bytes or b"").decode("utf-8"))
        ids = {i.get("id") for r in cfg.get("roles", []) if isinstance(r, dict) and r.get("id") == "founder"
               and r.get("kind") == "human" for i in r.get("instances") or [] if isinstance(i, dict)}
        return ids or {"founder"}
    except (ValueError, AttributeError, UnicodeDecodeError):
        return {"founder"}


def is_founding_signature(s, founders, allow_test=None):
    """A signature by which the founder founded the organization: written by the close-out, signed, with founding
    "FOUND" (the word the founder typed at the close-out's prompt), by a founder; a test-mode one only in the seed's
    own self-test."""
    if allow_test is None:
        allow_test = os.environ.get("SEED_SELFTEST") == "1"
    return (isinstance(s, dict) and s.get("captured_by") == "close_script" and s.get("answer") == "signed"
            and s.get("founding") == FOUNDING_WORD and s.get("signer") in founders
            and (s.get("mode") == "terminal" or (allow_test and s.get("mode") == "test")))


def _jsonl(data):
    out = []
    for raw in (data or b"").split(b"\n"):
        raw = raw.rstrip(b"\r")
        try:
            o = strict_loads(raw.decode("utf-8"))   # a line with a key twice is no record: it says two things
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(o, dict):
            out.append((raw, o))
    return out


def _founding_in(added, decisions, config_bytes, allow_test=None):
    """The founding signature among the signature lines a commit added, checked against the decision line it signs as
    that commit holds it: (signature, decision ID), or None."""
    founders = founder_ids(config_bytes)
    lines = {o.get("id"): (raw, o) for raw, o in _jsonl(decisions)}
    for _, s in _jsonl(added):
        if not is_founding_signature(s, founders, allow_test):
            continue
        raw, d = lines.get(s.get("decision_id"), (None, None))
        if d is None or d.get("seq") != s.get("decision_seq") \
                or hashlib.sha256(raw).hexdigest() != s.get("decision_sha256"):
            continue
        if d.get("verdict") in ("adopted", "amended") and d.get("decided_by") in founders \
                and d.get("decider_kind") == "human":
            return s, d.get("id")
    return None


def founding_history(gp, tip, allow_test=None):
    """Where the organization was founded, and every commit that holds structure before it. Only an organization's
    history is judged: its second commit is the [BIRTH] commit (the seed's own history has none). Returns
    {'org': True when it is an organization's history, 'commit': the founding commit or None, 'decision': the decision
    the founder founded it on, 'signature_seq', 'violations': [(commit, subject, [(file, what changed)])] for each
    commit, the founding commit included, that holds structure changed from birth while no earlier commit founds it}."""
    res = {"org": False, "commit": None, "decision": None, "signature_seq": None, "violations": []}
    revs = git_text(gp, "rev-list", "--reverse", "--topo-order", tip).split()
    if len(revs) < 2 or not git_text(gp, "log", "-1", "--format=%s", revs[1]).startswith("[BIRTH]"):
        return res
    res["org"] = True
    root = revs[0]
    birth = structure_at(gp, root)
    watched = list(STRUCTURE_FILES) + [SIGNATURES, DECISIONS]
    code, out, err = run_git(list(gp) + ["ls-tree", "-r", "-z", root, "--"] + watched)
    cur = {}
    for item in out.decode("utf-8", "replace").split("\0") if code == 0 else []:
        meta, _, rel = item.partition("\t")
        if len(meta.split()) == 3:
            cur[rel] = meta.split()[2]
    log = git_text(gp, "log", "--reverse", "--topo-order", "--no-renames", "--raw", "--no-abbrev",
                   "--format=@@%H %s", tip, "--", *watched)
    commits, c = [], None
    for line in log.splitlines():
        if line.startswith("@@"):
            sha, _, subject = line[2:].partition(" ")
            c = {"sha": sha, "subject": subject, "changes": []}
            commits.append(c)
        elif line.startswith(":") and c is not None:
            meta, _, rel = line.partition("\t")
            f = meta[1:].split()
            if len(f) >= 5:
                c["changes"].append((rel.strip().strip('"'), f[2], f[3]))
    steps = []
    for c in commits:
        if c["sha"] == root:
            continue
        old_sig = cur.get(SIGNATURES)
        for rel, _, new in c["changes"]:
            cur[rel] = None if new == ZERO else new
        sig_changed = any(rel == SIGNATURES for rel, _, _ in c["changes"])
        steps.append((c, {rel: cur.get(rel) for rel in STRUCTURE_FILES}, (old_sig, cur.get(SIGNATURES))
                      if sig_changed and c["subject"].startswith(FOUNDING_SUBJECT) else None,
                      cur.get(DECISIONS), cur.get(CONFIG)))
    blobs = read_blobs(gp, [b for _, ids, _, _, _ in steps for b in ids.values() if b])
    parts = {}

    def part(rel, blob):
        if blob not in parts:
            parts[blob] = structure_part(rel, blobs.get(blob)) if blob else None
        return parts[blob]
    for c, ids, sig, dec, cfg in steps:
        diffs = structure_differences(birth, {rel: part(rel, ids.get(rel)) for rel in STRUCTURE_FILES})
        if diffs:
            res["violations"].append((c["sha"], c["subject"], diffs))
        if sig:
            more = read_blobs(gp, [sig[0], sig[1], dec, cfg])
            old, new = more.get(sig[0], b""), more.get(sig[1], b"")
            found = _founding_in(new[len(old):] if new.startswith(old) else new, more.get(dec), more.get(cfg),
                                 allow_test)
            if found:
                res.update(commit=c["sha"], decision=found[1], signature_seq=found[0].get("seq"))
                break
    return res


# ---------------------------------------------------------------- the hook

def pre_receive():
    gp = []
    code, out, _ = run_git(["config", "--get", "witness.branch"])
    branch = out.decode().strip() if code == 0 and out.strip() else DEFAULT_BRANCH
    head_ref = "refs/heads/" + branch
    allow_test = witness_test_mode(gp)   # fixed at setup; never the environment of whoever pushes
    current = rev_parse(gp, head_ref)
    updates = [ln.split() for ln in sys.stdin.read().splitlines() if ln.strip()]
    problems, new_tip = [], None
    for old, new, ref in updates:
        if new == ZERO:
            problems.append("%s: deleting is refused" % ref)
        elif ref == head_ref:
            if old != ZERO and not is_ancestor(gp, old, new):
                problems.append("this push does not extend the history the witness holds: "
                                "history was rewritten, and the rewrite is refused")
            new_tip = new
        elif ref.startswith("refs/tags/"):
            if old != ZERO:
                problems.append("%s: moving a tag is refused" % ref)
        else:
            problems.append("%s: this witness keeps one branch (%s); other refs are refused" % (ref, branch))
    tip = new_tip or current
    for old, new, ref in updates:
        if ref.startswith("refs/tags/") and new != ZERO and old == ZERO:
            target = rev_parse(gp, new + "^{commit}")
            if not target or not tip or not is_ancestor(gp, target, tip):
                problems.append("%s: a tag must point to a commit in the witnessed history" % ref)
    checked = 0
    if new_tip and not problems:
        try:
            problems += check_history(gp, new_tip, allow_test)
            checked = len(git_text(gp, "rev-list", new_tip).split())
        except GitError as e:
            problems.append(str(e))
    def say(text):  # bytes with plain newlines: git relays them to the person pushing
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
    log_push(updates, problems, checked)
    if problems:
        say("WITNESS REFUSED THIS PUSH:\n" + "".join("  - %s\n" % p for p in problems)
            + "Nothing was changed in the witness.\n")
        return 1
    say("witness: accepted (%d commits checked from the first)\n" % checked)
    return 0


PUSH_LOG = "pushlog.jsonl"


def log_push(updates, problems, checked):
    """One line per push attempt, accepted or refused, in the witness folder (next to history.git): when, which
    refs moved from what to what, why it was refused, and the SHA-256 of the check that decided. A refused push
    is evidence too: someone tried, and the structure held."""
    try:
        git_dir = os.path.abspath(os.environ.get("GIT_DIR") or ".")
        folder = os.path.dirname(git_dir)
        rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               "result": "refused" if problems else "accepted",
               "updates": [{"ref": ref, "old": old, "new": new} for old, new, ref in updates],
               "reasons": problems, "commits_checked": checked,
               "check_sha256": sha256_file(os.path.abspath(__file__))}
        with open(os.path.join(folder, PUSH_LOG), "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass   # the log never decides a push; the check above does


def read_push_log(witness):
    """The witness's push log as a list of dicts (lines that are not valid JSON are skipped)."""
    out = []
    p = os.path.join(witness, PUSH_LOG)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


# ---------------------------------------------------------------- setup and verify

README = """This folder is the witness of the organization in the folder next to it.

It is kept outside the organization's folder so that the organization's
members (AI agents working in that folder) cannot reach it in ordinary work.
Do not open it in an agent app, and do not move it inside the organization.

  history.git/   a copy of the organization's history. It refuses rewrites,
                 deletions, and changes to records other than additions.
  snapshots/     dated copies of records/, kept when git is not available.
  drills/        your sealed drill descriptions (scripts/fos_drill.py).
  transcripts/   keep your agent app's transcripts here, if you keep them.
                 Members never load them; they are an independent account
                 of what happened, to check the records against.
"""


# Test-mode signatures (fos_close.py --test-answers) count only in the seed's own self-test. For a witness, whether it
# serves a self-test is fixed once, when it is set up (git config witness.testmode), and the check run on every push
# reads that setting, never the environment of whoever pushes: a member who sets SEED_SELFTEST=1 in its own shell and
# pushes a test-mode founding is refused, as it would be without the variable.
TEST_MODE_KEY, TEST_MODE_VALUE = "witness.testmode", "selftest"


def witness_test_mode(gp):
    code, out, _ = run_git(list(gp) + ["config", "--get", TEST_MODE_KEY])
    return code == 0 and out.decode("utf-8", "replace").strip() == TEST_MODE_VALUE


def hook_text(python):
    py = python.replace("\\", "/")
    return ("#!/bin/sh\n"
            "# Runs the witness check on every push. Installed by fos_witness.py setup.\n"
            "exec \"%s\" \"$(dirname \"$0\")/%s\" pre-receive\n" % (py, HOOK_SCRIPT))


def setup(witness, branch=DEFAULT_BRANCH):
    witness = os.path.abspath(witness)
    hist = os.path.join(witness, "history.git")
    if os.path.exists(hist):
        print("a witness already exists at %s" % hist)
        return 1
    os.makedirs(witness, exist_ok=True)
    code, _, err = run_git(["init", "--quiet", "--bare", "--initial-branch=" + branch, hist])
    if code != 0:
        print("could not create the witness repository: %s" % err.decode("utf-8", "replace"))
        return 1
    gp = ["--git-dir", hist]
    for key, value in (("receive.denyNonFastForwards", "true"), ("receive.denyDeletes", "true"),
                       ("receive.fsckObjects", "true"), ("core.logAllRefUpdates", "true"),
                       ("witness.branch", branch)):
        run_git(gp + ["config", key, value])
    if os.environ.get("SEED_SELFTEST") == "1":   # a witness made inside the seed's self-test; fixed here, for good
        run_git(gp + ["config", TEST_MODE_KEY, TEST_MODE_VALUE])
    hooks = os.path.join(hist, "hooks")
    os.makedirs(hooks, exist_ok=True)
    shutil.copyfile(os.path.abspath(__file__), os.path.join(hooks, HOOK_SCRIPT))
    hook = os.path.join(hooks, "pre-receive")
    with open(hook, "w", encoding="utf-8", newline="\n") as f:
        f.write(hook_text(sys.executable))
    os.chmod(hook, 0o755)
    for sub in ("snapshots", "drills", "transcripts"):
        os.makedirs(os.path.join(witness, sub), exist_ok=True)
    with open(os.path.join(witness, "README.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(README)
    print("witness created: %s" % hist)
    return 0


def sha256_file(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify(witness):
    """Return a dict describing the witness: settings, hook, and its history."""
    hist = os.path.join(os.path.abspath(witness), "history.git")
    rep = {"path": hist, "exists": os.path.isdir(hist), "settings_ok": False, "hook_ok": False,
           "hook_same_as_this_copy": False, "branch": None, "tip": None, "history_problems": []}
    if not rep["exists"]:
        return rep
    gp = ["--git-dir", hist]

    def cfg(key):
        code, out, _ = run_git(gp + ["config", "--get", key])
        return out.decode().strip() if code == 0 else ""
    rep["settings_ok"] = (cfg("core.bare") == "true" and cfg("receive.denyNonFastForwards") == "true"
                          and cfg("receive.denyDeletes") == "true")
    rep["branch"] = cfg("witness.branch") or DEFAULT_BRANCH
    hook = os.path.join(hist, "hooks", "pre-receive")
    script = os.path.join(hist, "hooks", HOOK_SCRIPT)
    rep["hook_ok"] = os.path.isfile(hook) and os.path.isfile(script)
    if os.path.isfile(script):
        rep["hook_same_as_this_copy"] = sha256_file(script) == sha256_file(os.path.abspath(__file__))
    rep["tip"] = rev_parse(gp, "refs/heads/" + rep["branch"])
    if rep["tip"]:
        try:
            rep["history_problems"] = check_history(gp, rep["tip"], witness_test_mode(gp))
        except GitError as e:
            rep["history_problems"] = [str(e)]
    return rep


def verify_cli(witness, as_json=False):
    rep = verify(witness)
    if as_json:
        print(json.dumps(rep))
    else:
        print("witness: %s" % rep["path"])
        print("  exists: %s; refuses rewrites and deletions: %s; check runs on every push: %s"
              % (rep["exists"], rep["settings_ok"], rep["hook_ok"]))
        if rep["hook_ok"] and not rep["hook_same_as_this_copy"]:
            print("  note: the witness's check differs from this folder's copy of fos_witness.py")
        print("  branch %s at %s" % (rep["branch"], (rep["tip"] or "no commits yet")[:12]))
        for p in rep["history_problems"]:
            print("  PROBLEM: " + p)
    ok = rep["exists"] and rep["settings_ok"] and rep["hook_ok"] and not rep["history_problems"]
    return 0 if ok else 1


# ---------------------------------------------------------------- folder witness (no git)

def record_files(org):
    d = os.path.join(org, "records")
    return sorted(f for f in os.listdir(d) if f.endswith(".jsonl")) if os.path.isdir(d) else []


def latest_snapshot(witness):
    d = os.path.join(witness, "snapshots")
    if not os.path.isdir(d):
        return None
    names = sorted(n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n)))
    return os.path.join(d, names[-1]) if names else None


BIRTH_COPY = ("org", "BIRTH.json")   # written once at birth; the dated copies keep it too


def compare_with_snapshot(org, snap):
    """Problems if any file in the snapshot is missing now or no longer starts with its old content."""
    problems = []
    kept_birth = os.path.join(snap, BIRTH_COPY[1])
    if os.path.exists(kept_birth):
        cur = os.path.join(org, *BIRTH_COPY)
        with open(kept_birth, "rb") as f:
            old = f.read().replace(b"\r\n", b"\n")
        if not os.path.exists(cur):
            problems.append("%s is missing; the witness holds a copy" % "/".join(BIRTH_COPY))
        else:
            with open(cur, "rb") as f:
                if f.read().replace(b"\r\n", b"\n") != old:
                    problems.append("%s was changed since birth; the witness holds the original" % "/".join(BIRTH_COPY))
    for name in sorted(os.listdir(snap)):
        if not name.endswith(".jsonl"):
            continue
        cur = os.path.join(org, "records", name)
        if not os.path.exists(cur):
            problems.append("records/%s is missing; the witness holds a copy" % name)
            continue
        with open(os.path.join(snap, name), "rb") as f:
            old = f.read()
        with open(cur, "rb") as f:
            new = f.read().replace(b"\r\n", b"\n")
        if not is_append(old.replace(b"\r\n", b"\n"), new):
            problems.append("records/%s: earlier lines were changed or removed since the last snapshot" % name)
    return problems


def snapshot(org, witness):
    org, witness = os.path.abspath(org), os.path.abspath(witness)
    prev = latest_snapshot(witness)
    if prev:
        problems = compare_with_snapshot(org, prev)
        if problems:
            print("snapshot refused; the records do not extend the last snapshot:")
            for p in problems:
                print("  - " + p)
            return 1
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    dest = os.path.join(witness, "snapshots", stamp)
    n = 1
    while os.path.exists(dest):   # two snapshots in the same instant still get distinct, ordered names
        n += 1
        dest = os.path.join(witness, "snapshots", "%s-%d" % (stamp, n))
    os.makedirs(dest)
    manifest = {"created": stamp, "files": {}}
    for name in record_files(org):
        src = os.path.join(org, "records", name)
        with open(src, "rb") as f:
            data = f.read().replace(b"\r\n", b"\n")
        with open(os.path.join(dest, name), "wb") as f:
            f.write(data)
        manifest["files"][name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                                   "lines": data.count(b"\n")}
    birth = os.path.join(org, *BIRTH_COPY)
    if os.path.exists(birth):
        with open(birth, "rb") as f:
            data = f.read().replace(b"\r\n", b"\n")
        with open(os.path.join(dest, BIRTH_COPY[1]), "wb") as f:
            f.write(data)
        manifest["files"][BIRTH_COPY[1]] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    print("snapshot written: %s" % dest)
    return 0


def check_snapshot(org, witness):
    prev = latest_snapshot(os.path.abspath(witness))
    if not prev:
        print("no snapshot yet")
        return 0
    problems = compare_with_snapshot(os.path.abspath(org), prev)
    for p in problems:
        print("PROBLEM: " + p)
    if not problems:
        print("records extend the last snapshot (%s)" % os.path.basename(prev))
    return 1 if problems else 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "pre-receive":
        return pre_receive()
    if len(argv) >= 3 and argv[1] == "setup":
        branch = argv[argv.index("--branch") + 1] if "--branch" in argv else DEFAULT_BRANCH
        return setup(argv[2], branch)
    if len(argv) >= 3 and argv[1] == "verify":
        return verify_cli(argv[2], "--json" in argv)
    if len(argv) >= 3 and argv[1] == "check-history":
        rev = argv[3] if len(argv) > 3 else "HEAD"
        problems = check_history(["-C", argv[2]], rev)
        for p in problems:
            print("PROBLEM: " + p)
        print("history: %s" % ("clean" if not problems else "%d problems" % len(problems)))
        return 1 if problems else 0
    if len(argv) >= 4 and argv[1] == "snapshot":
        return snapshot(argv[2], argv[3])
    if len(argv) >= 4 and argv[1] == "check-snapshot":
        return check_snapshot(argv[2], argv[3])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
