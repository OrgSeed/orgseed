"""Self-test: run the seed's integrity claims on throwaway copies, and report what held.

Usage:  python scripts/fos_selftest.py [--keep] [--json [<results.json>]]

It copies this folder's files (as they are on disk, without .git and without ignored files) into
a new temporary folder, makes that copy a seed repository, and from it births organizations with
scripts/fos_init.py. Then it plays the parts a member and a founder play, including members who
break the rules, and checks the outcome on disk each time:
  - the founding comes first (these cases run first), as one invariant on files and history: only the founder's FOUND
    at the close-out founds the organization, and it is committed on its own before any structure; without it, no
    structure is committed, and a commit that holds it is refused by the witness and failed by the check, whatever the
    decisions are called (among them: a later founding that corrects a deferred or unsigned one, decisions of
    kind other, items re-pointed to another decision, seed-labelled items edited in place, a key written twice in
    config.json); a signature is written only from the close-out's own run, the witness takes test mode from its
    own setting, and the founding prompt shows every structural change from birth;
  - birth: the first commit's tree equals the seed's tree (the birth hash); the witness exists;
  - a session written through fos_log; generic replies and unnamed proposals flagged;
  - the close-out refuses to run without a terminal; in test mode it signs, commits and pushes;
  - a malformed line is a failure until a record_correction points to it;
  - the witness refuses a records file deleted in a commit, an earlier line edited in a commit,
    a rewritten history (force push), a second branch, and deleting its branch;
  - the check sees a local history rewrite; the close-out refuses to commit over it;
  - the close-out restores a deleted file and an edited line, keeping newer records;
  - a forged signature line does not count and is voided at the next close-out;
  - structure switched on with no decision is PROPOSAL-ONLY; an ungoverned tool folder is flagged;
  - an enforcement add-on that refused a write is declared in the tool registry, with what it covers; a change to
    an add-on shipped with the seed is reported like a change to its scripts;
  - proposals for change: welcome from any member, in a form the founder can judge (warned when a decision
    adopts structure without a plain-language effect or an undo, or rests on a work marked read and not saved);
    a trial adoption (DR-9) in the rules in force;
  - a launch records the hashes of the agent app's own instruction files, never their content;
  - drills: sealed when planted, verified when revealed, a tampered description caught;
  - export: the bundle verifies, clones, and passes the check in its new place;
  - the view: no scripts, a content-security policy, escaped text, identical when redrawn;
  - without git: birth, dated copies in the witness folder, a deletion caught and restored;
  - rename: the name changes everywhere and the scripts still run;
  - release: the seed's last tree, byte for byte, as one commit by a neutral identity at a fixed UTC
    date, with no history, remote or ignored file; the same inputs give the same commit; planted
    identifying strings are each caught and nothing is committed.
Nothing outside the temporary folder is touched; it is deleted at the end unless --keep is given.
Test signatures are marked as such and count only inside this self-test.
Standard library only; no network.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402
import fos_init  # noqa: E402

RESULTS = []
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SEED_SELFTEST="1", GIT_CONFIG_NOSYSTEM="1")
PY = sys.executable


def run(args, cwd, env=None, data=None, stdin=None):
    r = subprocess.run(args, cwd=cwd, env=env or ENV, input=data, stdin=stdin, capture_output=True)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")


def py(org, script, *args, env=None, data=None, stdin=None):
    return run([PY, os.path.join(org, "scripts", script)] + list(args), org, env=env, data=data, stdin=stdin)


def git(org, *args, env=None):
    return run(["git", "-C", org] + list(args), org, env=env)


def ok(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    d = (detail or "").strip()
    if len(d) > 900:
        d = d[:300] + "\n  ...\n" + d[-600:]
    print("  %s  %s%s" % ("PASS" if cond else "FAIL", name, ("  [" + d + "]") if d and not cond else ""))
    return cond


def log(org, kind, rec):
    return py(org, "fos_log.py", kind, "--json", "-", data=json.dumps(rec).encode("utf-8"))


def lines(org, rel):
    with open(os.path.join(org, *rel.split("/")), encoding="utf-8") as f:
        return [ln for ln in f.read().splitlines() if ln.strip()]


def objs(org, rel):
    out = []
    for x in lines(org, rel):
        try:
            out.append(json.loads(x))
        except ValueError:
            pass   # a malformed line kept on purpose (and corrected) by an earlier scenario
    return out


def write(org, rel, text, mode="w"):
    p = os.path.join(org, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, mode, encoding="utf-8", newline="\n") as f:
        f.write(text)


def set_module(org, mid, state, adopted_by):
    p = os.path.join(org, "org", "config.json")
    with open(p, encoding="utf-8") as f:
        c = json.load(f)
    for m in c["modules"]:
        if m["id"] == mid:
            m.update(state=state, adopted_by=adopted_by)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(c, f, indent=2)
        f.write("\n")


def rmtree(p):
    def onerror(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    shutil.rmtree(p, onerror=onerror)


def make_seed(tmp):
    seed = os.path.join(tmp, "seed")
    os.makedirs(seed)
    code, out = L.git("ls-files", "-co", "--exclude-standard")
    rels = [x for x in out.splitlines() if x.strip()] if code == 0 else list(fos_init.files_without_git())
    for rel in rels:
        src = L.path(rel)
        if os.path.isfile(src):
            dst = os.path.join(seed, *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as f:
                data = L.canonical_bytes(rel, f.read())    # LF, and CRLF for the Windows launchers
            with open(dst, "wb") as f:
                f.write(data)
    git(seed, "init", "-q", "--initial-branch=main")
    git(seed, "config", "user.name", "selftest")
    git(seed, "config", "user.email", "")
    git(seed, "config", "core.autocrlf", "false")
    git(seed, "add", "-A")
    code, staged = L.git("ls-files", "-s")                  # keep the seed's file modes (the macOS launchers: 100755)
    exe = {ln.split("\t", 1)[1] for ln in staged.splitlines() if ln.startswith("100755 ")} if code == 0 else set()
    exe |= {rel for rel in rels if L.is_executable_path(rel)}
    exe = sorted(x for x in exe if os.path.isfile(os.path.join(seed, *x.split("/"))))
    if exe:
        git(seed, "update-index", "--chmod=+x", "--", *exe)
    git(seed, "commit", "-q", "-m", "[SEED] self-test copy",
        "-m", "[BIRTH] written at the start of a message body line must not make the seed look born.")
    return seed


# ---------------------------------------------------------------- scenarios

def t_birth(seed, org):
    print("Birth")
    code, out = py(seed, "fos_init.py", org)
    ok("fos_init creates the organization", code == 0, out)
    out_init = out
    s_tree = git(seed, "rev-parse", "HEAD^{tree}")[1].strip()
    root = git(org, "rev-list", "--max-parents=0", "HEAD")[1].strip()
    o_tree = git(org, "rev-parse", root + "^{tree}")[1].strip()
    ok("birth hash: the first commit's tree equals the seed's tree", s_tree and s_tree == o_tree, "%s vs %s" % (s_tree, o_tree))
    born = [x for x in objs(org, "records/events.jsonl") if x.get("type") == "born"]
    ok("the birth record names that tree", born and born[0]["seed"]["tree"] == s_tree)
    bf = os.path.join(org, "org", "BIRTH.json")
    ok("org/BIRTH.json holds the same birth", os.path.exists(bf)
       and json.load(open(bf, encoding="utf-8"))["seed"]["tree"] == s_tree)
    code, out = py(seed, "fos_check.py")
    ok("the seed itself is still the seed (no birth in its history)", "stage: seed" in out, out)
    s_commit = git(seed, "rev-parse", "--short", "HEAD")[1].strip()
    ok("the seed's check names its commit and the tree an organization born from it gets as its birth hash, the one "
       "fos_init prints", "at commit %s, seed tree %s" % (s_commit, s_tree) in out
       and "birth hash (seed tree): %s" % s_tree in out_init, out)
    ok("the witness exists outside the folder", os.path.isdir(org + "-witness/history.git"))
    code, out = py(org, "fos_check.py")
    ok("fos_check passes on a new organization", code == 0 and "Result: OK" in out, out)
    code, out = py(org, "fos_check.py", env=dict(ENV, SEED_NO_GIT="1"))
    ok("where git cannot start (some sandboxes), the witness is still found and not called missing",
       code == 0 and "UNWITNESSED" not in out and "found without git" in out and "stage: born" in out, out)


def t_init_atomic(tmp, seed):
    print("Birth is all or nothing, and paths too long for the machine are refused first")
    target = os.path.join(tmp, "half")
    code, out = py(seed, "fos_init.py", target, env=dict(ENV, SEED_INIT_FAIL="1"))
    ok("a birth that fails part-way leaves no organization and no witness behind",
       code == 1 and not os.path.exists(target) and not os.path.exists(target + "-witness")
       and "Nothing was created" in out, out)
    if fos_init.long_paths_enabled():
        ok("(long paths are switched on here, so the path-length refusal is not exercised)", True)
        return
    deep = os.path.join(tmp, "p" * max(10, 250 - len(tmp)))
    code, out = py(seed, "fos_init.py", deep)
    ok("a folder whose paths would be too long is refused before anything is created",
       code == 1 and "too long" in out and not os.path.exists(deep) and not os.path.exists(deep + "-witness"), out)


def read(org, rel):
    with open(os.path.join(org, *rel.split("/")), encoding="utf-8") as f:
        return f.read()


def drop(org):
    for p in (org, org + "-witness"):
        if os.path.exists(p):
            rmtree(p)


def t_continuity(tmp, seed):
    print("Every later session starts from what the last one left, founded or not")
    org = os.path.join(tmp, "cont-org")
    py(seed, "fos_init.py", org)
    code, out = py(org, "fos_check.py")
    ok("before any session, the check sends a new member to the first session",
       "next, for a member opening a new session: onboarding/START.md" in out, out)
    log(org, "event", {"type": "session_start", "summary": "First session"})
    log(org, "decision", {"question": "Which framing do you pursue first: the records or the meetings?",
                          "proposal_ids": [], "framed_by": "member-1", "decided_by": "founder",
                          "decider_kind": "human", "right": "founder", "verdict": "adopted",
                          "words": "The records framing, please."})
    write(org, "org/LETTER_TO_NEXT_SESSION.md", "# Letter to the next session\n\nNot founded yet: we stopped at step 7, "
                                                "before the founding decision. The founder chose the records framing.\n")
    log(org, "event", {"type": "session_end", "summary": "Stopped before the founding"})
    code, out = py(org, "fos_close.py", "--test-answers", "y,y")
    cfg = json.loads(read(org, "org/config.json"))
    ok("a first session that stopped before the founding is closed out, and the organization is not founded",
       code == 0 and not cfg["organization"]["founded"], out)
    code, out = py(org, "fos_check.py")
    ok("the next member is sent to session start, not to the first session again, and told the founding is unfinished",
       "next, for a member opening a new session: onboarding/SESSION_START.md" in out and "not founded yet" in out, out)
    code, out = py(org, "fos_check.py", "--resume")
    ok("fos_check --resume prints the letter, the state and each signed decision with the founder's words",
       code == 0 and "we stopped at step 7" in out and "# Current state" in out and "D-0001" in out
       and "The records framing, please." in out and out.index("we stopped") < out.index("D-0001"), out)
    agents, ss = read(org, "AGENTS.md"), read(org, "onboarding/SESSION_START.md")
    ok("AGENTS.md sends a member by the sessions on record, whatever 'founded' says",
       "No session before this one is on record" in agents and "whether or not `founded` is `true`" in agents)
    first = ss.split("\n## ")[1]
    ok("SESSION_START's first step reads the letter, the state and the signed decisions, and does not restart the "
       "first session in an organization not yet founded",
       first.startswith("1. Read what the last session left") and "LETTER_TO_NEXT_SESSION.md" in first
       and "org/STATE.md" in first and '"answer": "signed"' in first and "Do not start the first session again" in first)
    drop(org)


def t_founding_first(tmp, seed):
    print("The founding is a close-out step: only the founder's FOUND founds the organization")
    org = os.path.join(tmp, "found-org")
    first_session(seed, org, ("memory", "charter"))
    decide(org, "Do you found the organization on this charter and adopt P-0001 and P-0002?", ["P-0001", "P-0002"],
           words="Yes: found it, with P-0001 and P-0002 adopted.", founding=True)
    set_module(org, "memory", "on", "D-0001")
    set_module(org, "charter", "on", "D-0001")
    write(org, "org/CHARTER.md", CHARTER % "D-0001")
    code, out = py(org, "fos_check.py")
    ok("the member prepares the charter: before the close-out the organization is born, not founded, and the check "
       "notes the structure prepared for the founding without failing it",
       code == 0 and "stage: born" in out and "structure prepared for the founding" in out
       and "org/config.json (modules)" in out and "org/CHARTER.md (added)" in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "FOUND,y")
    i_found, i_commit = out.find(FOUND_PROMPT), out.find("Committed")
    ok("the close-out asks the founding first, on its own, showing the structure prepared for it, and the founder "
       "types FOUND", code == 0 and 0 <= out.find("The founding (asked first, on its own)") < i_found < i_commit
       and "If you found it: the organization is founded on this charter" in out, out)
    subjects = git(org, "log", "--reverse", "--format=%s")[1].splitlines()
    first = git(org, "show", "--name-only", "--format=", "HEAD~1")[1].split()
    rest = git(org, "show", "--name-only", "--format=", "HEAD")[1].split()
    ok("the founding is committed on its own, records only, and the structure in the commit after it",
       len(subjects) == 4 and subjects[2].startswith("[FOUND] S001: the founder founded the organization on D-0001")
       and subjects[3].startswith("[CLOSE]") and first and all(p.startswith("records/") for p in first)
       and "org/config.json" in rest and "org/CHARTER.md" in rest, "%s\n%s\n%s" % (subjects, first, rest))
    sig = objs(org, "records/signatures.jsonl")[-1]
    cfg = json.loads(read(org, "org/config.json"))["organization"]
    ok("its signature records the word the founder typed, and the close-out writes the founding into config.json",
       sig.get("founding") == "FOUND" and sig.get("decision_id") == "D-0001" and sig.get("answer") == "signed"
       and cfg.get("founded") is True and cfg.get("founding_decision") == "D-0001" and cfg.get("founded_on"),
       json.dumps(sig)[:300] + json.dumps(cfg))
    wtip = run(["git", "--git-dir", org + "-witness/history.git", "rev-parse", "main"], org)[1].strip()
    code, out = py(org, "fos_check.py")
    ok("the witness accepts both commits, and the check reads the founding from the history",
       wtip == git(org, "rev-parse", "HEAD")[1].strip() and code == 0 and "stage: founded" in out
       and "founded: the founder typed FOUND for D-0001" in out, out)
    no_test = dict(ENV)
    no_test.pop("SEED_SELFTEST")
    code, out = py(org, "fos_check.py", env=no_test)
    ok("a founding signed in test mode founds nothing outside the self-test: there, the structure after it fails",
       code == 1 and "STRUCTURE BEFORE FOUNDING" in out and "stage: born" in out, out)
    start, agents = read(org, "onboarding/START.md"), read(org, "AGENTS.md")
    session, close = read(org, "onboarding/SESSION_START.md"), read(org, "onboarding/CLOSE_OUT.md")
    ok("START, SESSION_START, CLOSE_OUT and CORE-2 say it: the member prepares the charter, and the founder founds the "
       "organization at the close-out by typing FOUND",
       "do not ask the founder to adopt it on its own" in start and "It is the organization's first decision" in start
       and "Do not set `founded` in `org/config.json` yourself" in start
       and "the founder founds the organization at the close-out, by reading the founding decision" in start
       and "ask for no adoption but the founding decision" in agents
       and "Only the founder founds it, by typing FOUND at the close-out" in agents
       and "until the founder types FOUND at a close-out" in session and "type FOUND, in capitals" in close)
    drop(org)


def first_session(seed, org, targets):
    """A new organization, its first session opened, and one module proposal per target (P-0001, P-0002 ...)."""
    py(seed, "fos_init.py", org)
    log(org, "event", {"type": "session_start", "summary": "First session"})
    for target in targets:
        log(org, "proposal", {"kind": "module", "target": target, "change": "Switch on the %s module" % target,
                              "why": "The founder chose it", "proposed_by": "member-1"})


def decide(org, question, pids, verdict="adopted", words="Yes, I adopt them.", **extra):
    """A decision the founder took, recorded by member-1 with the question and the reply."""
    rec = {"question": question, "proposal_ids": pids, "framed_by": "member-1", "decided_by": "founder",
           "decider_kind": "human", "right": "founder", "verdict": verdict, "words": words}
    rec.update(extra)
    return log(org, "decision", rec)


WEEKLY_RULE = ("\n### OUR-1 Close each week with a note\nrule: On the last working day of each week, a member writes a "
               "short note of what was done.\nwhy: one page read each week keeps the whole in view.\nadopted_by: %s\n")


def add_weekly_rule(org, pid, did):
    """A proposal of kind other (P-...), its decision, and the rule it adds to org/OUR_RULES.md, adopted by that decision."""
    log(org, "proposal", {"kind": "other", "target": "org/OUR_RULES.md", "change": "Add OUR-1: a note at the end of "
                          "each week", "why": "The founder asked for it", "proposed_by": "member-1"})
    decide(org, "Do you adopt %s (a note at the end of each week)?" % pid, [pid], words="Yes, I adopt %s." % pid)
    write(org, "org/OUR_RULES.md", WEEKLY_RULE % did, mode="a")


def member_commit(org, message="[CLOSE] S001: committed by a member"):
    """A member commits the folder as it is, by hand, and pushes it to the witness: (push exit code, its output)."""
    git(org, "add", "-A")
    git(org, "-c", "user.name=a member", "-c", "user.email=", "commit", "-q", "-m", message)
    return git(org, "push", "witness", "main")


def committed_since_birth(org, *rels):
    """Those of the structural files given whose structure, as HEAD holds them, differs from the first commit's (the
    organization block of config.json and the model slots aside, as the invariant has it)."""
    W = L.W
    root = git(org, "rev-list", "--max-parents=0", "HEAD")[1].strip()
    diffs = W.structure_differences(W.structure_at(["-C", org], root), W.structure_at(["-C", org], "HEAD"))
    return [rel for rel, _ in diffs if rel in rels]


def must_fail(org, label):
    """The invariant's two guards on a commit that holds structure before the founding: the witness refuses the push,
    and the check fails the history. Returns (passed, what they said)."""
    code_p, out_p = member_commit(org)
    code_c, out_c = py(org, "fos_check.py")
    passed = (code_p != 0 and "STRUCTURE BEFORE FOUNDING" in out_p and code_c == 1
              and "history: STRUCTURE BEFORE FOUNDING" in out_c)
    ok("%s: committed by hand, the witness refuses it and the check fails it (STRUCTURE BEFORE FOUNDING)" % label,
       passed, out_p + out_c)
    return passed


CHARTER = ("# Charter\n\n### NG-1 Learn the field\ngoal: map the sources\nkind: learn\ndone_when: ten sources saved\n"
           "adopted_by: %s\n")
FOUND_PROMPT = "Found the organization now on this charter? (type FOUND)"


def t_founding_void(tmp, seed):
    print("No FOUND, no founding: structure stays uncommitted, and a commit that holds it fails")
    org = os.path.join(tmp, "void-y")
    first_session(seed, org, ("memory", "charter"))
    decide(org, "Do you found the organization on this charter and adopt P-0001 and P-0002?", ["P-0001", "P-0002"],
           words="Yes: found it.", founding=True)
    set_module(org, "memory", "on", "D-0001")
    write(org, "org/CHARTER.md", CHARTER % "D-0001")
    code, out = py(org, "fos_close.py", "--test-answers", "y,n,y")
    body = git(org, "log", "-1", "--format=%B")[1]
    ok("a plan answering y at the founding prompt does not found the organization: the founding is not signed, and the "
       "structure prepared for it stays in the folder, uncommitted",
       code == 0 and FOUND_PROMPT in out and "stage: born" in py(org, "fos_check.py")[1]
       and "Not-signed: D-0001" in body and "Held until the founding (structure, not founded yet): org/config.json, "
       "org/CHARTER.md" in body and not committed_since_birth(org, "org/config.json", "org/CHARTER.md")
       and json.loads(read(org, "org/config.json"))["modules"][3]["state"] == "on", out + body)
    code, out = py(org, "fos_check.py")
    ok("the held files are not taken for a member's unrecorded work", "SESSION NOT RECORDED" not in out, out)
    must_fail(org, "the prepared structure")
    code, out = py(org, "fos_sync.py", "--test-answers", "y")
    code2, out2 = py(org, "fos_check.py")
    ok("a sync returns the folder to the witness and keeps the prepared structure in it, uncommitted",
       code == 0 and "history: STRUCTURE BEFORE FOUNDING" not in out2
       and json.loads(read(org, "org/config.json"))["modules"][3]["state"] == "on"
       and not committed_since_birth(org, "org/config.json"), out + out2)
    drop(org)
    for verdict, words, answers in (("deferred", "Not yet: I want to read the charter again first.", "y,y"),
                                    ("declined", "No, I do not found it on this charter.", "y,y")):
        org = os.path.join(tmp, "void-" + verdict)
        first_session(seed, org, ("memory", "charter"))
        decide(org, "Do you found the organization on this charter and adopt P-0001 and P-0002?", ["P-0001", "P-0002"],
               verdict, words, founding=True)
        decide(org, "Do you adopt P-0001 (switch on the memory module)?", ["P-0001"], words="Yes, I adopt P-0001.")
        set_module(org, "memory", "on", "D-0002")
        code, out = py(org, "fos_close.py", "--test-answers", answers)
        body = git(org, "log", "-1", "--format=%B")[1]
        ok("a founding that is %s is not offered for founding; the adoption after it is not asked, and its module "
           "stays uncommitted" % verdict,
           code == 0 and FOUND_PROMPT not in out and "D-0001 is recorded as the founding, but its verdict is %s" % verdict
           in out and "Not asked: D-0002 adopts structure" in out and "Not-asked: D-0002" in body
           and not committed_since_birth(org, "org/config.json") and "stage: born" in py(org, "fos_check.py")[1],
           out + body)
        drop(org)


def t_founding_backdating(tmp, seed):
    print("A later founding that corrects a deferred or unsigned one founds nothing")
    org = os.path.join(tmp, "back-deferred")
    first_session(seed, org, ("memory", "charter"))
    decide(org, "Do you found the organization on this charter and adopt P-0001 and P-0002?", ["P-0001", "P-0002"],
           "deferred", "Not yet.", founding=True)
    decide(org, "Do you adopt P-0001 (switch on the memory module)?", ["P-0001"], words="Yes, I adopt P-0001.")
    set_module(org, "memory", "on", "D-0002")
    decide(org, "Do you found the organization on this charter and adopt P-0002?", ["P-0002"],
           words="Yes: found it, with P-0002.", founding=True, corrects="D-0001")
    edit_config(org, lambda c: c["organization"].update(founded=True, founded_on="2026-10-14", founding_decision="D-0003"))
    set_module(org, "charter", "on", "D-0003")
    code, out = py(org, "fos_check.py")
    ok("records and config.json that call the organization founded do not found it: the check says it is not, and "
       "names the early adoption as a warning",
       code == 0 and "stage: born" in out and "org/config.json says the organization is founded, but no close-out "
       "founded it" in out and "D-0002: adopts P-0001, module 'memory' while the organization is not founded" in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "y,y,y,y,y")
    ok("a close-out answered y to every prompt founds nothing and commits no structure: the module adopted before the "
       "founding is not asked",
       code == 0 and FOUND_PROMPT in out and "Not asked: D-0002 adopts structure" in out
       and not committed_since_birth(org, "org/config.json") and "stage: born" in py(org, "fos_check.py")[1]
       and json.loads(read(org, "org/config.json"))["organization"]["founded"] is False, out)
    must_fail(org, "a founding that corrects a deferred one")
    drop(org)
    org = os.path.join(tmp, "back-refused")
    first_session(seed, org, ("charter", "memory"))
    decide(org, "Do you found the organization on this charter and adopt P-0001?", ["P-0001"],
           words="Yes: found it, with P-0001.", founding=True)
    set_module(org, "charter", "on", "D-0001")
    decide(org, "Do you adopt P-0002 (switch on the memory module)?", ["P-0002"], words="Yes, I adopt P-0002.")
    set_module(org, "memory", "on", "D-0002")
    code, out = py(org, "fos_close.py", "--test-answers", "n,n,y")
    ok("the founder answers n at the founding prompt: the founding is not signed, and the adoption after it waits",
       code == 0 and "Not asked: D-0002 adopts structure" in out
       and [s["answer"] for s in objs(org, "records/signatures.jsonl")] == ["refused"], out)
    log(org, "event", {"type": "session_start", "summary": "The next session"})
    decide(org, "Do you found the organization on this charter and adopt P-0001?", ["P-0001"],
           words="Yes: found it, with P-0001.", founding=True, corrects="D-0001")
    edit_config(org, lambda c: c["organization"].update(founded=True, founding_decision="D-0003"))
    code, out = py(org, "fos_check.py")
    ok("recorded again with corrects, the refused founding still founds nothing", "stage: born" in out, out)
    must_fail(org, "a founding that corrects one the founder did not sign")
    drop(org)


def t_founding_labels(tmp, seed):
    print("What decisions are called, or which decision an item names, founds nothing")
    org = os.path.join(tmp, "kind-org")
    first_session(seed, org, ())
    log(org, "proposal", {"kind": "other", "target": "memory", "change": "Keep the founder's rulings",
                          "why": "The founder asked for it", "proposed_by": "member-1"})
    decide(org, "Do you adopt P-0001 (keep the founder's rulings)?", ["P-0001"], words="Yes, I adopt P-0001.")
    set_module(org, "memory", "on", "D-0001")
    add_weekly_rule(org, "P-0002", "D-0002")
    code, out = py(org, "fos_check.py")
    ok("decisions of kind 'other' that switch a module on and add a rule before the founding are named, as warnings "
       "only", code == 0 and "D-0001: adopts module 'memory' while the organization is not founded" in out
       and "D-0002: adopts OUR-1 Close each week with a note (org/OUR_RULES.md)" in out, out)
    log(org, "proposal", {"kind": "module", "target": "charter", "change": "Switch on the charter module",
                          "why": "The founder chose it", "proposed_by": "member-1"})
    decide(org, "Do you found the organization on this charter and adopt P-0003?", ["P-0003"],
           words="Yes: found it, with P-0003.", founding=True)
    set_module(org, "memory", "on", "D-0003")
    write(org, "org/OUR_RULES.md", read(org, "org/OUR_RULES.md").replace("adopted_by: D-0002", "adopted_by: D-0003"))
    edit_config(org, lambda c: c["organization"].update(founded=True, founded_on="2026-10-14", founding_decision="D-0003"))
    code, out = py(org, "fos_close.py", "--test-answers", "y,y,y,y")
    ok("re-pointed to the founding decision, the module and the rule are still not committed: a close-out answered y "
       "throughout founds nothing",
       code == 0 and FOUND_PROMPT in out and not committed_since_birth(org, "org/config.json", "org/OUR_RULES.md")
       and "stage: born" in py(org, "fos_check.py")[1], out)
    must_fail(org, "a kind-'other' module and rule, re-pointed to the founding decision")
    drop(org)
    org = os.path.join(tmp, "stand-in-org")
    first_session(seed, org, ())
    log(org, "proposal", {"kind": "other", "target": "org/GOAL.md", "change": "Our founding goal, in your words",
                          "why": "The founder said it", "proposed_by": "member-1"})
    decide(org, "Do you adopt P-0001 (our founding goal, in your words)?", ["P-0001"], words="Yes, I adopt P-0001.",
           founding=True)
    log(org, "proposal", {"kind": "module", "target": "memory", "change": "Switch on the memory module",
                          "why": "The founder chose it", "proposed_by": "member-1"})
    decide(org, "Before the founding, do you adopt P-0002 (switch on the memory module, as found in modules/memory)?",
           ["P-0002"], words="Yes, I adopt P-0002.")
    set_module(org, "memory", "on", "D-0002")
    code, out = py(org, "fos_close.py", "--test-answers", "y,y,y")
    ok("a founding stand-in that changes nothing, then a module: the close-out still asks for FOUND, and a y founds "
       "nothing and commits no module", code == 0 and FOUND_PROMPT in out and "Not asked: D-0002" in out
       and not committed_since_birth(org, "org/config.json"), out)
    drop(org)
    org = os.path.join(tmp, "seedlabel-org")
    py(seed, "fos_init.py", org)
    log(org, "event", {"type": "session_start", "summary": "First session"})

    def edits(c):
        member = c["roles"][1]
        member["purpose"] = "Checks claims"
        c["roles"].append(dict(member, purpose="A second role under the seed's own label"))
        c["settings"]["rule_reasons"] = "hidden"
        c["decision_rights"]["reserved_to_founder"] = c["decision_rights"]["reserved_to_founder"][:2]
    edit_config(org, edits)
    views = json.loads(read(org, "view/VIEWS.json"))
    views["panels"] = views["panels"][2:]
    write(org, "view/VIEWS.json", json.dumps(views, indent=1) + "\n")
    code, out = py(org, "fos_close.py", "--test-answers", "y,y,y")
    body = git(org, "log", "-1", "--format=%B")[1]
    ok("seed-labelled items edited in place, with no decision at all (a role's purpose, a second role, settings, the "
       "founder's reserved rights, the view's panels): the close-out commits none of it",
       code == 0 and "Held until the founding (structure, not founded yet): org/config.json, view/VIEWS.json" in body
       and not committed_since_birth(org, "org/config.json", "view/VIEWS.json"), out + body)
    must_fail(org, "seed-labelled items edited in place")
    drop(org)
    org = os.path.join(tmp, "late-org")
    first_session(seed, org, ("memory", "charter"))
    decide(org, "Do you adopt P-0001 (switch on the memory module)?", ["P-0001"], words="Yes, I adopt P-0001.")
    set_module(org, "memory", "on", "D-0001")
    decide(org, "Do you found the organization on this charter and adopt P-0002?", ["P-0002"],
           words="Yes: found it, with P-0002.", founding=True)
    set_module(org, "charter", "on", "D-0002")
    code, out = py(org, "fos_close.py", "--test-answers", "FOUND,y,y")
    code, out = py(org, "fos_check.py")
    ok("an adoption recorded before the founding decision, once the founder has founded the organization and signed "
       "it, is a warning only: the check passes", code == 0 and "stage: founded" in out
       and "D-0001: adopts P-0001, module 'memory' before the founding decision D-0002" in out, out)
    drop(org)


SIGN_BY_IMPORT = ("import sys; sys.path.insert(0, 'scripts'); import fos_lib as L, fos_close as F\n"
                  "cfg = L.config(); _, raw, d = L.read_records(L.RECORD_FILES['decision']).rows[-1]\n"
                  "try:\n    F.record_answer(cfg, raw, d, 'y', None, 'shown', {}, 'S001', founding=True)\n"
                  "except L.RecordError as e:\n    print('refused: %s' % e)\n"
                  "try:\n    L.append_record('signature', {'decision_id': d['id'], 'answer': 'signed', 'mode': 'terminal', "
                  "'signer': 'founder', 'captured_by': 'close_script', 'founding': 'FOUND'}, writer='fos_close')\n"
                  "except L.RecordError as e:\n    print('refused: %s' % e)\n")


def prepare_founding(seed, org, env=None):
    """A new organization (born with env, when given), its founding decision recorded and its structure prepared."""
    py(seed, "fos_init.py", org, env=env)
    log(org, "event", {"type": "session_start", "summary": "First session"})
    for target in ("memory", "charter"):
        log(org, "proposal", {"kind": "module", "target": target, "change": "Switch on the %s module" % target,
                              "why": "The founder chose it", "proposed_by": "member-1"})
    decide(org, "Do you found the organization on this charter and adopt P-0001 and P-0002?", ["P-0001", "P-0002"],
           words="Yes: found it.", founding=True)
    set_module(org, "memory", "on", "D-0001")
    write(org, "org/CHARTER.md", CHARTER % "D-0001")


def t_founding_guards(tmp, seed):
    print("What a founding rests on: one reading of each file, a signature only from the close-out, the founder sees "
          "every change")
    org = os.path.join(tmp, "twice-org")
    py(seed, "fos_init.py", org)
    log(org, "event", {"type": "session_start", "summary": "First session"})
    text = read(org, "org/config.json")
    cfg = json.loads(text)
    on = [dict(m, state="on", adopted_by="D-0001") if m["id"] == "memory" else m for m in cfg["modules"]]
    i = text.index('"modules"')
    write(org, "org/config.json", text[:i] + '"modules": ' + json.dumps(on) + ',\n  ' + text[i:])
    code, out = py(org, "fos_check.py")
    ok("a key written twice in config.json (the first copy switches a module on, the last is the birth's) fails the "
       "check in plain words, and counts as structure changed from birth",
       code == 1 and 'org/config.json: the key "modules" is written twice in one object, so the file says two things'
       in out and "structure prepared for the founding" in out, out)
    must_fail(org, "a key written twice in config.json")
    drop(org)
    org = os.path.join(tmp, "import-org")
    prepare_founding(seed, org)
    code, out = run([PY, "-c", SIGN_BY_IMPORT], org)
    ok("a member's script that imports the close-out and calls its signing function, or writes a signature through "
       "the records writer, is refused: nothing is signed",
       out.count("refused: a signature is written only by the founder's close-out") == 2
       and not lines(org, "records/signatures.jsonl"), out)
    drop(org)
    org = os.path.join(tmp, "testmode-org")
    real = dict(ENV)
    real.pop("SEED_SELFTEST")
    prepare_founding(seed, org, env=real)
    code, out = py(org, "fos_close.py", "--test-answers", "FOUND,y,y,y,y")
    wtip = run(["git", "--git-dir", org + "-witness/history.git", "rev-parse", "main"], org)[1].strip()
    ok("a test-mode founding, pushed with SEED_SELFTEST=1 in the pusher's environment to a witness set up without it, "
       "is refused: the witness reads test mode from its own setting",
       "WITNESS REFUSED THIS PUSH" in out and "STRUCTURE BEFORE FOUNDING" in out
       and wtip != git(org, "rev-parse", "HEAD")[1].strip(), out)
    drop(org)
    org = os.path.join(tmp, "shown-org")
    prepare_founding(seed, org)

    def edits(c):
        c["decision_rights"]["reserved_to_founder"] = c["decision_rights"]["reserved_to_founder"][:2]
        c["roles"][0]["instances"].append({"id": "member-9"})
    edit_config(org, edits)
    code, out = py(org, "fos_close.py", "--test-answers", "1,n,n,y")
    sig = (objs(org, "records/signatures.jsonl") or [{}])[-1]
    shown = "\n".join((sig.get("shown") or {}).get("structure_changes") or [])
    ok("at the founding prompt the founder sees every change from birth, in words: a trimmed reserved right (which "
       "this close-out cannot put back, and the screen says so), an added role instance (offered to put back), the "
       "module the founding adopts, and the charter's lines; the signature keeps what was shown",
       'decision_rights > reserved_to_founder: removed: "sign the organization\'s work"   [cannot be put back here]' in out
       and "roles > founder > instances > member-9: added" in out
       and "the close-out offers to put it back, after the founding]" in out
       and 'modules > memory > state: was "off", now "on"   [adopted by D-0001, this founding]' in out
       and "added line:   ### NG-1 Learn the field" in out
       and "This close-out cannot put back the 3 change(s) marked 'cannot be put back here' or the lines of "
           "org/CHARTER.md" in out
       and out.find("reserved_to_founder") < out.find(FOUND_PROMPT) and "reserved_to_founder" in shown, out)
    drop(org)


def t_listening(seed):
    print("The interview listens first: a reason the founder already gave is not asked for again")
    start = read(seed, "onboarding/START.md")
    step5 = start.split("## ▶ 5.", 1)[1].split("\n## ", 1)[0]
    cue = step5.find("**Listen before you ask.**")
    ok("step 5 tells the member to look back over the founder's words before each question, and not to ask again "
       "what was already said", cue > step5.find("1. A year from now") and "do not ask for it again" in step5
       and "say it back in their own words" in step5 and "ask only what is still missing" in step5)
    ok("GOAL.md's reason field is filled from wherever the founder gave the reason, in their words",
       "`reason:` for why it matters, taken from wherever they said it" in step5
       and "reason: (why it matters to them, in their own words)" in read(seed, "org/GOAL.md"))


def t_pointers(tmp, seed):
    print("Boot pointers: CLAUDE.md and GEMINI.md import AGENTS.md; the others point to it in words")
    raw = {rel: open(os.path.join(seed, *rel.split("/")), "rb").read() for rel in
           ("CLAUDE.md", "GEMINI.md", ".cursorrules", ".windsurfrules", "CONVENTIONS.md", ".github/copilot-instructions.md")}
    ok("CLAUDE.md holds only the import line @AGENTS.md, outside backticks, so Claude Code loads the boot file",
       raw["CLAUDE.md"] == b"@AGENTS.md\n", repr(raw["CLAUDE.md"]))
    ok("GEMINI.md holds only Gemini CLI's import line for the same folder, @./AGENTS.md",
       raw["GEMINI.md"] == b"@./AGENTS.md\n", repr(raw["GEMINI.md"]))
    ok("the other pointer files name AGENTS.md in words, with no import line an app could misread",
       all(b"Read AGENTS.md in full and follow it" in v or b"Read it in full and follow it" in v
           for k, v in raw.items() if k not in ("CLAUDE.md", "GEMINI.md")) and
       all(b"@" not in v for k, v in raw.items() if k not in ("CLAUDE.md", "GEMINI.md")), str(raw))
    org = os.path.join(tmp, "ptr-org")
    py(seed, "fos_init.py", org)
    write(org, "CLAUDE.md", "@AGENTS.md\n@work/other_instructions.md\n")
    code, out = py(org, "fos_check.py")
    ok("a pointer file changed after birth is reported, like the seed's other files",
       "seed file changed since birth: CLAUDE.md" in out, out)
    drop(org)


def t_zip(tmp, seed):
    print("A ZIP download, with no history of its own: the birth still makes the git history and the witness")
    import zipfile
    s_tree = git(seed, "rev-parse", "HEAD^{tree}")[1].strip()
    zpath = os.path.join(tmp, "seed-download.zip")
    git(seed, "archive", "--format=zip", "--prefix=OrgSeed/", "-o", zpath, "HEAD")
    plain = os.path.join(tmp, "dl-plain")
    inside = os.path.join(tmp, "dl-in-repo")          # a download folder that is itself inside some git repository
    for d in (plain, inside):
        os.makedirs(d)
    git(inside, "init", "-q", "--initial-branch=main")
    write(inside, "unrelated.txt", "a file of some other repository\n")
    git(inside, "add", "-A")
    git(inside, "-c", "user.name=x", "-c", "user.email=", "commit", "-q", "-m", "unrelated")
    for d in (plain, inside):
        with zipfile.ZipFile(zpath) as z:
            z.extractall(d)
    for label, d in (("a plain download folder", plain), ("a folder inside another repository", inside)):
        zseed, org = os.path.join(d, "OrgSeed"), os.path.join(tmp, "zip-org-%s" % os.path.basename(d))
        code, out = py(zseed, "fos_init.py", org)
        ok("from a downloaded copy in %s, fos_init still makes the git repository and the witness" % label,
           code == 0 and "Born:" in out and "without git" not in out and "a downloaded copy with no history" in out
           and os.path.isdir(os.path.join(org, ".git")) and os.path.isdir(org + "-witness/history.git"), out)
        root = git(org, "rev-list", "--max-parents=0", "HEAD")[1].strip()
        subjects = git(org, "log", "--reverse", "--format=%s")[1].splitlines()
        wtip = run(["git", "--git-dir", org + "-witness/history.git", "rev-parse", "main"], org)[1].strip()
        ok("its birth hash is the seed's own tree, computed from the files; [SEED] and [BIRTH] are in the witness (%s)"
           % label, git(org, "rev-parse", root + "^{tree}")[1].strip() == s_tree and s_tree in out
           and len(subjects) == 2 and subjects[0].startswith("[SEED]") and subjects[1].startswith("[BIRTH]")
           and wtip == git(org, "rev-parse", "HEAD")[1].strip()
           and not os.path.exists(os.path.join(org, "unrelated.txt")), "%s\n%s" % (subjects, out))
        code, out = py(org, "fos_check.py")
        ok("and the check passes in it (%s)" % label, code == 0 and "UNWITNESSED" not in out, out)
        code, out = py(zseed, "fos_check.py")
        ok("the downloaded seed's check names the same tree, computed from its files (%s)" % label,
           "a copy with no history; seed tree %s, computed from its files" % s_tree in out, out)
        drop(org)
    code, out = py(os.path.join(plain, "OrgSeed"), "fos_init.py", os.path.join(tmp, "zip-from"), "--from", "HEAD")
    ok("--from, which needs the seed's history, is refused for a downloaded copy",
       code == 1 and "needs the seed's history" in out and not os.path.exists(os.path.join(tmp, "zip-from")), out)
    rmtree(plain)
    rmtree(inside)


def t_launchers(tmp, seed):
    print("Double-click launchers for the founder's own steps, keeping each script's safeguards")
    scripts = {"Found-an-organization": "fos_init.py --ask", "Start-a-member": "fos_launch.py --ask --file",
               "Close-out": "fos_close.py"}
    modes = {ln.split("\t", 1)[1]: ln.split()[0] for ln in git(seed, "ls-files", "-s")[1].splitlines() if "\t" in ln}
    bad = []
    for name, script in scripts.items():
        cmd = open(os.path.join(seed, name + ".cmd"), "rb").read()
        sh = open(os.path.join(seed, name + ".command"), "rb").read()
        if cmd.count(b"\n") != cmd.count(b"\r\n") or b'cd /d "%~dp0"' not in cmd \
                or ("scripts\\" + script).encode() not in cmd or b"\r\npause\r\n" not in cmd:
            bad.append(name + ".cmd")
        if not sh.startswith(b"#!/bin/sh\n") or b"\r" in sh or b'cd "$(dirname "$0")"' not in sh \
                or ("scripts/" + script).encode() not in sh or b"read -r _" not in sh:
            bad.append(name + ".command")
        if any(x in cmd + sh for x in (b"--test-answers", b" < ", b"isatty")):
            bad.append(name + " (bypasses a safeguard)")
        if modes.get(name + ".command") != "100755" or modes.get(name + ".cmd") != "100644":
            bad.append(name + " (mode)")
    ok("each founder step has a Windows (.cmd, CRLF) and a macOS (.command, executable) launcher that changes to its "
       "own folder, runs the script unchanged, and waits before closing", not bad, str(bad))
    org = os.path.join(tmp, "launch-org")
    py(seed, "fos_init.py", org)
    root = git(org, "rev-list", "--max-parents=0", "HEAD")[1].strip()
    born = {ln.split("\t", 1)[1]: ln.split()[0] for ln in git(org, "ls-tree", root)[1].splitlines() if "\t" in ln}
    ok("the organization is born with the launchers, the macOS ones still executable, and the same birth hash",
       all(born.get(n + ".command") == "100755" and born.get(n + ".cmd") == "100644" for n in scripts)
       and git(org, "rev-parse", root + "^{tree}")[1].strip() == git(seed, "rev-parse", "HEAD^{tree}")[1].strip(),
       str(born))
    code, out = py(org, "fos_init.py", os.path.join(tmp, "from-an-org"))
    ok("the founding launcher, copied into every organization, will not found one from an organization",
       code == 1 and "not the seed itself" in out and not os.path.exists(os.path.join(tmp, "from-an-org")), out)
    env = dict(ENV, PATH=os.path.dirname(PY) + os.pathsep + os.environ.get("PATH", ""))
    env.pop("SEED_SELFTEST")

    def launch(folder, name, data=None):
        if os.name == "nt":
            args = ["cmd", "/c", os.path.join(folder, name + ".cmd")]
        else:
            args = ["sh", os.path.join(folder, name + ".command")]
        r = subprocess.run(args, cwd=tmp, env=env, input=data if data is not None else b"", capture_output=True,
                           timeout=300)
        return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")
    code, out = launch(org, "Close-out")
    ok("the close-out launcher keeps the close-out's own safeguard: run without a terminal, the script refuses",
       code == 3 and "runs only in a terminal you are typing in" in out and "Committed" not in out, out)
    code, out = launch(org, "Start-a-member")
    ok("so does the member launcher", code == 3 and "runs only in a terminal you are typing in" in out, out)
    code, out = launch(seed, "Found-an-organization", b"named-by-launcher\n\n")
    made = os.path.join(os.path.dirname(seed), "named-by-launcher")
    ok("the founding launcher asks for a name and makes the organization and its witness next to the seed",
       code == 0 and "Born:" in out and os.path.isdir(os.path.join(made, ".git")) and os.path.isdir(made + "-witness"),
       out)
    write(org, "Close-out.cmd", "@echo off\r\nrem changed\r\n")
    code, out = py(org, "fos_check.py")
    ok("a launcher changed in an organization is reported, like the seed's other files",
       "seed file changed since birth: Close-out.cmd" in out, out)
    drop(made)
    drop(org)


def t_study(tmp, seed):
    print("A research configuration: the claim rule switched off for a study, and only for a study")
    write(tmp, "study.json", json.dumps({"name": "claims-off pilot", "switch_off": ["CORE-13"], "status": "exploratory"}))
    write(tmp, "bad_study.json", json.dumps({"name": "no records", "switch_off": ["CORE-4"]}))
    code, out = py(seed, "fos_init.py", os.path.join(tmp, "bad-study"), "--study", os.path.join(tmp, "bad_study.json"))
    ok("nothing but the claim rule can be switched off (the record-keeping core never)",
       code == 1 and not os.path.exists(os.path.join(tmp, "bad-study")), out)
    org = os.path.join(tmp, "study-org")
    code, out = py(seed, "fos_init.py", org, "--study", os.path.join(tmp, "study.json"))
    ok("fos_init --study makes a research configuration and says so", code == 0 and "RESEARCH CONFIGURATION" in out, out)
    agents = open(os.path.join(org, "AGENTS.md"), encoding="utf-8").read()
    start = open(os.path.join(org, "onboarding", "START.md"), encoding="utf-8").read()
    ok("its boot file has no claim rule, and its first session asks for no claims lines",
       "CORE-13" not in agents and "CORE-12" in agents and "records/claims.jsonl" not in start)
    ok("the first session's line about recall, part of the claim rule, goes with it",
       "What you remember is never a source" not in start and "log every fetch" in start)
    s_tree = git(seed, "rev-parse", "HEAD^{tree}")[1].strip()
    root = git(org, "rev-list", "--max-parents=0", "HEAD")[1].strip()
    subjects = git(org, "log", "--reverse", "--format=%s")[1].splitlines()
    ok("it is still born from the seed (same birth hash), and the change is its own [STUDY] commit",
       git(org, "rev-parse", root + "^{tree}")[1].strip() == s_tree and len(subjects) == 3
       and subjects[2].startswith("[STUDY]"), str(subjects))
    log(org, "event", {"type": "session_start", "summary": "A study session"})
    write(org, "work/notes.md", "See https://example.org/x for the numbers.\n")
    code, out = py(org, "fos_check.py")
    ok("the check says it is a research configuration and runs no claim checks",
       code == 0 and "configuration: research" in out and "cites URL" not in out
       and "seed file changed since birth" not in out, out)
    py(org, "fos_render.py")
    ok("the view says so in its frame",
       "RESEARCH CONFIGURATION" in open(os.path.join(org, "view", "org_view.html"), encoding="utf-8").read())
    plain = os.path.join(tmp, "plain-org")
    py(seed, "fos_init.py", plain)
    shutil.copyfile(os.path.join(org, "org", "STUDY.json"), os.path.join(plain, "org", "STUDY.json"))
    write(plain, "work/notes.md", "See https://example.org/x for the numbers.\n")
    code, out = py(plain, "fos_check.py")
    ok("a STUDY.json copied into an ordinary organization switches nothing off",
       code == 1 and "RESEARCH CONFIGURATION NOT CONFIRMED" in out and "cites URL" in out, out)



def t_enforcement(tmp, seed):
    print("Enforcement declared in the record: an add-on that refused a write has a registry row saying what it covers")
    org = os.path.join(tmp, "enforce-org")
    py(seed, "fos_init.py", org)
    log(org, "event", {"type": "session_start", "summary": "First session"})
    code, out = log(org, "decline", {"by": "member-1", "rule_id": "OUR-1", "what": "a table with a rounded figure",
                                     "why_declined": "the add-on refused the write: OUR-1 asks for figures as printed",
                                     "outcome": "kept_after_fix", "enforced_by": "refuse-writes"})
    c2, out = py(org, "fos_check.py")
    ok("a decline enforced by an add-on with no registry row is UNDECLARED ENFORCEMENT",
       code == 0 and c2 == 0 and "UNDECLARED ENFORCEMENT: decline X-0001 says the add-on refuse-writes" in out, out)
    write(org, "tools/refuse-writes/addon.js", "// refuses writes that break OUR-1\n")
    p = os.path.join(org, "org", "TOOLS.json")
    reg = json.load(open(p, encoding="utf-8"))
    row = {"id": "refuse-writes", "kind": "enforcement add-on", "path": "tools/refuse-writes/addon.js", "tier": 2,
           "status": "active", "agent_app": "an agent app", "agent_app_version": "1.0", "enforces": ["OUR-1"],
           "refusal": "reasoned", "adopted_by": "D-0001"}
    reg["tools"].append(row)
    write(org, "org/TOOLS.json", json.dumps(reg, indent=2) + "\n")
    code, out = py(org, "fos_check.py")
    ok("its row, once registered, declares it; a row that does not say what it covers or which code it is is flagged",
       "UNDECLARED ENFORCEMENT" not in out and "enforcement add-on refuse-writes does not say which channels it covers "
       "(covers) or which code it is (code_sha256)" in out, out)
    row.update(covers="file tools; shell: no",
               code_sha256=L.hashlib.sha256(open(os.path.join(org, "tools", "refuse-writes", "addon.js"), "rb")
                                            .read()).hexdigest())
    write(org, "org/TOOLS.json", json.dumps(reg, indent=2) + "\n")
    code, out = py(org, "fos_check.py")
    ok("with what it covers and its code hash, the add-on is declared and nothing about it is flagged",
       "UNDECLARED ENFORCEMENT" not in out and "enforcement add-on refuse-writes" not in out, out)
    for status, declared in (("testing", True), ("proposed", False)):
        row["status"] = status
        write(org, "org/TOOLS.json", json.dumps(reg, indent=2) + "\n")
        code, out = py(org, "fos_check.py")
        ok("a row in testing declares the add-on, so the founder's own trial of it is on record" if declared else
           "a row that is only proposed does not",
           ("UNDECLARED ENFORCEMENT" not in out) if declared else
           ("UNDECLARED ENFORCEMENT: decline X-0001" in out and "in testing, active, paused or retired" in out), out)
    write(org, "addons/opencode/refuse_writes.js", "// changed in the organization\n")
    code, out = py(org, "fos_check.py")
    ok("a change to an add-on shipped with the seed is reported as a change to the seed's own files",
       "seed file changed since birth: addons/opencode/refuse_writes.js" in out, out)
    drop(org)



def t_change_loop(tmp, seed):
    print("Changes are welcome from any member, in the proposal form; the founder decides; DR-9 adopts on trial")
    org = os.path.join(tmp, "loop-org")
    py(seed, "fos_init.py", org)
    log(org, "event", {"type": "session_start", "summary": "First session"})
    code, out = log(org, "proposal", {
        "kind": "module", "target": "decision-rights", "change": "Switch on the decision-rights module",
        "why": "The founder wants to delegate small choices later", "proposed_by": "member-1",
        "problem": "Every small choice waits for the founder (records/decisions.jsonl)",
        "expected_effect": "Delegated choices recorded with the right used",
        "grounding": {"source": "Adler & Borys 1996, Two types of bureaucracy", "pages": "p. 72", "status": "read",
                      "source_file": "sources/adler_borys_1996.txt"},
        "for_the_founder": "You keep every key; you can hand some choices to a role later, and take them back.",
        "undo": "Switch the module off by a decision; its records stay."})
    ok("a proposal with the problem, the expected effect, its grounding, a paragraph for the founder and its undo is "
       "accepted", code == 0, out)
    code, out = log(org, "proposal", {"kind": "module", "target": "memory", "change": "Switch on the memory module",
                                      "why": "The founder chose it", "proposed_by": "member-1"})
    ok("a proposal without them is accepted too: they are asked for, not required", code == 0, out)
    decide(org, "Do you found the organization on this charter and adopt P-0001 and P-0002?", ["P-0001", "P-0002"],
           words="Yes: found it.", founding=True)
    set_module(org, "decision-rights", "on", "D-0001")
    set_module(org, "memory", "on", "D-0001")
    code, out = py(org, "fos_check.py")
    flagged = [x for x in out.splitlines() if "PROPOSAL WITHOUT PLAIN-LANGUAGE EFFECT OR UNDO" in x]
    ok("a decision adopting structure from a proposal that does not say what it changes for the founder, or how it is "
       "undone, is flagged, and only for that proposal", code == 0 and len(flagged) == 1
       and "D-0001 adopts structure from P-0002, which does not" in flagged[0] and "P-0001" not in flagged[0], out)
    ok("a proposal that rests on a work marked read with no saved copy is flagged (CORE-13)",
       "GROUNDING NOT SAVED: P-0001 rests on Adler & Borys 1996" in out, out)
    write(org, "sources/adler_borys_1996.txt", "Two types of bureaucracy: enabling and coercive.\n")
    code, out = py(org, "fos_check.py")
    ok("once its source is saved, it is not", "GROUNDING NOT SAVED" not in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "FOUND,y")
    rif = read(org, "org/RULES_IN_FORCE.md")
    ok("with decision-rights in force, the rules in force include DR-9: adopting on trial what the founder cannot judge",
       code == 0 and "### DR-9 Adopt on trial what you cannot judge" in rif, out[-1500:])
    log(org, "proposal", {"kind": "module", "target": "engagement", "change": "Switch on the engagement module",
                          "why": "The founder wants each session to hand a decision back", "proposed_by": "member-1",
                          "for_the_founder": "Each session ends with one decision for you.",
                          "undo": "Switch the module off by a decision."})
    log(org, "proposal", {"kind": "other", "target": "work/notes.md", "change": "Keep a running notes file",
                          "why": "Notes in one place", "proposed_by": "member-1"})
    decide(org, "Do you adopt P-0003 (switch on engagement) and P-0004 (a notes file)?", ["P-0003", "P-0004"])
    set_module(org, "engagement", "on", "D-0002")
    log(org, "proposal", {"kind": "other", "target": "work/notes.md", "change": "Cite the boot file", "why": "-",
                          "proposed_by": "member-1", "grounding": {"source": "The boot file", "status": "read",
                                                                   "source_file": "sources/../AGENTS.md"}})
    code, out = py(org, "fos_check.py")
    ok("only a decision's structural proposals are asked for the plain-language effect and the undo: a proposal of "
       "kind other beside one is not flagged",
       not [x for x in out.splitlines() if "PROPOSAL WITHOUT PLAIN-LANGUAGE EFFECT OR UNDO: D-0002" in x], out)
    ok("a saved copy named by a path that leaves sources/ does not count as saved",
       "GROUNDING NOT SAVED: P-0005 rests on The boot file" in out, out)
    agents, ss, close = read(org, "AGENTS.md"), read(org, "onboarding/SESSION_START.md"), read(org, "onboarding/CLOSE_OUT.md")
    ok("AGENTS.md, SESSION_START and CLOSE_OUT each say changes are welcome; CORE-2 asks for the proposal form; the core "
       "rules are still thirteen",
       agents.count("welcome") == 1 and ss.count("welcome") == 1 and close.count("welcome") == 1
       and "the difference it makes for the founder in everyday words, and the way back" in agents
       and len([x for x in agents.splitlines() if x.startswith("- **CORE-")]) == 13)
    drop(org)



def t_app_instructions(tmp, seed):
    print("A launch records the hashes of the agent app's own instructions, never their content")
    org = os.path.join(tmp, "instr-org")
    py(seed, "fos_init.py", org)
    home = os.path.join(tmp, "app-home")
    write(home, "instructions.md", "Answer briefly. SECRET-INSTRUCTION-TEXT-1\n")
    write(home, "plugins/a.js", "// SECRET-INSTRUCTION-TEXT-2\n")
    code, out = py(org, "fos_launch.py", "member-1", "--model-id", "model-x", "--producer", "Producer A",
                   "--agent-app", "an agent app", "--host", "this machine",
                   "--app-instructions", os.path.join(home, "instructions.md"), os.path.join(home, "plugins"),
                   "--test-answers", "")
    ev = [e for e in objs(org, "records/events.jsonl") if e.get("type") == "instance_launched"]
    got = (ev[-1].get("app_instructions") if ev else None) or []
    want = L.hashlib.sha256(open(os.path.join(home, "instructions.md"), "rb").read()).hexdigest()
    text = read(org, "records/events.jsonl")
    ok("the launch records two items, each by name and SHA-256, and none of their content or full paths",
       code == 0 and [g.get("name") for g in got] == ["instructions.md", "plugins/"] and got[0].get("sha256") == want
       and got[1].get("files") == 1 and "SECRET-INSTRUCTION-TEXT" not in text and "app-home" not in text, out)
    line = [x for x in out.splitlines() if "export FOS_LAUNCH=" in x]
    env = dict(ENV, FOS_LAUNCH=line[0].split("export FOS_LAUNCH=", 1)[1].strip()) if line else ENV
    py(org, "fos_log.py", "event", "type=note", "summary=a member at work", env=env)
    code, out = py(org, "fos_check.py")
    ok("the check matches the launch against the witness's copy and verifies the member's record as before",
       code == 0 and "differs from the witness folder's copy" not in out and "verified against their launch" in out, out)
    code, out = py(org, "fos_launch.py", "member-1", "--app-instructions", os.path.join(home, "missing.md"),
                   "--test-answers", "")
    ok("a path that is neither a file nor a folder records nothing",
       code == 1 and "Nothing was recorded" in out
       and len([e for e in objs(org, "records/events.jsonl") if e.get("type") == "instance_launched"]) == 1, out)
    drop(org)


def t_session(org):
    print("A session written through fos_log")
    ok("session_start", log(org, "event", {"type": "session_start", "summary": "Opened"})[0] == 0)
    write(org, "work/p1.json", json.dumps({"kind": "module", "target": "memory", "change": "Switch on the memory module",
                                           "why": "The founder wants rulings remembered", "proposed_by": "member-1"}))
    code, out = py(org, "fos_log.py", "proposal", "--json-file", "work/p1.json")
    os.remove(os.path.join(org, "work", "p1.json"))
    ok("a whole record from a file (--json-file)", code == 0, out)
    ok("a whole record from standard input (--json -)", log(org, "proposal", {
        "kind": "module", "target": "charter", "change": "Switch on the charter module", "why": "A charter",
        "proposed_by": "member-1"})[0] == 0)
    code, out = log(org, "decision", {"question": "Do you found the organization on this charter and adopt P-0001 "
                                                  "(switch on the memory module)?",
                                      "proposal_ids": ["P-0001"], "framed_by": "member-1", "decided_by": "founder",
                                      "decider_kind": "human", "right": "founder", "verdict": "adopted",
                                      "words": "Yes, I adopt P-0001.", "founding": True})
    ok("decision with the founder's words", code == 0, out)
    log(org, "decision", {"question": "Shall we keep going?", "proposal_ids": ["P-0002"], "framed_by": "member-1",
                          "decided_by": "founder", "decider_kind": "human", "right": "founder", "verdict": "adopted",
                          "words": "Sounds great!"})
    set_module(org, "memory", "on", "D-0001")
    set_module(org, "charter", "on", "D-0002")
    write(org, "work/notes.md", "Sources: https://example.org/report and doi 10.1234/abcd.5\n")
    write(org, "docs/MY_NOTES.md", "a member wrote in docs\n")
    log(org, "event", {"type": "session_end", "summary": "Closed"})
    code, out = py(org, "fos_check.py")
    ok("check flags a generic reply recorded as a decision", "Sounds great!" in out and "generic" in out, out)
    ok("check flags a question that does not name its proposal", "does not name P-0002" in out, out)
    ok("check reports decided structure as awaiting signature", "AWAITING SIGNATURE" in out, out)
    ok("check flags citations in work/ with no claims line", "cites URL https://example.org/report" in out and "cites DOI" in out, out)
    ok("check flags a member writing into docs/", "docs/MY_NOTES.md changed" in out, out)
    ok("no failure so far (warnings only)", code == 0, out)
    os.remove(os.path.join(org, "docs", "MY_NOTES.md"))


def t_batch(org):
    print("Several records in one call, and members writing side by side")
    n0 = len(objs(org, "records/dissent.jsonl"))
    recs = [{"by": "member-1", "rule_id": "CORE-%d" % i, "case": "batch test %d" % i, "view": "a view"} for i in (1, 2)]
    code, out = py(org, "fos_log.py", "dissent", "--json", "-", data=json.dumps(recs).encode("utf-8"))
    ok("a JSON list of records goes in one call", code == 0 and len(objs(org, "records/dissent.jsonl")) == n0 + 2, out)
    write(org, "work/batch.jsonl", "".join(json.dumps(dict(r, case="line %d" % i)) + "\n" for i, r in enumerate(recs)))
    code, out = py(org, "fos_log.py", "dissent", "--json-file", "work/batch.jsonl")
    ok("one record per line goes in one call", code == 0 and len(objs(org, "records/dissent.jsonl")) == n0 + 4, out)
    mixed = [{"record": "event", "type": "note", "summary": "batch of kinds"},
             {"record": "decline", "by": "member-1", "rule_id": "CORE-13", "what": "an unsourced number",
              "why_declined": "no source", "outcome": "dropped"}]
    code, out = py(org, "fos_log.py", "batch", "--json", "-", data=json.dumps(mixed).encode("utf-8"))
    ok("batch mixes kinds, each naming its kind", code == 0 and "Wrote 2 records" in out, out)
    before = {f: len(lines(org, "records/" + f)) for f in ("events.jsonl", "declines.jsonl")}
    bad = [{"record": "event", "type": "note", "summary": "fine"}, {"record": "decline", "by": "member-1"}]
    code, out = py(org, "fos_log.py", "batch", "--json", "-", data=json.dumps(bad).encode("utf-8"))
    after = {f: len(lines(org, "records/" + f)) for f in ("events.jsonl", "declines.jsonl")}
    ok("if one record in a call does not fit, none is written", code == 1 and "Nothing was written" in out
       and before == after, out)
    os.remove(os.path.join(org, "work", "batch.jsonl"))
    # Three writers in tight loops through the one appender (as fos_log calls it). Without the lock, this
    # gives many repeated seq numbers; with it, none.
    script = "\n".join([
        "import os, sys",
        "sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))",
        "import fos_lib as L",
        "for i in range(40):",
        "    L.append_record('event', {'type': 'note', 'summary': 'side-' + sys.argv[1] + str(i), 'instance': 'member-1'})",
        ""])
    procs = [subprocess.Popen([PY, "-c", script, tag], cwd=org, env=ENV) for tag in ("a", "b", "c")]
    for p in procs:
        p.wait()
    ev = objs(org, "records/events.jsonl")
    seqs = [e["seq"] for e in ev]
    side = [e for e in ev if str(e.get("summary", "")).startswith("side-")]
    ok("three writers side by side: every line kept, no seq used twice",
       len(side) == 120 and len(seqs) == len(set(seqs)) and seqs == sorted(seqs)
       and len(lines(org, "records/events.jsonl")) == len(ev), "%d of 120 lines; %d repeated seq"
       % (len(side), len(seqs) - len(set(seqs))))
    ok("no lock is left behind", not os.path.exists(os.path.join(org, ".fos-lock")))


def t_log_refusals(org):
    print("fos_log refusals")
    code, out = py(org, "fos_log.py", "signature", "decision_id=D-0001")
    ok("refuses a signature from a member", code == 1 and "never by a member" in out, out)
    code, out = py(org, "fos_log.py", "event", "type=close_out", "summary=x")
    ok("refuses a close_out event from a member", code == 1, out)
    code, out = py(org, "fos_log.py", "event", "type=note", "summary=x", "captured_by=close_script")
    ok("refuses a reserved captured_by value", code == 1, out)
    code, out = py(org, "fos_log.py", "decision", "question=x")
    ok("refuses a record that does not fit its schema", code == 1 and "missing required field" in out, out)
    code, out = py(org, "fos_log.py", "event", "type=note", "summary=dry", "--check")
    ok("--check validates without writing", code == 0 and "valid (not written)" in out, out)


def t_close(org):
    print("The founder's close-out")
    code, out = py(org, "fos_close.py", stdin=subprocess.DEVNULL)
    ok("refuses to run without a terminal", code == 3, out)
    env = dict(ENV)
    env.pop("SEED_SELFTEST")
    code, out = py(org, "fos_close.py", "--check-only", env=env, stdin=subprocess.DEVNULL)
    ok("--check-only runs anywhere and lists what waits", code == 0 and "D-0001" in out, out)
    glob_cfg = os.path.join(os.path.dirname(org), "global.gitconfig")
    with open(glob_cfg, "w", encoding="utf-8") as f:
        f.write("[user]\n\tname = Someone Global\n\temail = someone@example.invalid\n")
    code, out = py(org, "fos_close.py", "--test-answers", "FOUND,n,n,y", env=dict(ENV, GIT_CONFIG_GLOBAL=glob_cfg))
    ok("test mode: founds the organization on D-0001, does not sign D-0002, commits and pushes",
       code == 0 and "The witness has the close-out" in out, out)
    who = git(org, "log", "-1", "--format=%an <%ae>")[1].strip()
    ok("the commit carries the organization's own author name, never a machine-wide git name or e-mail",
       who == "Test Founder <>", who)
    ok("the founder is offered to put back structure with no signed decision (and here keeps it, as a proposal)",
       "no signed decision behind them" in out and "module 'charter'" in out, out)
    ok("before signing, the founder sees the check result and what changed on disk",
       "Before you sign" in out and "Check:" in out and "org/config.json" in out, out)
    ok("the founding is asked first, on its own, where the founder types FOUND; the decision with warnings after it, "
       "on its own", "The founding (asked first, on its own)" in out and "Needs your judgement (1)" in out
       and "Routine (" not in out and 0 <= out.index(FOUND_PROMPT) < out.index("Sign D-0002?"), out)
    subjects = git(org, "log", "-2", "--format=%s")[1].splitlines()
    ok("the founding is its own commit, before the one with the structure",
       len(subjects) == 2 and subjects[1].startswith("[FOUND]") and subjects[0].startswith("[CLOSE]"), str(subjects))
    sigs = objs(org, "records/signatures.jsonl")
    ok("two signature lines, written by the close-out", len(sigs) == 2 and all(s["captured_by"] == "close_script" for s in sigs))
    by = {s["decision_id"]: s for s in sigs}
    ok("each signature records what the founder was shown", all(s.get("shown_sha256") and s.get("shown") for s in sigs)
       and "module 'memory'" in by.get("D-0001", {}).get("shown", {}).get("effects", [])
       and by.get("D-0002", {}).get("shown", {}).get("warnings"), json.dumps(sigs)[:400])
    shown_files = by.get("D-0001", {}).get("shown", {}).get("changed_files_sha256", {})
    ok("what was shown includes the SHA-256 of each changed file",
       shown_files and all(len(h) == 64 for h in shown_files.values()), json.dumps(shown_files)[:300])
    head = git(org, "rev-parse", "HEAD")[1].strip()
    wtip = run(["git", "--git-dir", org + "-witness/history.git", "rev-parse", "main"], org)[1].strip()
    ok("the witness holds the close-out commit", head == wtip, "%s vs %s" % (head, wtip))
    author = git(org, "log", "-1", "--format=%an %ad", "--date=iso")[1]
    ok("the close-out commit is dated in UTC", "+0000" in author, author)
    code, out = py(org, "fos_check.py")
    ok("signed structure is in force", "memory" in open(os.path.join(org, "org", "RULES_IN_FORCE.md"), encoding="utf-8").read())
    ok("structure whose decision the founder refused fails", code == 1 and "refused to sign D-0002" in out, out)
    ok("a refused decision leaves its proposal open, and the next member is told so",
       "P-0002 is still a proposal, open again: the founder did not sign D-0002" in out and "(1 open," in out, out)
    py(org, "fos_render.py")
    ok("the view's queue shows it as open again",
       "open again: the founder did not sign D-0002" in open(os.path.join(org, "view", "org_view.html"), encoding="utf-8").read())
    env = dict(ENV)
    env.pop("SEED_SELFTEST")
    code, out = py(org, "fos_check.py", env=env)
    ok("outside the self-test, test signatures sign nothing, and a test founding founds nothing",
       "test mode" in out and "STRUCTURE BEFORE FOUNDING" in out, out)
    set_module(org, "charter", "off", None)
    log(org, "event", {"type": "structure_change", "summary": "Charter module switched off: the founder did not sign D-0002"})
    code, out = py(org, "fos_check.py")
    ok("undoing the unsigned change clears the failure", code == 0, out)


def t_corrections(org):
    print("Corrections by seq and line")
    write(org, "records/events.jsonl", '{"seq": 99, broken line\n', mode="a")
    code, out = py(org, "fos_check.py")
    ok("a malformed line fails the check", code == 1 and "not valid JSON" in out, out)
    n = len(open(os.path.join(org, "records", "events.jsonl"), encoding="utf-8").read().splitlines())
    code, out = log(org, "event", {"type": "record_correction", "corrects": {"file": "records/events.jsonl", "line": n},
                                   "summary": "line %d is a broken write; it should have been a note" % n})
    ok("fos_log still appends after a malformed line", code == 0, out)
    code, out = py(org, "fos_check.py")
    ok("once corrected, it is a corrected defect, not a failure", code == 0 and "corrected defect" in out, out)


def t_witness_refusals(org):
    print("The witness refuses, and a sync returns the folder to the witnessed history")
    code, out = py(org, "fos_close.py", "--test-answers", "y")
    ok("a clean close-out first, so every planted change starts from the witnessed state", code == 0, out)
    os.remove(os.path.join(org, "records", "dissent.jsonl"))
    git(org, "add", "-A")
    git(org, "commit", "-q", "-m", "[WORK] tidy up")
    code, out = git(org, "push", "witness", "main")
    ok("a records file deleted in a member's own commit", code != 0 and "a records file was deleted" in out, out)
    code, out = py(org, "fos_check.py")
    ok("the check sees the deletion in history", code == 1 and "a records file was deleted" in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "y,y,y")
    ok("the close-out offers a sync, which returns the folder to the witnessed history and closes out",
       code == 0 and "Run the sync now?" in out and "The witness has the close-out" in out
       and os.path.exists(os.path.join(org, "records", "dissent.jsonl")) and "reset --hard" not in out, out)
    ev = objs(org, "records/events.jsonl")
    ok("the sync is on record", any(e.get("type") == "sync" and e.get("captured_by") == "sync_script" for e in ev))
    code, out = py(org, "fos_check.py")
    ok("after the sync the check passes", code == 0, out)
    p = os.path.join(org, "records", "decisions.jsonl")
    ls = open(p, encoding="utf-8").read().splitlines()
    ls[0] = ls[0].replace("Yes, I adopt P-0001.", "Yes, adopt everything.")
    write(org, "records/decisions.jsonl", "".join(x + "\n" for x in ls))
    git(org, "commit", "-q", "-am", "[WORK] fix wording")
    code, out = git(org, "push", "witness", "main")
    ok("an earlier line edited in a commit", code != 0 and "earlier lines were changed" in out, out)
    code, out = py(org, "fos_sync.py", "--test-answers", "y")
    aside = [d for d in os.listdir(org + "-witness/set_aside")] if os.path.isdir(org + "-witness/set_aside") else []
    ok("fos_sync undoes the refused commit, sets the edited line aside and keeps a copy of everything",
       code == 0 and "Yes, I adopt P-0001." in open(p, encoding="utf-8").read() and len(aside) >= 2, out)
    write(org, "records/events.jsonl", "", mode="a")
    git(org, "commit", "-q", "--amend", "--allow-empty", "-m", "[CLOSE] rewritten")
    code, out = git(org, "push", "-f", "witness", "main")
    ok("a rewritten history (force push)", code != 0 and "history was rewritten" in out, out)
    code, out = py(org, "fos_check.py")
    ok("the check sees the local rewrite", code == 1 and "no longer contains the witnessed commit" in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "n")
    ok("the close-out will not commit over a rewritten history, and never advises reset --hard",
       code == 1 and "Nothing was committed" in out and "reset --hard" not in out, out)
    code, out = git(org, "push", "witness", "main:refs/heads/other")
    ok("a second branch", code != 0 and "keeps one branch" in out, out)
    log_lines = objs(org + "-witness", "pushlog.jsonl")
    refused = [x for x in log_lines if x.get("result") == "refused"]
    ok("every refused push is logged in the witness folder, with its reasons and the hash of the check",
       len(refused) >= 4 and all(x.get("reasons") and len(x.get("check_sha256", "")) == 64 for x in refused)
       and any(x.get("result") == "accepted" for x in log_lines), "%d lines, %d refused" % (len(log_lines), len(refused)))
    code, out = py(org, "fos_check.py")
    ok("the check counts the refused pushes", "the witness has refused %d push(es)" % len(refused) in out, out)
    code, out = py(org, "fos_sync.py", "--test-answers", "y")
    ok("fos_sync returns a rewritten history to the witnessed one", code == 0, out)
    code, out = git(org, "push", "witness", ":main")
    ok("deleting its branch", code != 0, out)
    code, out = py(org, "fos_check.py")
    ok("back to the witnessed history, the check passes", code == 0, out)


def t_parallel(tmp, org):
    print("Two copies of one organization: not supported, told apart from a rewrite, synced without loss")
    code, out = py(org, "fos_close.py", "--test-answers", "y")
    ok("copy A starts from a close-out", code == 0, out)
    other = os.path.join(tmp, "copy-b")
    code, out = run(["git", "clone", "-q", "-o", "witness", org + "-witness/history.git", other], tmp)
    ok("a second copy is made from the witness", code == 0, out)
    log(org, "event", {"type": "session_start", "summary": "copy A works"})
    py(other, "fos_log.py", "event", "--json", "-", data=json.dumps({"type": "session_start", "summary": "copy B works"}).encode())
    a, b = objs(org, "records/events.jsonl")[-1], objs(other, "records/events.jsonl")[-1]
    ok("the two copies number their records the same way (why copies are not supported)",
       a["seq"] == b["seq"] and a["session"] == b["session"], "%s/%s vs %s/%s" % (a["seq"], a["session"], b["seq"], b["session"]))
    code, out = py(org, "fos_close.py", "--test-answers", "y")
    ok("copy A closes out first", code == 0 and "The witness has the close-out" in out, out)
    code, out = py(other, "fos_check.py")
    ok("copy B is told it is behind, not that its history was rewritten",
       code == 1 and "BEHIND THE WITNESS" in out and "REWRITTEN" not in out and "no longer contains" not in out, out)
    code, out = py(other, "fos_close.py", "--test-answers", "y,y")
    ok("copy B's close-out offers the sync (never reset --hard); its colliding record is set aside, not merged",
       code == 0 and "reset --hard" not in out and "sets aside 1 record line" in out
       and "The witness has the close-out" in out, out)
    ev = objs(other, "records/events.jsonl")
    ok("copy B now holds copy A's session, and not its own colliding line",
       any(e.get("summary") == "copy A works" for e in ev) and not any(e.get("summary") == "copy B works" for e in ev))
    kept = [os.path.join(d, f) for d, _, fs in os.walk(org + "-witness/set_aside") for f in fs if f == "manifest.json"]
    ok("copy B's line is kept in the witness folder", any("copy B works" in open(k, encoding="utf-8").read() for k in kept))
    code, out = py(other, "fos_check.py")
    ok("copy B passes the check again", code == 0, out)
    code, out = py(org, "fos_check.py")
    ok("copy A, behind in its turn, is told so", code == 1 and "BEHIND THE WITNESS" in out, out)
    code, out = py(org, "fos_sync.py", "--test-answers", "y")
    code2, out2 = py(org, "fos_check.py")
    ok("copy A comes back in line with nothing lost", code == 0 and code2 == 0
       and any(e.get("summary") == "copy A works" for e in objs(org, "records/events.jsonl")), out + out2)
    rmtree(other)


def t_repair(org):
    print("Repair at close-out")
    log(org, "event", {"type": "session_start", "summary": "Second session"})
    os.remove(os.path.join(org, "records", "dissent.jsonl"))
    p = os.path.join(org, "records", "proposals.jsonl")
    ls = open(p, encoding="utf-8").read().splitlines()
    ls[0] = ls[0].replace("memory", "everything")
    write(org, "records/proposals.jsonl", "\n".join(ls) + "\n")
    code, out = py(org, "fos_check.py")
    ok("the check sees the deletion and the edit", code == 1 and "dissent.jsonl is missing" in out
       and "proposals.jsonl: earlier lines were edited" in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "y,y")
    ok("the close-out restores both and commits", code == 0 and "restored records/dissent.jsonl" in out, out)
    ev = [x for x in objs(org, "records/events.jsonl")]
    rep = [e for e in ev if e["type"] == "integrity_repair"]
    ok("the repair is recorded, with the changed line kept", len(rep) == 2 and any(e.get("dropped_lines") for e in rep))
    ok("the second session's newer record survived the repair", any(e.get("summary") == "Second session" for e in ev))
    code, out = py(org, "fos_check.py")
    ok("after the repair the check passes", code == 0, out)


def t_forgery(org):
    print("A forged signature")
    log(org, "proposal", {"kind": "rule", "target": "OUR-1", "change": "Add a rule", "why": "test", "proposed_by": "member-1"})
    log(org, "decision", {"question": "Do you adopt P-0003 (add a rule)?", "proposal_ids": ["P-0003"],
                          "framed_by": "member-1", "decided_by": "founder", "decider_kind": "human", "right": "founder",
                          "verdict": "adopted", "words": "Yes, I adopt P-0003."})
    raw = lines(org, "records/decisions.jsonl")[-1]
    seq = max(x["seq"] for x in objs(org, "records/signatures.jsonl")) + 1
    forged = {"seq": seq, "id": "SG-%04d" % seq, "ts": "2026-10-08T00:00:00+00:00", "session": "S002",
              "identity": {"instance": "fos_close", "kind": "script"}, "captured_by": "close_script",
              "decision_id": "D-0003", "decision_seq": json.loads(raw)["seq"],
              "decision_sha256": L.line_sha256(raw), "answer": "signed", "mode": "terminal", "signer": "founder"}
    write(org, "records/signatures.jsonl", json.dumps(forged) + "\n", mode="a")
    code, out = py(org, "fos_check.py")
    ok("an uncommitted signature line does not count", "not yet committed" in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "n,b=Reword the rule first,y")
    ok("the next close-out voids it and asks the founder", code == 0 and "marked void" in out and "Sign D-0003?" in out, out)
    sig = [x for x in objs(org, "records/signatures.jsonl") if x["decision_id"] == "D-0003" and x["captured_by"] == "close_script"]
    ok("the founder can send a decision back with a note", sig and sig[-1]["answer"] == "sent_back"
       and sig[-1].get("note") == "Reword the rule first", json.dumps(sig)[:300])
    code, out = py(org, "fos_check.py")
    ok("the members see the founder's note on a decision sent back", "sent back by the founder" in out
       and "Reword the rule first" in out, out)
    log(org, "proposal", {"kind": "role", "target": "checker", "change": "Add a checker role", "why": "a second reading",
                          "proposed_by": "member-1"})
    log(org, "decision", {"question": "Do you adopt P-0004 (add a checker role)?", "proposal_ids": ["P-0004"],
                          "framed_by": "member-1", "decided_by": "founder", "decider_kind": "human", "right": "founder",
                          "verdict": "adopted", "words": "Yes, I adopt P-0004."})
    code, out = py(org, "fos_close.py", "--test-answers", "s=Yes and keep it small,y")
    ok("a change to who is a member is asked on its own", "Needs your judgement (1)" in out, out)
    ok("and that close-out was committed and witnessed", code == 0 and "The witness has the close-out" in out, out)
    sig = [x for x in objs(org, "records/signatures.jsonl") if x["decision_id"] == "D-0004"]
    ok("the founder can sign with a note", sig and sig[-1]["answer"] == "signed" and sig[-1].get("note"), json.dumps(sig)[:300])


def t_birth_lost(org):
    print("A lost birth record: events.jsonl overwritten whole")
    log(org, "event", {"type": "session_start", "summary": "Third session"})
    n_before = len(objs(org, "records/events.jsonl"))
    pretty = json.dumps({"type": "note", "summary": "a member wrote the events file whole"}, indent=2)
    write(org, "records/events.jsonl", pretty + "\n")     # the whole file replaced by one pretty-printed object
    code, out = py(org, "fos_check.py")
    ok("the check still knows the folder is an organization (birth read from the history)",
       ("stage: born" in out or "stage: founded" in out) and "birth read from the history" in out, out)
    ok("it names the lost birth record", code == 1 and "BIRTH RECORD LOST" in out, out)
    ok("it still checks the witness", "witness: none" not in out and "history.git" in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "y,y")
    ok("the close-out does not call it the seed, and restores the file before anything else",
       code == 0 and "seed itself" not in out and "restored records/events.jsonl" in out
       and out.index("restored records/events.jsonl") < out.index("Committed"), out)
    ev = objs(org, "records/events.jsonl")
    ok("the birth record is back, with the earlier events", any(e.get("type") == "born" for e in ev)
       and len(ev) >= n_before - 1, "%d events, %d before" % (len(ev), n_before))
    ok("the overwritten lines are kept in the repair record",
       any(e.get("type") == "integrity_repair" and any("wrote the events file whole" in d for d in e.get("dropped_lines", []))
           for e in ev))
    code, out = py(org, "fos_check.py")
    ok("after the repair the check passes", code == 0, out)
    write(org, "records/events.jsonl", "")                 # emptied, and the birth file deleted as well
    os.remove(os.path.join(org, "org", "BIRTH.json"))
    code, out = py(org, "fos_check.py")
    ok("an emptied events file and a deleted birth file are both named",
       code == 1 and "BIRTH RECORD LOST" in out and "org/BIRTH.json is missing" in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "y,y")
    ok("the close-out restores both", code == 0 and os.path.exists(os.path.join(org, "org", "BIRTH.json"))
       and any(e.get("type") == "born" for e in objs(org, "records/events.jsonl")), out)
    code, out = py(org, "fos_check.py")
    ok("and the check passes again", code == 0, out)


def t_sessions(org):
    print("Sessions that recorded nothing")
    write(org, "work/draft.md", "A draft written in a session that recorded nothing.\n")
    code, out = py(org, "fos_check.py")
    ok("files changed with no session_start since the last close-out are flagged",
       "SESSION NOT RECORDED" in out and "work/draft.md" in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "y")
    gap = [e for e in objs(org, "records/events.jsonl") if e.get("type") == "unrecorded_session"]
    ok("the close-out puts the gap on record, naming what changed", code == 0 and gap
       and "work/draft.md" in gap[-1]["summary"] and gap[-1]["founder_answer"].startswith("not asked"), out)
    labels = [e["session"] for e in objs(org, "records/events.jsonl") if e.get("type") == "close_out"]
    ok("an unrecorded session still gets its own number", len(labels) >= 2 and labels[-1] != labels[-2]
       and labels[-1] != "S000", str(labels[-3:]))
    code, out = py(org, "fos_close.py", "--test-answers", "y,y")
    gap = [e for e in objs(org, "records/events.jsonl") if e.get("type") == "unrecorded_session"]
    ok("with nothing recorded and nothing changed, the founder is asked whether a session took place",
       code == 0 and "Did you work with an AI member" in out and gap[-1]["founder_answer"] == "yes", out)
    last = [e for e in objs(org, "records/events.jsonl") if e.get("type") == "close_out"][-1]["session"]
    code, out = py(org, "fos_log.py", "event", "type=note", "summary=the founder's own note", "captured_by=founder")
    rec = json.loads(lines(org, "records/events.jsonl")[-1])
    ok("a record written after a close-out belongs to the next session, not the closed one",
       code == 0 and rec["session"] != last and L.session_number(rec["session"]) == L.session_number(last) + 1,
       "%s after %s" % (rec.get("session"), last))
    code, out = py(org, "fos_roles.py")
    ok("the roll-call counts close-outs: the drill role is reported after three sessions without a drill",
       any(x.strip().startswith("drill") and ("NEVER" in x or "STALE" in x) for x in out.splitlines()), out)
    py(org, "fos_close.py", "--test-answers", "y")


def edit_config(org, fn):
    p = os.path.join(org, "org", "config.json")
    with open(p, encoding="utf-8") as f:
        c = json.load(f)
    fn(c)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(c, f, indent=2)
        f.write("\n")


def last_id(org, rel):
    return objs(org, rel)[-1]["id"]


def nfails(org):
    """How many items the check fails in this folder now."""
    code, out = py(org, "fos_check.py", "--json")
    return len(json.loads(out[out.index("{"):])["fails"])


def t_fail_before_sign(org):
    print("What fails is shown before anything is signed")
    log(org, "event", {"type": "session_start", "summary": "A session that adds a role"})
    log(org, "proposal", {"kind": "role", "target": "claim-checker", "change": "Add a claim-checker role",
                          "why": "a second reading of claims", "proposed_by": "member-1"})
    pid = last_id(org, "records/proposals.jsonl")
    log(org, "decision", {"question": "Do you adopt %s (add a claim-checker role)?" % pid, "proposal_ids": [pid],
                          "framed_by": "member-1", "decided_by": "founder", "decider_kind": "human",
                          "right": "founder", "verdict": "adopted", "words": "Yes, I adopt %s." % pid})
    did = last_id(org, "records/decisions.jsonl")
    edit_config(org, lambda c: c["roles"].append({
        "id": "claim-checker", "title": "Claim checker", "kind": "ai", "purpose": "Checks claims.",
        "trigger": {"on": "claim_ready", "when": "when a claim is ready"}, "output": "records/reviews.jsonl",
        "expected_every_sessions": 3, "card": None, "instances": [], "adopted_by": did}))
    n = nfails(org)
    head, n_sig = git(org, "rev-parse", "HEAD")[1].strip(), len(lines(org, "records/signatures.jsonl"))
    code, out = py(org, "fos_close.py", "--test-answers", "y,y,y,y")
    ok("a scripted run that answers y to every prompt cannot sign past the failures: it stops before the first "
       "signature question, with nothing signed or committed",
       code == 1 and "Stopped before signing" in out and "Sign %s?" % did not in out
       and len(lines(org, "records/signatures.jsonl")) == n_sig and git(org, "rev-parse", "HEAD")[1].strip() == head, out)
    ok("every failing item is listed, numbered, before that question",
       n >= 1 and all("    %d. " % i in out for i in range(1, n + 1))
       and 0 <= out.find("What fails, before you sign anything") < out.find("Type %d, the number of failing items" % n),
       out)
    code, out = py(org, "fos_close.py", "--test-answers", "%d,n,y,y" % n)
    i_fail, i_ack, i_sign = (out.find("What fails, before you sign anything"),
                             out.find("Type %d, the number of failing items" % n), out.find("Sign %s?" % did))
    ok("every failure is listed before the first signature question, and its number must be typed to go on",
       0 <= i_fail < i_ack < i_sign and "claim_ready" in out[i_fail:i_ack], out)
    ok("the failure is attached to the decision whose effects include the failing role",
       "THE CHECK FAILS for what this decision adopts" in out and "Needs your judgement" in out, out)
    sig = [s for s in objs(org, "records/signatures.jsonl") if s["decision_id"] == did]
    ok("the signature records that the founder was shown every failure and acknowledged them",
       sig and "claim_ready" in json.dumps(sig[-1].get("shown", {}))
       and sig[-1]["shown"].get("failures_acknowledged") == n and len(sig[-1]["shown"]["check_failures"]) == n,
       json.dumps(sig)[:300])
    roles = [r["id"] for r in json.load(open(os.path.join(org, "org", "config.json"), encoding="utf-8"))["roles"]]
    ok("the role the founder did not sign was put back out at the close-out, and the record keeps what it was",
       code == 0 and "claim-checker" not in roles and any(e.get("put_back") for e in objs(org, "records/events.jsonl")), out)
    code, out = py(org, "fos_check.py")
    ok("so the check passes after that close-out", code == 0, out)


def t_selective(org):
    print("The founder chooses what a close-out commits")
    log(org, "event", {"type": "session_start", "summary": "A session that strays"})
    write(org, "work/ok.md", "Work in its proper place.\n")
    write(org, "docs/HOSTING.md", "\nA member's addition to the seed's documentation.\n", mode="a")
    write(org, "notes.txt", "A stray file at the top level.\n")
    set_module(org, "norms", "on", None)
    code, out = py(org, "fos_close.py", "--test-answers", "y,n,y,y,y")
    files = git(org, "show", "--name-only", "--format=", "HEAD")[1].split()
    mods = {m["id"]: m for m in json.load(open(os.path.join(org, "org", "config.json"), encoding="utf-8"))["modules"]}
    ok("structure switched on with no decision is put back before the commit",
       "module 'norms'" in out and mods["norms"]["state"] == "off", out)
    ok("the commit holds the records and the work, not the seed's documentation or the stray file",
       code == 0 and "work/ok.md" in files and "records/events.jsonl" in files
       and "docs/HOSTING.md" not in files and "notes.txt" not in files, " ".join(files))
    status = git(org, "status", "--porcelain")[1]
    ok("what was left out stays in the folder, uncommitted", "docs/HOSTING.md" in status and "notes.txt" in status, status)
    ok("the commit message says what was left out", "Left out of this commit" in git(org, "log", "-1", "--format=%B")[1])
    code, out = py(org, "fos_close.py", "--test-answers", "y,y,y")
    kept = [os.path.join(d, f) for d, _, fs in os.walk(org + "-witness/set_aside") for f in fs if f == "HOSTING.md"]
    ok("at the next close-out the seed's file is put back, and the changed version is kept in the witness folder",
       code == 0 and "A member's addition" not in open(os.path.join(org, "docs", "HOSTING.md"), encoding="utf-8").read()
       and any("A member's addition" in open(k, encoding="utf-8").read() for k in kept), out)
    os.remove(os.path.join(org, "notes.txt"))
    log(org, "event", {"type": "session_start", "summary": "Work left unsigned"})
    log(org, "proposal", {"kind": "rule", "target": "OUR-9", "change": "Add a rule", "why": "test",
                          "proposed_by": "member-1"})
    pid = last_id(org, "records/proposals.jsonl")
    log(org, "decision", {"question": "Do you adopt %s (add a rule)?" % pid, "proposal_ids": [pid], "framed_by": "member-1",
                          "decided_by": "founder", "decider_kind": "human", "right": "founder", "verdict": "adopted",
                          "words": "Yes, I adopt %s." % pid})
    did = last_id(org, "records/decisions.jsonl")
    write(org, "org/STATE.md", "# Current state\n\n## Waiting for close-out\n\n- %s, adopting %s\n" % (did, pid))
    log(org, "event", {"type": "session_start", "summary": "The next session, with no close-out between"})
    write(org, "org/STATE.md", "# Current state\n\nAll good.\n")
    code, out = py(org, "fos_check.py")
    ok("a STATE.md that drops a decision still waiting for signature is flagged", "no longer mentions %s" % did in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "y,y")
    body = git(org, "log", "-1", "--format=%B")[1]
    ok("the close-out's commit lists that decision from the records anyway",
       code == 0 and "Decided at this close-out (from the records)" in body and did in body, body)


def t_launch(org):
    print("Identity from the founder's launch, not from the member's say-so")
    log(org, "event", {"type": "session_start", "summary": "A session that adds a checker"})
    log(org, "proposal", {"kind": "role", "target": "checker", "change": "Add a checker role with one instance",
                          "why": "a second reading by another producer's model", "proposed_by": "member-1"})
    pid = last_id(org, "records/proposals.jsonl")
    log(org, "decision", {"question": "Do you adopt %s (add a checker role)?" % pid, "proposal_ids": [pid],
                          "framed_by": "member-1", "decided_by": "founder", "decider_kind": "human",
                          "right": "founder", "verdict": "adopted", "words": "Yes, I adopt %s." % pid})
    did = last_id(org, "records/decisions.jsonl")
    edit_config(org, lambda c: c["roles"].append({
        "id": "checker", "title": "Checker", "kind": "ai", "purpose": "Checks claims before the founder signs.",
        "trigger": {"on": "event", "when": "before the founder signs work"}, "output": "records/reviews.jsonl",
        "expected_every_sessions": None, "card": None,
        "instances": [{"id": "checker-1", "slot": {"producer": "Producer B", "model_id": "model-b-1",
                                                   "model_id_source": "founder", "agent_app": "App B", "host": "Host B"},
                       "adopted_by": did}], "adopted_by": did}))
    code, out = py(org, "fos_close.py", "--test-answers", "y,y")
    ok("a checker role with an instance on another producer's model is adopted and signed", code == 0, out)
    code, out = py(org, "fos_launch.py", "checker-1", stdin=subprocess.DEVNULL)
    ok("a launch runs only from the founder's terminal", code == 3, out)
    code, out = py(org, "fos_launch.py", "checker-1", "--model-id", "model-b-2", "--producer", "Producer B",
                   "--agent-app", "App B", "--host", "Host B", "--test-answers", "")
    line = next((x.split("FOS_LAUNCH=", 1)[1].strip() for x in out.splitlines() if x.strip().startswith("bash")), "")
    lid = line.split(":", 1)[0]
    ok("the launch is recorded in the records, and with its secret only in the witness folder",
       code == 0 and line.count(":") == 2 and os.path.exists(org + "-witness/launches/%s.json" % lid)
       and any(e.get("type") == "instance_launched" and e.get("launch_id") == lid for e in objs(org, "records/events.jsonl"))
       and line.split(":")[2] not in open(os.path.join(org, "records", "events.jsonl"), encoding="utf-8").read(), out)
    env = dict(ENV, FOS_LAUNCH=line)
    code, out = py(org, "fos_log.py", "event", "type=note", "summary=written by the launched checker", env=env)
    rec = objs(org, "records/events.jsonl")[-1]
    ident = rec.get("identity", {})
    ok("a launched member's record names the launched instance, the founder's statement of its model, and a fingerprint",
       code == 0 and ident.get("instance") == "checker-1" and ident.get("source") == "launch"
       and ident.get("model_id") == "model-b-2" and ident.get("model_id_source") == "founder"
       and ident.get("launch", {}).get("id") == lid and len(ident.get("launch", {}).get("mac", "")) == 64, json.dumps(rec))
    code, out = py(org, "fos_log.py", "event", "type=note", "summary=pretending", "instance=member-1", env=env)
    ok("a launched member cannot write as another instance", code == 1 and "launched as checker-1" in out, out)
    code, out = py(org, "fos_check.py")
    ok("the check verifies the fingerprint against the witness's copy",
       "verified against their launch" in out and "WRITER NOT AS CLAIMED" not in out, out)
    ok("and says the launch differs from the instance's model slot", "differs from its model slot" in out, out)
    ok("records with no launch are reported as unverified", "WRITER NOT VERIFIED" in out, out)
    forged = dict(rec, seq=max(e["seq"] for e in objs(org, "records/events.jsonl")) + 1, summary="forged in its name")
    forged["identity"] = dict(ident, launch={"id": lid, "mac": "0" * 64})
    write(org, "records/events.jsonl", json.dumps(forged) + "\n", mode="a")
    code, out = py(org, "fos_check.py")
    ok("a line that claims the launch without its secret fails the check", code == 1 and "WRITER NOT AS CLAIMED" in out, out)
    log(org, "event", {"type": "record_correction", "corrects": {"file": "records/events.jsonl", "seq": forged["seq"]},
                       "summary": "this line was not written by the launch it names", "captured_by": "founder"})
    code, out = py(org, "fos_check.py")
    ok("once a correction points to it, it is a corrected defect", code == 0 and "corrected defect" in out, out)
    no_test = dict(ENV)
    no_test.pop("SEED_SELFTEST")
    code, out = py(org, "fos_log.py", "event", "type=note", "summary=as if the founder", "instance=founder",
                   env=no_test, stdin=subprocess.DEVNULL)
    ok("an agent app cannot write a record in the founder's name", code == 1 and "own terminal" in out, out)
    py(org, "fos_close.py", "--test-answers", "y")


def t_claims(org):
    print("CK-1: quotations checked against their saved sources, and the check tested by a drill")
    write(org, "sources/council_report.md", "# Council report\n\nThe committee met eleven times in 2021 and approved "
                                            "four proposals — two of them after a public hearing.\n")
    claim = {"claim": "The committee met eleven times in 2021.", "cites": "Council report", "source_file":
             "sources/council_report.md", "quote": "The committee met eleven times in 2021", "location": "first paragraph",
             "finding_or_ours": "finding", "status": "verified", "instance": "member-1"}
    code, out = log(org, "claim", claim)
    rec = objs(org, "records/claims.jsonl")[-1]
    ok("a claim records the SHA-256 of its saved source", code == 0 and len(rec.get("source_sha256", "")) == 64, out)
    code, out = py(org, "fos_check.py")
    ok("a quotation that occurs in its source passes", "QUOTE NOT IN SOURCE" not in out, out)
    log(org, "claim", dict(claim, quote="four proposals - two of them after a public hearing"))
    log(org, "claim", dict(claim, quote="The committee met ... four proposals"))
    code, out = py(org, "fos_check.py")
    ok("typographic dashes and an ellipsis do not hide a true quotation", "QUOTE NOT IN SOURCE" not in out, out)
    log(org, "claim", dict(claim, claim="The committee met twelve times.", quote="The committee met twelve times in 2021"))
    bad = objs(org, "records/claims.jsonl")[-1]
    code, out = py(org, "fos_check.py")
    ok("a quotation that is not in its source fails the check (CK-1)",
       code == 1 and "QUOTE NOT IN SOURCE: claim %s" % bad["id"] in out, out)
    code, out = py(org, "fos_claims.py")
    ok("fos_claims shows the same, claim by claim", code == 1 and bad["id"] in out and "FAIL" in out, out)
    log(org, "event", {"type": "record_correction", "corrects": {"file": "records/claims.jsonl", "seq": bad["seq"]},
                       "summary": "the source says eleven, not twelve", "instance": "member-1"})
    code, out = py(org, "fos_check.py")
    ok("a corrected claim stays on record as a corrected defect", code == 0 and "corrected defect" in out, out)
    write(org, "sources/council_report.md", "\nA later line added to the saved source.\n", mode="a")
    code, out = py(org, "fos_check.py")
    ok("a saved source that changed after the claim is reported", "changed since the claim was recorded" in out, out)
    write(org, "org/GOAL.md", "# Goal\n\n### goal\nwords: To learn how the council's decisions changed across 2014 to "
                              "2022, and why.\nreason: To advise the next council.\nset_by: founder\n")
    write(org, "org/CHARTER.md", "# Charter\n\nGoal, in the founder's words: “how the council's decisions changed "
                                 "across 2014 to 2022”.\n")
    code, out = py(org, "fos_check.py")
    ok("a passage in org/ quoting the founder's own words passes", "QUOTE NOT FROM THE FOUNDER" not in out, out)
    code, out = py(org, "fos_drill.py", "plant", "--test-answers", "In org/CHARTER.md the quoted years now read 2012 to 2022")
    did = json.loads(lines(org, "records/drills.jsonl")[-1])["id"]
    write(org, "org/CHARTER.md", "# Charter\n\nGoal, in the founder's words: “how the council's decisions changed "
                                 "across 2012 to 2022”.\n")
    code, out = py(org, "fos_claims.py")
    ok("the planted misquotation in org/ is caught by CK-1", code == 1 and "org/CHARTER.md line 3" in out, out)
    code, out = py(org, "fos_drill.py", "reveal", did, "--test-answers", "y|CK-1")
    code, out = py(org, "fos_check.py")
    ok("so CK-1 is a tested check: a drill was revealed as caught by it",
       "QUOTE NOT FROM THE FOUNDER: org/CHARTER.md line 3" in out, out)
    write(org, "org/CHARTER.md", "# Charter\n\nGoal, in the founder's words: “how the council's decisions changed "
                                 "across 2014 to 2022”.\n")
    log(org, "review", {"check_id": "CK-1", "maker": "member-1", "checker": "checker-1", "object": "records/claims.jsonl",
                        "result": "pass", "instance": "checker-1"})
    code, out = py(org, "fos_check.py")
    ok("a checker that has not yet caught a drill is reported as untested", "UNTESTED CHECKER: checker-1" in out, out)
    py(org, "fos_drill.py", "plant", "--test-answers", "A date in a claim's sentence was changed")
    did = json.loads(lines(org, "records/drills.jsonl")[-1])["id"]
    py(org, "fos_drill.py", "reveal", did, "--test-answers", "y|checker-1")
    code, out = py(org, "fos_check.py")
    ok("once it catches one, it is no longer reported as untested", "UNTESTED CHECKER" not in out, out)


def t_seed_quotes(org):
    print("CK-1 tells a quotation of the seed's own text from a misquotation of the founder")
    state, letter = read(org, "org/STATE.md"), read(org, "org/LETTER_TO_NEXT_SESSION.md")
    write(org, "org/STATE.md", state + "\n- The founder answered \"Which decisions or tasks would you keep for yourself, "
                                       "whoever else was available?\" first.\n- \"What you keep for yourself\": "
                                       "the final word on claims.\n")
    write(org, "org/LETTER_TO_NEXT_SESSION.md", letter + "\nAsk again \"what would you keep for yourself\" if unsure.\n")
    exact = [i for i, ln in enumerate(read(org, "org/STATE.md").splitlines(), 1) if "The founder answered" in ln][0]
    code, out = py(org, "fos_check.py")
    ok("an exact quotation of the seed's interview question passes, and close quotations of it are not called the "
       "founder's misquotes", code == 0 and "QUOTE NOT FROM THE FOUNDER" not in out
       and "org/STATE.md line %d " % exact not in out, out)
    ok("a close quotation of the seed is a warning that names the seed's file and words",
       "QUOTES THE SEED, NOT THE FOUNDER: org/STATE.md" in out
       and "QUOTES THE SEED, NOT THE FOUNDER: org/LETTER_TO_NEXT_SESSION.md" in out
       and "onboarding/START.md" in out and "would you keep for yourself, whoever else was available" in out, out)
    write(org, "org/STATE.md", read(org, "org/STATE.md") + "- Goal: \"how the council's decisions changed across "
                                                         "2012 to 2022\"\n")
    code, out = py(org, "fos_check.py")
    code2, out2 = py(org, "fos_claims.py")
    ok("a misquotation of the founder still fails, in the check and in fos_claims",
       code == 1 and "QUOTE NOT FROM THE FOUNDER: org/STATE.md" in out and code2 == 1 and "FAIL org/STATE.md" in out2
       and "WARN org/STATE.md" in out2, out + out2)
    write(org, "org/STATE.md", state)
    write(org, "org/LETTER_TO_NEXT_SESSION.md", letter)
    code, out = py(org, "fos_check.py")
    ok("with the files as they were, the check passes again", code == 0, out)


def t_sources(org):
    print("Sources enter because the founder saved them or allowed a fetch that was logged; recall is never a source")
    page = "sources/example_2026_page.html"
    write(org, page, "<html><body><p>A page that was fetched.</p></body></html>\n")
    code, out = py(org, "fos_log.py", "event", "type=source_fetched", "url=https://example.org/page", "saved_as=" + page,
                   "summary=Fetched the example page", "instance=member-1")
    rec = objs(org, "records/events.jsonl")[-1]
    ok("a member logs a fetch with its address and saved file, and fos_log records the saved file's SHA-256",
       code == 0 and rec.get("type") == "source_fetched" and rec.get("url") == "https://example.org/page"
       and len(rec.get("saved_sha256", "")) == 64, out)
    code, out = py(org, "fos_check.py")
    ok("a logged fetch whose page is saved and unchanged raises nothing", code == 0 and "logs a fetch" not in out
       and "changed since it was fetched" not in out, out)
    original = read(org, page)
    write(org, page, "<p>edited later</p>\n", mode="a")
    log(org, "event", {"type": "source_fetched", "url": "https://example.org/other", "saved_as": "sources/other_page.html",
                       "summary": "A fetch whose page was not saved", "instance": "member-1"})
    code, out = py(org, "fos_check.py")
    ok("the check warns when a fetched page changed after it was saved, or was never saved",
       "%s changed since it was fetched from https://example.org/page" % page in out
       and "saved as sources/other_page.html, which is not in the folder" in out, out)
    write(org, page, original)
    write(org, "sources/other_page.html", "<p>saved afterwards</p>\n")
    code, out = py(org, "fos_check.py")
    ok("once the pages are saved as fetched, those warnings go", code == 0 and "changed since it was fetched" not in out
       and "which is not in the folder" not in out, out)
    readme, start, agents = read(org, "README.md"), read(org, "onboarding/START.md"), read(org, "AGENTS.md")
    step3 = start.split("## ▶ 3.", 1)[1].split("\n## ", 1)[0]
    ok("README and the first session say plainly how sources enter: saved by the founder, or fetched with the founder's "
       "leave and logged; and that what a member remembers is never a source",
       "## How sources enter the organization" in readme and "**You save them.**" in readme
       and "**The member fetches them, if you allow it.**" in readme and "logs every fetch" in readme
       and "What a member remembers is never a source" in readme and "log every fetch" in step3
       and "type=source_fetched" in step3 and "What you remember is never a source" in step3
       and "What you remember is never a source" in agents)


def t_small(org):
    print("Small fixes: a record that fits no schema, line endings, charter items, the goal's decision")
    seq = max(o["seq"] for o in objs(org, "records/declines.jsonl")) + 1
    write(org, "records/declines.jsonl", json.dumps({"seq": seq, "id": None, "what": None}) + "\n", mode="a")
    code, out = py(org, "fos_render.py")
    ok("the view is drawn even when a record fits no schema", code == 0 and "wrote view/org_view.html" in out, out)
    log(org, "event", {"type": "record_correction", "corrects": {"file": "records/declines.jsonl", "seq": seq},
                       "summary": "a hand-written line that fits no schema", "instance": "member-1"})
    py(org, "fos_rules.py")
    py(org, "fos_render.py")
    for rel in ("org/config.json", "org/RULES_IN_FORCE.md", "view/org_view.html"):
        p = os.path.join(org, *rel.split("/"))
        data = open(p, "rb").read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        open(p, "wb").write(data)
    code, out = py(org, "fos_check.py")
    ok("files checked out with CRLF line endings are not reported out of date",
       "RULES_IN_FORCE.md is out of date" not in out and "the view is out of date" not in out, out)
    fd = json.loads(read(org, "org/config.json"))["organization"]["founding_decision"]   # founded in t_session
    write(org, "org/CHARTER.md", "# Charter\n\n### NG-1 Learn the field\ngoal: map the sources\nkind: learn\n"
                                 "done_when: ten sources saved\n\n### NG-2 A first table\ngoal: a table\nkind: produce\n"
                                 "done_when: the table exists\nadopted_by: D-9999\n")
    code, out = py(org, "fos_check.py")
    ok("a charter item with no adopted_by is reported, naming the founding decision",
       "NG-1 has no adopted_by" in out and fd in out, out)
    ok("a charter item adopted by no signed decision fails", code == 1 and "NG-2: adopted_by D-9999" in out, out)
    ok("a founded organization whose goal does not name its decision is told so",
       "org/GOAL.md's decision field" in out, out)
    write(org, "org/CHARTER.md", "# Charter\n\n### NG-1 Learn the field\ngoal: map the sources\nkind: learn\n"
                                 "done_when: ten sources saved\nadopted_by: %s\n" % fd)
    write(org, "org/GOAL.md", open(os.path.join(org, "org", "GOAL.md"), encoding="utf-8").read() + "decision: %s\n" % fd)
    code, out = py(org, "fos_check.py")
    ok("with the decision named in both places, those notices go", code == 0 and "NG-1 has no adopted_by" not in out
       and "org/GOAL.md's decision field" not in out, out)
    py(org, "fos_close.py", "--test-answers", "y")


def t_crate(tmp, org):
    print("Export as an RO-Crate with a PROV file, from the witnessed history only")
    marks = {k: "%s-%s" % (k, os.urandom(6).hex()) for k in ("sealed", "transcript", "uncommitted")}
    py(org, "fos_drill.py", "plant", "--test-answers", marks["sealed"] + " changed a count in work/")
    write(org + "-witness", "transcripts/session.txt", marks["transcript"] + " of a session\n")
    log(org, "event", {"type": "session_start", "summary": "Before the export", "instance": "member-1"})
    py(org, "fos_close.py", "--test-answers", "y")
    write(org, "work/uncommitted.md", marks["uncommitted"] + " not yet closed out\n")
    out1, out2 = os.path.join(tmp, "crate1"), os.path.join(tmp, "crate2")
    code, out = py(org, "fos_crate.py", out1)
    ok("fos_crate writes a crate outside the folder", code == 0 and os.path.exists(os.path.join(out1, "ro-crate-metadata.json"))
       and os.path.exists(os.path.join(out1, "prov", "run.prov.jsonld")), out)
    py(org, "fos_crate.py", out2)

    def tree(d):
        got = {}
        for root, _, fs in os.walk(d):
            for f in fs:
                p = os.path.join(root, f)
                got[os.path.relpath(p, d).replace("\\", "/")] = open(p, "rb").read()
        return got
    t1, t2 = tree(out1), tree(out2)
    ok("the same revision gives the same bytes", t1 == t2 and len(t1) > 20, "%d vs %d files" % (len(t1), len(t2)))
    crate = json.loads(t1["ro-crate-metadata.json"])
    nodes = {n["@id"]: n for n in crate["@graph"]}
    root = nodes.get("./", {})

    def ids(v):
        return [x["@id"] for x in (v if isinstance(v, list) else [v]) if isinstance(x, dict)]
    ok("it declares RO-Crate 1.3 and the Process Run Crate 0.6 profile",
       crate["@context"] == "https://w3id.org/ro/crate/1.3/context"
       and nodes["ro-crate-metadata.json"]["conformsTo"] == {"@id": "https://w3id.org/ro/crate/1.3"}
       and root.get("conformsTo") == {"@id": "https://w3id.org/ro/wfrun/process/0.6"} and root.get("datePublished"))
    creates = [n for n in nodes.values() if n.get("@type") == "CreateAction"]
    ok("every CreateAction has an identifier and an instrument, and the root mentions it",
       creates and all(n.get("instrument") for n in creates) and set(n["@id"] for n in creates) <= set(ids(root.get("mentions"))))
    committed = {rel: git(org, "show", "HEAD:" + rel)[1] for rel in L.RECORD_FILES.values()}
    rec_ok = all(nodes.get(rel, {}).get("sha256") == L.hashlib.sha256(open(os.path.join(out1, *rel.split("/")), "rb")
                                                                      .read()).hexdigest() for rel in committed)
    ok("every records file is in the crate with its SHA-256", rec_ok and set(committed) <= set(ids(root.get("hasPart"))))
    prov = json.loads(t1["prov/run.prov.jsonld"])
    lines_n = sum(len(objs(out1, rel)) for rel in committed)
    ents = [n for n in prov["@graph"] if n["@id"].startswith("records/") and "#" in n["@id"]]
    ok("the PROV file holds every record line as an entity, attributed to its writer",
       len(ents) == lines_n and all(e.get("prov:wasAttributedTo") for e in ents), "%d entities, %d lines" % (len(ents), lines_n))
    blob = b"".join(t1.values())
    ok("no transcript, no sealed drill text and nothing uncommitted is in the crate",
       not any(m.encode() in blob for m in marks.values()), str(marks))
    out3 = os.path.join(tmp, "crate3")
    code, out = py(org, "fos_crate.py", out3, "--with-pushlog")
    ok("with --with-pushlog, the witness's push log travels with it", code == 0
       and os.path.exists(os.path.join(out3, "witness_pushlog.jsonl")), out)
    os.remove(os.path.join(org, "work", "uncommitted.md"))
    for d in (out1, out2, out3):
        rmtree(d)
    os.remove(os.path.join(org, "records", "dissent.jsonl"))
    code, out = py(org, "fos_check.py")
    code_w, out_w = py(org, "fos_check.py", "--from-witness")
    ok("--from-witness gives a verdict from witnessed history only, whatever this folder holds",
       code == 1 and code_w == 0 and "From a fresh clone of the witness" in out_w and "dissent.jsonl is missing" not in out_w,
       out_w)
    git(org, "checkout", "--", "records/dissent.jsonl")


def t_ledgers(org):
    print("Pins, claims about members, a member's own producer, deviations, successes, a hand-back explained")
    log(org, "event", {"type": "session_start", "summary": "A session with new ledgers", "instance": "member-1"})
    code, out = log(org, "pin", {"words": "Let's come back to the funding question after the pilot.",
                                 "trigger": "after the pilot's close-out", "state": "open", "captured_by": "founder"})
    pid = objs(org, "records/pins.jsonl")[-1]["id"]
    code, out = py(org, "fos_check.py")
    ok("an open pin is raised by the check, in the founder's words", "pin %s is open" % pid in out
       and "funding question" in out, out)
    code, out = py(org, "fos_roles.py")
    ok("and by the roll-call", pid in out, out)
    log(org, "pin", {"id": pid, "words": "Let's come back to the funding question after the pilot.",
                     "trigger": "after the pilot's close-out", "state": "revisited", "outcome": "discussed",
                     "captured_by": "founder"})
    code, out = py(org, "fos_check.py")
    ok("once revisited, it is no longer raised", "pin %s is open" % pid not in out, out)
    log(org, "claim", {"claim": "The checker missed one planted fault.", "status": "lead", "about_member": True,
                       "instance": "member-1"})
    code, out = py(org, "fos_check.py")
    ok("a claim about a member's behaviour without its run count is flagged (CLM-9)",
       "does not say how many runs it rests on" in out, out)
    log(org, "review", {"check_id": "CK-1", "maker": "member-1", "checker": "checker-1", "object": "work/",
                        "result": "findings", "findings": "The comparison favours Producer B's newest model.",
                        "instance": "checker-1"})
    code, out = py(org, "fos_check.py")
    ok("a member's work that names its own producer is flagged (MBR-9)", "names its own producer (Producer B)" in out, out)
    code, out = log(org, "deviation", {"what_changed": "member-1 moved to a newer model", "class": "forced",
                                       "forced_by": "the producer retired the earlier model", "outcome_seen": False,
                                       "instance": "member-1"})
    ok("a deviation is recorded with its kind", code == 0, out)
    code, out = log(org, "success", {"what_went_well": "CK-1 caught a planted misquotation",
                                     "evidence": ["records/drills.jsonl"], "lesson": "keep the quotation check on",
                                     "instance": "member-1"})
    ok("a success is recorded beside declines and corrections", code == 0, out)
    log(org, "proposal", {"kind": "rule", "target": "OUR-2", "change": "Save every source as text too",
                          "why": "so quotations can be checked", "proposed_by": "member-1", "instance": "member-1",
                          "background": "A PDF cannot be read by the check; a text copy beside it can.",
                          "if_undecided": "PDFs stay unchecked", "cost_of_waiting": "none this week"})
    pid = last_id(org, "records/proposals.jsonl")
    log(org, "decision", {"question": "Do you adopt %s (save sources as text too)?" % pid, "proposal_ids": [pid],
                          "framed_by": "member-1", "decided_by": "founder", "decider_kind": "human", "right": "founder",
                          "verdict": "adopted", "words": "Yes, I adopt %s." % pid, "instance": "member-1"})
    code, out = py(org, "fos_close.py", "--test-answers", "y,y")
    ok("the close-out shows the founder the background, the default and the cost of waiting",
       code == 0 and "Background:  A PDF cannot be read" in out and "If nobody decides: PDFs stay unchecked" in out, out)
    ok("a decision with no warning, changing no one's rights, is in the routine group the founder may sign together",
       "Routine (1)" in out and "Sign all 1 routine decisions together?" in out, out)


def t_governance(org):
    print("Governance")
    set_module(org, "norms", "on", None)
    code, out = py(org, "fos_check.py")
    ok("structure switched on with no decision is PROPOSAL-ONLY", code == 1 and "PROPOSAL-ONLY" in out, out)
    set_module(org, "norms", "off", None)
    os.makedirs(os.path.join(org, "tools", "scraper"))
    write(org, "tools/scraper/run.py", "print('x')\n")
    code, out = py(org, "fos_check.py")
    ok("an unregistered tool folder is flagged", "tools/scraper has no row" in out, out)
    p = os.path.join(org, "org", "TOOLS.json")
    reg = json.load(open(p, encoding="utf-8"))
    reg["tools"].append({"id": "scraper", "path": "tools/scraper/run.py", "tier": "seed", "status": "active",
                         "purpose": "x", "adopted_by": "seed"})
    write(org, "org/TOOLS.json", json.dumps(reg, indent=2))
    code, out = py(org, "fos_check.py")
    ok("a tool falsely claiming to be a seed tool fails", code == 1 and "claims to be a seed tool" in out, out)
    reg["tools"].pop()
    write(org, "org/TOOLS.json", json.dumps(reg, indent=2) + "\n")
    rmtree(os.path.join(org, "tools", "scraper"))
    signed = [s["decision_id"] for s in objs(org, "records/signatures.jsonl") if s.get("answer") == "signed"]
    write(org, "tools/counter/run.py", "print(len(open('records/claims.jsonl').readlines()))\n")
    reg = json.load(open(p, encoding="utf-8"))
    reg["tools"].append({"id": "counter", "path": "tools/counter/run.py", "tier": 1, "status": "active",
                         "purpose": "counts claims", "adopted_by": signed[-1],
                         "builder": {"instance": "member-1"}, "tester": {"instance": "checker-1"},
                         "code_sha256": L.hashlib.sha256(open(os.path.join(org, "tools", "counter", "run.py"), "rb")
                                                         .read()).hexdigest()})
    write(org, "org/TOOLS.json", json.dumps(reg, indent=2) + "\n")
    code, out = py(org, "fos_check.py")
    ok("an approved tool whose code still matches its code_sha256 is accepted", "tool counter" not in out, out)
    write(org, "tools/counter/run.py", "import os; os.remove('records/claims.jsonl')\n")
    code, out = py(org, "fos_check.py")
    ok("a tool whose code changed after approval is no longer approved",
       code == 1 and "tool counter: its code (tools/counter/run.py) changed since it was approved" in out, out)
    reg["tools"].pop()
    write(org, "org/TOOLS.json", json.dumps(reg, indent=2) + "\n")
    rmtree(os.path.join(org, "tools", "counter"))


def t_drills(org):
    print("Drills")
    code, out = py(org, "fos_drill.py", "plant", stdin=subprocess.DEVNULL)
    ok("planting refuses to run without a terminal", code == 3, out)
    code, out = py(org, "fos_drill.py", "plant", "--test-answers", "The count in work/table.md was changed from 88 to 89")
    d = json.loads(lines(org, "records/drills.jsonl")[-1])
    d1 = d.get("id")
    ok("the founder plants a sealed drill", code == 0 and "%s planted" % d1 in out, out)
    ok("the records hold only the seal", "description" not in d and len(d.get("seal", "")) == 64)
    ok("the description is outside the folder", os.path.exists(org + "-witness/drills/%s.json" % d1))
    code, out = py(org, "fos_drill.py", "reveal", d1, "--test-answers", "y|checker")
    ok("revealed, and its seal verifies", code == 0 and py(org, "fos_check.py")[0] == 0, out)
    py(org, "fos_drill.py", "plant", "--test-answers", "A date in org/STATE.md was moved by two years")
    d2 = json.loads(lines(org, "records/drills.jsonl")[-1])["id"]
    code, out = py(org, "fos_drill.py", "reveal", d2, "--test-answers", "n")
    rev = [d for d in objs(org, "records/drills.jsonl") if d.get("id") == d2 and d.get("action") == "revealed"]
    ok("a drill nobody caught is revealed as missed, and the miss is on record",
       code == 0 and "MISSED" in out and rev and rev[0]["outcome"] == "missed" and "caught_by" not in rev[0], out)
    code, out = py(org, "fos_check.py")
    ok("a missed drill passes the seal check", code == 0, out)
    py(org, "fos_drill.py", "plant", "--test-answers", "A quotation in work/notes.md was altered")
    d3 = json.loads(lines(org, "records/drills.jsonl")[-1])["id"]
    kept = org + "-witness/drills/%s.json" % d3
    k = json.load(open(kept, encoding="utf-8"))
    k["description"] = "Something easier to have caught"
    json.dump(k, open(kept, "w", encoding="utf-8"))
    py(org, "fos_drill.py", "reveal", d3, "--test-answers", "y|member-1")
    code, out = py(org, "fos_check.py")
    ok("a description changed after planting is caught", code == 1 and "does not match the seal" in out, out)


def t_export(tmp, org):
    print("Export")
    out_b = os.path.join(tmp, "export.bundle")
    code, out = py(org, "fos_export.py", out_b, "--zip")
    ok("fos_export writes a bundle and its relocation note", code == 0 and os.path.exists(out_b + ".RELOCATION.md"), out)
    code, out = run(["git", "-C", org, "bundle", "verify", out_b], org)
    ok("the bundle verifies", code == 0, out)
    clone = os.path.join(tmp, "moved")
    code, out = run(["git", "clone", "-q", out_b, clone], tmp)
    ok("it clones into a new folder", code == 0, out)
    code, out = py(clone, "fos_check.py")
    ok("the moved organization keeps its birth hash and records", "the first commit was replaced" not in out
       and "records: " in out, out)
    ok("and says it has no witness yet", "UNWITNESSED" in out, out)
    code, out = py(clone, "fos_render.py")
    ok("its view shows it as unwitnessed", "UNWITNESSED" in open(os.path.join(clone, "view", "org_view.html"), encoding="utf-8").read())


def t_release(tmp, seed, org):
    print("Release for publication: the last commit's files in one new commit, with nothing that identifies")
    import calendar
    rs = os.path.join(tmp, "rel-seed")
    shutil.copytree(seed, rs)
    write(rs, ".env", "KEPT_OUT=1\n")                          # ignored files must not travel
    write(rs, "scripts/__pycache__/x.pyc", "cache\n")
    date, epoch = "2026-01-01T00:00:00Z", calendar.timegm((2026, 1, 1, 0, 0, 0, 0, 0, 0))
    name = json.load(open(os.path.join(rs, "seed.json"), encoding="utf-8"))["name"]
    ident = "%s authors <anonymous%sexample.invalid>" % (name, "@")
    target = os.path.join(tmp, "release")
    code, out = py(rs, "release_export.py", target, "--date", date)
    ok("release_export makes a release, and its scan finds nothing to block",
       code in (0, 1) and "BLOCK: 0" in out and "Released" in out, out)
    ok("ignored files stay behind", not os.path.exists(os.path.join(target, ".env"))
       and not os.path.exists(os.path.join(target, "scripts", "__pycache__")))
    raw = git(target, "cat-file", "commit", "HEAD")[1]
    ok("exactly one commit, with no parent, by the neutral identity, at the fixed date in UTC",
       git(target, "rev-list", "--all", "--count")[1].strip() == "1" and "\nparent " not in raw
       and "author %s %d +0000\n" % (ident, epoch) in raw and "committer %s %d +0000\n" % (ident, epoch) in raw, raw)
    ok("its tree is the seed's last tree, byte for byte",
       git(target, "rev-parse", "HEAD^{tree}")[1].strip() == git(rs, "rev-parse", "HEAD^{tree}")[1].strip())
    listed = [ln for ln in out.splitlines() if len(ln) > 66 and ln[64:66] == "  " and all(c in "0123456789abcdef" for c in ln[:64])]
    ok("no remote, no other branch or tag; the manifest gives every file's hash",
       not git(target, "remote")[1].strip() and git(target, "for-each-ref", "--format=%(refname)")[1].split() == ["refs/heads/main"]
       and len(listed) == len(git(target, "ls-files")[1].split()) > 0, out)
    code, out2 = py(rs, "release_export.py", "--scan", target)
    ok("--scan of the release: nothing to block, one commit", code in (0, 1) and "BLOCK: 0" in out2 and "1 commit(s)" in out2, out2)
    first = git(target, "rev-parse", "HEAD")[1].strip()
    code, out2 = py(rs, "release_export.py", target, "--date", date)
    ok("an earlier release is not replaced without --replace", code == 2 and "--replace" in out2, out2)
    code, out2 = py(rs, "release_export.py", target, "--date", date, "--replace")
    ok("the same seed commit and date give the same commit id", code in (0, 1)
       and git(target, "rev-parse", "HEAD")[1].strip() == first, out2)
    r2 = os.path.join(tmp, "r2")
    c1, o1 = py(rs, "release_export.py", r2)
    c2, o2 = py(rs, "release_export.py", r2, "--date", "2026-01-01T00:00:00" + "+02:00")
    ok("a release needs a fixed date, in UTC", c1 == 2 and c2 == 2 and not os.path.exists(r2), o1 + o2)
    code, out2 = py(rs, "release_export.py", os.path.join(rs, "inside"), "--date", date)
    ok("a release is never written inside the seed", code == 2 and not os.path.exists(os.path.join(rs, "inside")), out2)
    other = os.path.join(tmp, "someone-else")
    write(other, "keep.txt", "mine\n")
    code, out2 = py(rs, "release_export.py", other, "--date", date, "--replace")
    ok("--replace deletes only a folder this script made", code == 2 and os.path.exists(os.path.join(other, "keep.txt")), out2)
    write(rs, "terms.json", json.dumps({"block": ["x"]}))
    code, out2 = py(rs, "release_export.py", os.path.join(tmp, "r3"), "--date", date, "--terms", os.path.join(rs, "terms.json"))
    ok("the term list must be kept outside the seed", code == 2 and "outside the seed" in out2, out2)
    os.remove(os.path.join(rs, "terms.json"))
    write(rs, "README.md", "\nchanged\n", mode="a")
    code, out2 = py(rs, "release_export.py", os.path.join(tmp, "r3"), "--date", date)
    ok("uncommitted changes are refused: a release is made from the last commit only",
       code == 2 and "uncommitted" in out2 and not os.path.exists(os.path.join(tmp, "r3")), out2)
    git(rs, "checkout", "--", "README.md")
    code, out2 = py(org, "release_export.py", os.path.join(tmp, "r4"), "--date", date)
    ok("an organization born from the seed is refused: its history is its record",
       code == 2 and "fos_export" in out2 and not os.path.exists(os.path.join(tmp, "r4")), out2)
    # Identifying strings, put together at run time so that this file never contains them.
    at, bs = "@", "\\"
    planted = [("e-mail", "Write to jane.doe" + at + "mail-host.com about it."),
               ("user path", "Saved in C:" + bs + "Users" + bs + "jdoe" + bs + "notes.txt"),
               ("time zone", "Run at 2025-12-04T05:06:07" + "-05:00 on the laptop."),
               ("IP address", "The printer is at 10.1." + "2.3 on the home network."),
               ("key-like", "token gh" + "p_" + "Ab3" * 12),
               ("machine name", "Built on DESKTOP-" + "AB12CD3."),
               ("ORCID iD", "iD 0000-0002-" + "1825-0097"),
               ("term list (test)", "Thanks to Zebra" + " Corp for the help.")]
    write(rs, "docs/planted.md", "\n".join(t for _, t in planted) + "\n")
    git(rs, "add", "-A")
    git(rs, "commit", "-q", "-m", "plant identifying strings")
    write(tmp, "terms.json", json.dumps({"block": {"test": ["Zebra ?Corp"]}, "review": [], "allow": []}))
    code, out2 = py(rs, "release_export.py", target, "--date", date, "--replace", "--terms", os.path.join(tmp, "terms.json"))
    missed = [c for c, _ in planted if "[%s] docs/planted.md" % c not in out2]
    ok("planted strings are each caught: " + ", ".join(c for c, _ in planted), code == 2 and not missed,
       "missed: %s\n%s" % (missed, out2))
    ok("and nothing is committed when one is found", "Nothing was committed" in out2
       and git(target, "rev-parse", "-q", "--verify", "HEAD")[0] != 0, out2)


def t_view(org):
    print("The view")
    write(org, "org/GOAL.md", "# Goal\n\n### goal\nwords: <script>alert(1)</script> and a goal\n")
    py(org, "fos_render.py")
    v1 = open(os.path.join(org, "view", "org_view.html"), encoding="utf-8").read()
    py(org, "fos_render.py")
    v2 = open(os.path.join(org, "view", "org_view.html"), encoding="utf-8").read()
    ok("no scripts in the view", "<script" not in v1.lower())
    ok("text is escaped", "&lt;script&gt;" in v1)
    ok("a content-security policy forbids loading anything", "default-src 'none'" in v1)
    ok("the same files draw the same view", v1 == v2)
    ok("the frame shows the birth hash", "birth hash" in v1)


def t_nogit(tmp, seed):
    print("Without git")
    env = dict(ENV, SEED_NO_GIT="1")
    org = os.path.join(tmp, "plain")
    code, out = py(seed, "fos_init.py", org, env=env)
    ok("birth without git, with a computed birth hash", code == 0 and "computed seed tree" in out, out)
    s_tree = git(seed, "rev-parse", "HEAD^{tree}")[1].strip()
    ok("the computed hash equals git's tree id", s_tree in out, "%s / %s" % (s_tree, out))
    code, out = py(org, "fos_check.py", env=env)
    ok("the check runs without git", code == 0, out)
    log2 = lambda k, r: run([PY, os.path.join(org, "scripts", "fos_log.py"), k, "--json", "-"], org, env=env,  # noqa: E731
                            data=json.dumps(r).encode("utf-8"))
    log2("event", {"type": "session_start", "summary": "Opened"})
    code, out = py(org, "fos_close.py", "--test-answers", "y", env=env)
    ok("the close-out keeps a dated copy in the witness folder", code == 0 and "snapshot written" in out, out)
    os.remove(os.path.join(org, "records", "claims.jsonl"))
    code, out = py(org, "fos_check.py", env=env)
    ok("a deleted file is caught against the copy", code == 1 and "claims.jsonl is missing" in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "y", env=env)
    ok("and restored from it", code == 0 and os.path.exists(os.path.join(org, "records", "claims.jsonl")), out)
    write(org, "records/events.jsonl", "{\n  \"note\": \"whole-file write\"\n}\n")
    code, out = py(org, "fos_check.py", env=env)
    ok("without git, a lost birth record is read from the witness's dated copy",
       code == 1 and "BIRTH RECORD LOST" in out and "birth read from the witness" in out, out)
    code, out = py(org, "fos_close.py", "--test-answers", "y", env=env)
    ok("and the close-out restores it from that copy", code == 0 and "seed itself" not in out
       and any(e.get("type") == "born" for e in objs(org, "records/events.jsonl")), out)


def t_rename(tmp, seed):
    print("Rename")
    copy = os.path.join(tmp, "renamed")
    shutil.copytree(seed, copy)
    code, out = py(copy, "rename.py", "--list")
    old = json.load(open(os.path.join(copy, "seed.json"), encoding="utf-8"))["name"]
    ok("--list names every occurrence", code == 0 and "seed.json" in out, out)
    code, out = py(copy, "rename.py", "Test Seed Name", "--prefix", "tsn")
    left = run(["git", "-C", copy, "grep", "-l", old], copy)[1].strip()
    ok("the old name is gone from every file", code == 0 and not left, left or out)
    ok("the scripts were renamed", os.path.exists(os.path.join(copy, "scripts", "tsn_check.py")))
    code, out = run([PY, os.path.join(copy, "scripts", "tsn_check.py")], copy)
    ok("the renamed check still runs", code == 0, out)


def main(argv):
    if not (L.git_ok()):
        print("The self-test needs git (it tests the witness and the history).")
        return 2
    tmp = tempfile.mkdtemp(prefix="seed-selftest-")
    print("Self-test in %s" % tmp)
    try:
        seed = make_seed(tmp)
        org = os.path.join(tmp, "org")
        # The founding comes first, and so do its tests: each builds its own organization from the seed, so a
        # failure there shows in the first few minutes of a run that takes much longer.
        t_founding_first(tmp, seed)
        t_founding_void(tmp, seed)
        t_founding_backdating(tmp, seed)
        t_founding_labels(tmp, seed)
        t_founding_guards(tmp, seed)
        t_birth(seed, org)
        t_init_atomic(tmp, seed)
        t_continuity(tmp, seed)
        t_listening(seed)
        t_pointers(tmp, seed)
        t_zip(tmp, seed)
        t_launchers(tmp, seed)
        t_study(tmp, seed)
        t_enforcement(tmp, seed)
        t_change_loop(tmp, seed)
        t_app_instructions(tmp, seed)
        t_session(org)
        t_batch(org)
        t_log_refusals(org)
        t_close(org)
        t_corrections(org)
        t_witness_refusals(org)
        t_parallel(tmp, org)
        t_repair(org)
        t_forgery(org)
        t_birth_lost(org)
        t_sessions(org)
        t_fail_before_sign(org)
        t_selective(org)
        t_launch(org)
        t_claims(org)
        t_seed_quotes(org)
        t_sources(org)
        t_small(org)
        t_crate(tmp, org)
        t_ledgers(org)
        t_governance(org)
        t_drills(org)
        t_view(org)
        t_export(tmp, org)
        t_release(tmp, seed, org)
        t_nogit(tmp, seed)
        t_rename(tmp, seed)
    finally:
        if "--keep" in argv:
            print("kept: %s" % tmp)
        else:
            rmtree(tmp)
    failed = [r for r in RESULTS if not r[1]]
    print("\n%d checks, %d passed, %d failed" % (len(RESULTS), len(RESULTS) - len(failed), len(failed)))
    if "--json" in argv:
        # One line per check, for comparing a reviewer's run with the expected results shipped with the seed
        # (docs/SELFTEST_EXPECTED.json): python scripts/fos_selftest.py --json results.json
        i = argv.index("--json")
        target = argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith("--") else None
        doc = {"checks": [{"check": name, "result": "pass" if passed else "fail"} for name, passed, _ in RESULTS],
               "passed": len(RESULTS) - len(failed), "failed": len(failed)}
        text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
        if target:
            with open(target, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            print("results written to %s" % target)
        else:
            print(text)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
