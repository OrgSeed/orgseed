"""Check the organization: its records, their whole history, the witness, and its governance.

Usage:  python scripts/fos_check.py [--json] [--from-witness]
        python scripts/fos_check.py --resume

--from-witness clones the witness into a temporary folder and runs the copy of this check found there, so the verdict
rests on witnessed history only (this folder's own state, committed or not, plays no part).
--resume prints, for a member opening a new session, what the last session left: the letter to the next session,
the state, the decisions the founder signed (with the founder's words), what is not yet signed, and the open
proposals. It checks nothing and changes nothing.

Its report names the file a member opening a new session follows ("next:"): the first session only while no
session is on record, and session start after that, founded or not.

It reads the disk, never a member's account. In order:
  1. Records: every records file exists (a missing one was deleted); every line is valid JSON
     and fits its schema; seq numbers rise; IDs are unique. A bad line or record that a later
     record_correction event points to (by seq, or by line number) is a corrected defect: a
     warning, not a failure.
  2. History (needs git): no records line was edited or removed since the last commit, and no
     commit in the whole history deleted a records file or changed one other than by appending.
     The first commit still has the tree its birth record names (the birth hash).
  3. The witness: it exists outside the folder, still refuses rewrites and deletions, and this
     folder's history still contains everything the witness holds.
  4. Stage: the seed itself, born, or founded; activity with no session recorded is reported.
  5. Decisions: each question names the proposals by ID; generic replies ("sounds great", "ok")
     are flagged; signatures match the decision lines they sign. Proposals whose structure is adopted say
     what they change for the founder and how they are undone; a grounding marked read has its saved copy.
  6. Governance: every structural item is adopted by a decision the founder signed. Items whose
     decision awaits signature are provisional; items with no decision are PROPOSAL-ONLY. The founding
     comes first, as one invariant on files and history: no commit holds the structural files changed
     from birth unless an earlier commit founds the organization, a close-out at which the founder
     typed FOUND (step 2 fails it; the witness refuses it). Founded is read from that history only.
     Decisions whose labels adopt structure before the founding are warnings only.
  7. Claims: every URL, DOI, arXiv ID or ISBN in work/ has a claims.jsonl line (CORE-13); CK-1: every
     verified claim's quotation occurs in its saved source, and every passage quoted in org/ is the
     founder's own words or a saved source's. (Off only in a research configuration made at birth.)
  8. Folders: docs/ and the seed's own files unchanged since birth; work goes in work/.
  9. Tools, drills, roles: the registry (with code hashes), enforcement add-ons declared in it (what they cover,
     and every recorded decline that names one; an add-on's own log, outside the folder, is the full count),
     sealed drills, untested checkers, the role roll-call, open pins.
 10. Writers: each AI member's record verified against its launch fingerprint, or reported unverified;
     launches and stated identities compared with the model slots.
The birth is read from the history ([BIRTH] commit) or the witness, never from events.jsonl alone.
Exit code 0 when nothing failed, 1 otherwise. Standard library only; no network.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402
import fos_witness as W  # noqa: E402

COMMIT_TYPES = ("SEED", "BIRTH", "CLOSE", "FOUND", "PROPOSE", "DECIDE", "STRUCTURE", "MEMBER", "RULE", "TOOL",
                "WORK", "DECLINE", "CORRECT", "RECALL", "SIGN", "SESSION", "DRILL", "VIEW", "REPAIR", "RELOCATE")
ORG_FOLDERS = ("org", "records", "work", "sources", "archive", "tools", "view")
SEED_AREAS = ("AGENTS.md", "scripts", "schemas", "onboarding", "modules", "docs", "addons")
# The files that point apps to AGENTS.md (docs/HARNESS_NOTES.md): changed, they could load something else at boot.
POINTER_FILES = ("CLAUDE.md", "GEMINI.md", ".cursorrules", ".windsurfrules", "CONVENTIONS.md",
                 ".github/copilot-instructions.md")


class Result:
    def __init__(self):
        self.fails, self.warns, self.notes, self.summary = [], [], [], {}
        self.info = {}
        self.item_fails = []      # (kind, label, message): failures that belong to one structural item
        self.decision_fails = {}  # decision id -> [message]: failures that belong to one decision

    def fail_item(self, kind, label, message):
        self.fails.append(message)
        self.item_fails.append((kind, label, message))

    def fail_decision(self, did, message):
        self.fails.append(message)
        self.decision_fails.setdefault(did, []).append(message)

    @property
    def ok(self):
        return not self.fails


def _norm_records_path(f):
    f = (f or "").replace("\\", "/").lstrip("./")
    return f if f.startswith("records/") else "records/" + f


def corrections_index(events):
    idx = {}
    for e in events:
        c = e.get("corrects")
        if e.get("type") != "record_correction" or not isinstance(c, dict) or not c.get("file"):
            continue
        f = _norm_records_path(c["file"])
        for k in ("seq", "line"):
            if isinstance(c.get(k), int):
                idx[(f, k, c[k])] = e.get("seq")
    return idx


BASE = {"rev": None}     # a research configuration counts the seed's files from its [STUDY] commit


def _lines_since_birth(area):
    """Paths under area changed since the first commit (or the [STUDY] commit), plus untracked ones."""
    root = BASE["rev"] or L.root_commit()
    out = set()
    if root:
        code, txt = L.git("diff", "--name-only", root, "--", area)
        if code == 0:
            out.update(x for x in txt.splitlines() if x.strip())
    code, txt = L.git("ls-files", "--others", "--exclude-standard", "--", area)
    if code == 0:
        out.update(x for x in txt.splitlines() if x.strip())
    return sorted(out)


def check_records(R, records, corr):
    for kind, rel in L.RECORD_FILES.items():
        p = records[kind]
        if p.missing:
            R.fails.append("%s is missing: a records file was deleted (CORE-4). The founder's close-out offers to "
                           "restore it from the last commit." % rel)
            continue
        for ln, raw, msg in p.bad:
            if (rel, "line", ln) in corr:
                R.warns.append("corrected defect: %s line %d is %s (corrected by event seq %s)"
                               % (rel, ln, msg, corr[(rel, "line", ln)]))
            else:
                R.fails.append("%s line %d is %s. Leave it, and append a record_correction event that points to "
                               "it, e.g. python scripts/fos_log.py event type=record_correction "
                               "corrects='{\"file\": \"%s\", \"line\": %d}' summary=\"...\"" % (rel, ln, msg, rel, ln))
        last, seen_ids = 0, {}
        for ln, raw, o in p.rows:
            seq = o.get("seq")
            corrected = (rel, "seq", seq) in corr or (rel, "line", ln) in corr
            for prob in L.validate(rel, o):
                (R.warns if corrected else R.fails).append(
                    "%s%s line %d (seq %s): %s" % ("corrected defect: " if corrected else "", rel, ln, seq, prob))
            if isinstance(seq, int) and not isinstance(seq, bool):
                if seq <= last and not corrected:
                    R.fails.append("%s line %d: seq %d does not rise (the previous record has seq %d); records are "
                                   "numbered by fos_log" % (rel, ln, seq, last))
                elif seq > last + 1 and last:
                    R.notes.append("%s: seq jumps from %d to %d at line %d" % (rel, last, seq, ln))
                last = max(last, seq)
            rid = o.get("id")
            if rid and kind not in L.REPEATABLE_IDS:
                if rid in seen_ids and not corrected:
                    R.fails.append("%s: id %s is used twice (lines %d and %d)" % (rel, rid, seen_ids[rid], ln))
                seen_ids.setdefault(rid, ln)
            cap = o.get("captured_by")
            if kind == "signature" and cap != "close_script":
                R.fails.append("%s line %d: a signature not written by the close-out script" % (rel, ln))
            if kind == "drill" and cap != "drill_script":
                R.fails.append("%s line %d: a drill record not written by fos_drill" % (rel, ln))
            if kind == "event" and o.get("type") in L.SCRIPT_ONLY_EVENTS and cap not in L.SCRIPT_CAPTURES:
                R.fails.append("%s line %d: a '%s' event not written by a seed script" % (rel, ln, o.get("type")))


def check_history(R, records, events, gitok, st):
    if not gitok:
        R.notes.append("git is not available here: the history checks were skipped (the founder's close-out "
                       "runs them, or keeps a dated copy of records/ in the witness when git is missing)")
        return
    for kind, rel in L.RECORD_FILES.items():
        head = L.head_bytes(rel)
        cur = L.read_bytes(rel)
        if head is None or cur is None:
            continue
        if not W.is_append(head.replace(b"\r\n", b"\n"), cur.replace(b"\r\n", b"\n")):
            R.fails.append("%s: earlier lines were edited or removed since the last commit (CORE-4). The founder's "
                           "close-out offers to restore them." % rel)
    for prob in L.history_problems():
        R.fails.append("history: " + prob)
    code, out = L.git("log", "--format=%h\t%s", "--", "records/")
    if code == 0 and st != "seed":  # the seed's own early history predates the convention
        bad = [ln.split("\t", 1) for ln in out.splitlines() if "\t" in ln]
        bad = [(h, s) for h, s in bad if not any(s.startswith("[%s]" % t) for t in COMMIT_TYPES)]
        if bad:
            R.warns.append("%d commit(s) that change records/ do not follow the commit convention ([TYPE] summary; "
                           "docs/RECORDS.md), e.g. %s \"%s\"" % (len(bad), bad[0][0], bad[0][1][:60]))
    born = [e for e in events if e.get("type") == "born"]
    if len(born) > 1:
        R.fails.append("there is more than one birth record")
    birth = R.info.get("birth") if R.info else (born[0] if born else None)
    if birth:
        root = L.root_commit()
        claimed = (birth.get("seed") or {}).get("tree")
        actual = L.tree_of(root) if root else None
        if actual != claimed:
            R.fails.append("the birth record names seed tree %s, but the first commit of this history has tree %s: "
                           "the first commit was replaced" % ((claimed or "?")[:12], (actual or "?")[:12]))


JSON_FILES = ("org/config.json", "org/TOOLS.json", "view/VIEWS.json", "org/BIRTH.json", "seed.json")


def check_json_twice(R):
    """A JSON file that holds the same key twice says two things: the scripts read the last copy, and a person reading
    it may stop at the first. Each one fails, whatever the copies say (for the structural files, the invariant also
    counts such a file as changed from birth)."""
    for rel in JSON_FILES:
        twice = W.duplicate_key(L.read_bytes(rel))
        if twice:
            R.fails.append("%s: %s, so the file says two things: the scripts read the last copy, and a person reading "
                           "it may stop at the first. Keep one copy of the key, the one the organization decided"
                           % (rel, twice))


def check_birth(R, info):
    """The birth is read from the history (or, without git, the witness), never from events.jsonl alone."""
    st = info["stage"]
    if info.get("damaged"):
        where = ("commit %s" % info["commit"][:12]) if info.get("commit") else "the witness folder's dated copy"
        R.fails.append("BIRTH RECORD LOST: records/events.jsonl no longer holds this organization's birth record, which "
                       "%s still holds. The file was overwritten or emptied (CORE-4). This folder is an organization, not "
                       "the seed. The founder's close-out restores the file before anything else." % where)
    if info.get("unconfirmed"):
        R.fails.append("records/events.jsonl holds a birth record that no [BIRTH] commit in this history holds; an "
                       "organization is born only through python scripts/fos_init.py, never by writing a line")
    data = L.read_bytes(L.BIRTH_FILE)
    if st == "seed":
        if data is not None:
            R.warns.append("%s exists, but no history or witness holds a birth: this folder is the seed itself"
                           % L.BIRTH_FILE)
        return
    if data is None:
        R.fails.append("%s is missing: it was deleted (it is written once, at birth). The founder's close-out restores "
                       "it from the last commit" % L.BIRTH_FILE)
        return
    try:
        kept = json.loads(data.decode("utf-8"))
        tree = (kept.get("seed") or {}).get("tree")
    except (ValueError, AttributeError, UnicodeDecodeError):
        kept, tree = None, None
    claimed = ((info.get("birth") or {}).get("seed") or {}).get("tree")
    if not kept or (claimed and tree != claimed):
        R.fails.append("%s does not match the birth record (seed tree %s): it was changed after birth. The founder's "
                       "close-out restores it" % (L.BIRTH_FILE, (claimed or "?")[:12]))


def check_witness(R, st, gitok):
    w = L.find_witness()
    R.summary["witness"] = "none"
    if st == "seed":
        R.notes.append("this folder is the seed itself; an organization is born from it with "
                       "python scripts/fos_init.py <new-folder>, which also creates its witness")
        return
    if w is None:
        R.warns.append("UNWITNESSED: no witness copy is set up, so the history could be rewritten without anyone "
                       "noticing. The founder can create one: python scripts/fos_witness.py setup <folder-outside>, "
                       "then git remote add witness <folder-outside>/history.git")
        return
    if w["kind"] == "git" and not L.git_ok():
        # Some agent apps' sandboxes cannot start git. The witness is still there; only its checks wait.
        R.summary["witness"] = (w.get("history") or w["folder"]) + " (found without git)"
        R.notes.append("git cannot run here, so the witness was found by reading this folder's settings, and its "
                       "history is not checked from here. It is not missing: the founder's close-out, run in an "
                       "ordinary terminal, checks it and pushes to it")
        return
    if w["kind"] == "git":
        rep = W.verify(w["folder"])
        R.summary["witness"] = rep["path"]
        if not rep["exists"]:
            if os.environ.get("SEED_IN_CONTAINER") == "1":
                R.notes.append("the witness is outside this container, as intended; the founder's close-out, run "
                               "outside, checks it and pushes to it")
            else:
                R.fails.append("the witness named by this folder's git remote does not exist: %s" % rep["path"])
            return
        if not rep["settings_ok"]:
            R.fails.append("the witness at %s no longer refuses rewrites and deletions: its settings changed" % rep["path"])
        if not rep["hook_ok"]:
            R.fails.append("the witness's check is missing from %s/hooks" % rep["path"])
        elif not rep["hook_same_as_this_copy"]:
            R.notes.append("the witness's check differs from this folder's scripts/fos_witness.py (one of them changed)")
        for prob in rep["history_problems"]:
            R.fails.append("witness history: " + prob)
        pushes = W.read_push_log(w["folder"])
        refused = [p for p in pushes if p.get("result") == "refused"]
        R.summary["pushes"] = {"accepted": len(pushes) - len(refused), "refused": len(refused)}
        if refused:
            last = refused[-1]
            R.notes.append("the witness has refused %d push(es); the latest, at %s: %s" % (
                len(refused), last.get("ts"), "; ".join(last.get("reasons") or [])[:300]))
        hook = os.path.join(rep["path"], "hooks", W.HOOK_SCRIPT)
        if pushes and os.path.isfile(hook):
            current = W.sha256_file(hook)
            odd = [p for p in pushes if p.get("check_sha256") not in (None, current)]
            if odd:
                R.warns.append("%d push(es) in the witness's log were decided by a different copy of its check than "
                               "the one installed now" % len(odd))
        tip = rep["tip"]
        if not tip:
            R.notes.append("the witness holds no commits yet")
        elif gitok:
            rel = L.witness_relation(w)
            R.summary["witness_relation"] = rel.get("state")
            state = rel.get("state")
            if state == "ahead":
                R.summary["unwitnessed_commits"] = rel["n"]
                R.notes.append("%d commit(s) not yet in the witness (the close-out pushes them)" % rel["n"])
            elif state == "behind":
                R.fails.append("BEHIND THE WITNESS: the witness holds %d close-out(s) that this folder never had, so "
                               "another copy of this organization was closed out. One working copy per organization "
                               "is supported (docs/RECORDS.md). Nothing is lost: the founder brings this folder up to "
                               "date with python scripts/fos_sync.py, which keeps this folder's own unsaved work (in "
                               "place, or set aside in the witness folder if it would collide)." % rel["n"])
            elif state == "diverged":
                R.fails.append("REWRITTEN OR SPLIT: this folder's history no longer contains the witnessed commit %s. "
                               "From their last common commit %s, this folder has %d commit(s) the witness never "
                               "accepted, and the witness has %d this folder lacks. The witness holds the original. The "
                               "founder returns this folder to it with python scripts/fos_sync.py, which keeps every "
                               "record and sets aside nothing without saying so."
                               % (tip[:12], (rel.get("base") or "?")[:12], rel.get("n", 0), rel.get("behind_n", 0)))
            elif state == "unrelated":
                R.fails.append("REWRITTEN OR SPLIT: this folder's history no longer contains the witnessed commit %s "
                               "and shares no commit with the witness: it was replaced. The witness holds the original; "
                               "python scripts/fos_sync.py returns this folder to it." % tip[:12])
    else:
        R.summary["witness"] = w["folder"] + " (dated copies of records/)"
        snap = W.latest_snapshot(w["folder"])
        if not snap:
            R.notes.append("the witness folder holds no snapshot of records/ yet")
        for prob in (W.compare_with_snapshot(L.ROOT, snap) if snap else []):
            R.fails.append("witness snapshot: " + prob)


def check_stage(R, cfg, records, events, st, gitok):
    starts = [e for e in events if e.get("type") == "session_start"]
    if st == "seed":
        n = sum(len(p.rows) + len(p.bad) for p in records.values())
        if n:
            R.warns.append("this folder is the seed itself (it has no birth record) but holds %d record(s). Work "
                           "belongs in an organization born from the seed: python scripts/fos_init.py "
                           "../my-organization" % n)
        return
    if not L.session_recorded(events):
        activity = activity_since_close(gitok)
        if activity:
            R.warns.append("SESSION NOT RECORDED: since the last close-out %s, and nobody recorded a session_start "
                           "for that work. A member worked here without recording its session (CORE-5). Record it now "
                           "(python scripts/fos_log.py event type=session_start summary=\"...\"); the close-out notes the "
                           "gap either way" % "; ".join(activity[:3]))
    elif starts:
        last = starts[-1].get("session")
        ended = any(e.get("type") in ("session_end", "close_out") and e.get("session") == last for e in events)
        if not ended:
            R.notes.append("session %s is open (no session_end yet)" % last)


GENERATED = ("view/org_view.html", "org/RULES_IN_FORCE.md")


def held_until_founding():
    """{path: SHA-256} of the structural files the last close-out left uncommitted until the founding."""
    closes = [e for e in L.read_records(L.RECORD_FILES["event"]).objs if e.get("type") == "close_out"
              and e.get("captured_by") == "close_script"]
    held = (closes[-1].get("held_until_founding") if closes else None) or {}
    return held if isinstance(held, dict) else {}


def activity_since_close(gitok):
    """What changed on disk since the last close-out, in a few plain phrases (generated files aside)."""
    out = []
    if gitok:
        code, txt = L.git("status", "--porcelain", "--untracked-files=all")
        paths = [ln[3:].strip().strip('"') for ln in txt.splitlines() if ln.strip()] if code == 0 else []
        held = held_until_founding()
        paths = [p for p in paths if p not in GENERATED and not p.startswith(".fos-lock")
                 and not (p in held and L.file_sha256(p) == held[p])]
        recs = [p for p in paths if p.startswith("records/")]
        other = [p for p in paths if not p.startswith("records/")]
        if recs:
            out.append("records were added (%s)" % ", ".join(recs[:4]))
        if other:
            out.append("files changed (%s%s)" % (", ".join(other[:4]), ", ..." if len(other) > 4 else ""))
        return out
    w = L.find_witness()
    snap = W.latest_snapshot(w["folder"]) if w else None
    if not snap:
        return out
    grown = []
    for name in sorted(os.listdir(snap)):
        if name.endswith(".jsonl"):
            with open(os.path.join(snap, name), "rb") as f:
                old = f.read().count(b"\n")
            now = (L.read_bytes("records/" + name) or b"").count(b"\n")
            if now > old:
                grown.append("records/" + name)
    if grown:
        out.append("records were added (%s)" % ", ".join(grown[:4]))
    return out


def check_decisions(R, cfg, records, events, ad):
    props = {p.get("id") for p in records["proposal"].objs}
    founders = L.founder_instances(cfg)
    cur = L.current_session(events)
    for d in ad["decisions"]:
        did, pids = d.get("id"), d.get("proposal_ids") or []
        for pid in pids:
            if pid not in props:
                R.fails.append("decision %s names proposal %s, which does not exist" % (did, pid))
        q = d.get("question") or ""
        missing = [p for p in pids if p not in q]
        if missing:
            R.warns.append("%s: the question as recorded does not name %s. Ask \"Do you adopt %s?\" and record the "
                           "reply (CORE-3)" % (did, ", ".join(missing), missing[0]))
        if L.is_generic_reply(d.get("words")):
            if missing or not pids:
                R.warns.append("%s: the reply \"%s\" is generic and does not answer a question that named what was "
                               "decided; it is not a decision until the founder answers one (CORE-3)"
                               % (did, d.get("words")))
            else:
                R.warns.append("%s: the reply \"%s\" is generic; at close-out the founder confirms it by signing"
                               % (did, d.get("words")))
        if d.get("decided_by") in founders and d.get("decider_kind") != "human":
            R.fails.append("%s: decided_by is the founder but decider_kind is not human" % did)
        if did in ad["awaiting"] and d.get("session") != cur:
            R.warns.append("%s (session %s) was never signed: it is a proposal again until the founder signs it at a "
                           "close-out" % (did, d.get("session")))
            if did not in (L.read_text("org/STATE.md", "") or ""):
                R.warns.append("org/STATE.md's 'Waiting for close-out' list no longer mentions %s, which still waits for "
                               "the founder's signature: put it back on the list (the close-out also lists it from the "
                               "records)" % did)
    notes = {s.get("decision_id"): s for s in records["signature"].objs if s.get("note")}
    for did in sorted(ad.get("sent_back", set())):
        R.warns.append("%s was sent back by the founder: \"%s\". Rework it and ask again as a new decision"
                       % (did, (notes.get(did) or {}).get("note", "")))
    for did in sorted(ad["signed"]):
        if did in notes:
            R.notes.append("%s was signed with a note from the founder: \"%s\"" % (did, notes[did]["note"]))
    for level, msg in ad["sig_problems"]:
        (R.fails if level == "FAIL" else R.warns).append(msg)


def check_proposals(R, cfg, records, ad, tools, views, claims_on=True):
    """The proposal form (AGENTS.md, CORE-2): a decision that adopts structure rests on proposals that say in plain
    words what they change for the founder and how they are undone; a proposal that rests on a work marked read
    has that work's saved copy (CORE-13; not in a research configuration that switches it off). Warnings only, so
    earlier organizations' records stay valid."""
    props = {p.get("id"): p for p in records["proposal"].objs}
    by = L.structure_by_decision(cfg, tools, views)
    for d in ad["decisions"]:
        did = d.get("id")
        if d.get("verdict") not in L.ADOPTING_VERDICTS or ad["sig_status"].get(did) in ("refused", "sent_back"):
            continue
        if not (by.get(did) or L.structural_proposals(d, props)):
            continue
        # Its structural proposals answer for the structure; only a decision that has none answers through all of them.
        named = L.structural_proposals(d, props) or [pid for pid in d.get("proposal_ids") or [] if pid in props]
        lacking = [pid for pid in named if not (props[pid].get("for_the_founder") and props[pid].get("undo"))]
        if lacking:
            R.warns.append("PROPOSAL WITHOUT PLAIN-LANGUAGE EFFECT OR UNDO: %s adopts structure from %s, which %s not "
                           "say in plain words what it changes for the founder (for_the_founder) or how it is undone "
                           "(undo) (CORE-2)" % (did, ", ".join(lacking), "does" if len(lacking) == 1 else "do"))
    for pid, p in (sorted(props.items(), key=lambda kv: str(kv[0])) if claims_on else []):
        g = p.get("grounding")
        if not (isinstance(g, dict) and g.get("status") == "read"):
            continue
        sf = g.get("source_file") or ""
        norm = os.path.normpath(sf).replace(os.sep, "/") if sf else ""
        if norm.startswith("sources/") and os.path.isfile(L.path(norm)):
            continue
        R.warns.append("GROUNDING NOT SAVED: %s rests on %s, marked read, but %s; a work marked read has its saved copy "
                       "in sources/ (source_file), or it is marked lead (CORE-13)"
                       % (pid, g.get("source") or "a work", ("%s is not a file in sources/" % sf) if sf else
                          "names no saved copy"))


def check_governance(R, cfg, ad, tools, views):
    for kind, label, ab in L.structural_items(cfg, tools, views):
        if L.governed(ab, ad["signed"], kind, label):
            continue
        if ab in ad["awaiting"]:
            R.warns.append("AWAITING SIGNATURE: %s '%s' (decision %s) is provisional until the founder signs it at "
                           "close-out" % (kind, label, ab))
        elif ab in ad.get("sent_back", set()):
            R.fail_item(kind, label, "%s '%s': the founder sent %s back, so it is not part of the organization; undo "
                                     "the change, rework it, and ask again as a new decision" % (kind, label, ab))
        elif ab in ad["refused"]:
            R.fail_item(kind, label, "%s '%s': the founder refused to sign %s, so it is not part of the organization; "
                                     "undo the change and keep the proposal" % (kind, label, ab))
        else:
            R.fail_item(kind, label, "PROPOSAL-ONLY, not part of the organization: %s '%s' (adopted_by: %s). Write a "
                                     "proposal and ask the founder (CORE-2)" % (kind, label, ab))
    for r in cfg.get("roles", []):
        on = (r.get("trigger") or {}).get("on")
        if not on:
            R.fail_item("role", r.get("id"), "role '%s' declares no trigger: it is an aspiration, not a role (CORE-12)"
                        % r.get("id"))
        elif on not in L.TRIGGER_KINDS:
            R.fail_item("role", r.get("id"), "role '%s' has trigger '%s'; use one of %s"
                        % (r.get("id"), on, ", ".join(L.TRIGGER_KINDS)))
    live = {r.get("id") for r in cfg.get("roles", [])}
    for r in cfg.get("retired_roles", []):
        if r.get("id") in live:
            R.fails.append("role '%s' is both live and retired" % r.get("id"))
    for m in cfg.get("modules", []):
        if not os.path.exists(L.path("modules/%s/MODULE.md" % m.get("id"))):
            R.fail_item("module", m.get("id"), "config lists module '%s' but modules/%s/MODULE.md does not exist"
                        % (m.get("id"), m.get("id")))


def check_founding(R, cfg, records, ad, info, tools=None, views=None):
    """The founding comes before structure, as one invariant on files and history: no commit holds the structural files
    (fos_witness.STRUCTURE_FILES) changed from the organization's birth unless an earlier commit founds it, a close-out
    at which the founder typed FOUND. That part runs with the history checks (fos_witness.check_history, which the
    witness also runs on every push) and fails there. Here: where the organization was founded; structure prepared in
    the folder before that, which the close-out holds back until the founding; org/config.json's founding facts
    against the history; and, as warnings only, decisions whose labels or effects adopt structure before the founding."""
    if info.get("stage") == "seed":
        return
    fs = info.get("founding") or {}
    org = cfg.get("organization", {})
    fd = fs.get("decision")
    R.summary["founding"] = {"founded": bool(fs.get("founded")), "decision": fd, "commit": fs.get("commit")}
    if fs.get("founded"):
        R.notes.append("founded: the founder typed FOUND for %s at a close-out%s" % (
            fd, (" (commit %s)" % fs["commit"][:10]) if fs.get("commit") else ""))
        if not org.get("founded") or org.get("founding_decision") != fd:
            R.warns.append("org/config.json does not show the founding the history holds (%s): its organization block "
                           "says founded %r, founding_decision %r. The close-out writes these at the founding; the "
                           "history is what counts" % (fd, org.get("founded"), org.get("founding_decision")))
    else:
        if org.get("founded"):
            R.warns.append("org/config.json says the organization is founded, but no close-out founded it. It is founded "
                           "only when the founder types FOUND at a close-out (onboarding/CLOSE_OUT.md), whatever "
                           "config.json or the decision records say")
        diffs = L.structure_since_birth()
        if diffs:
            R.notes.append("structure prepared for the founding, changed since the organization's birth: %s. The "
                           "organization is not founded yet, so a close-out commits it only once the founder founds "
                           "the organization there (types FOUND); until then it stays in this folder, uncommitted"
                           % W.describe_differences(diffs))
    for d, what in L.early_adoptions(cfg, records, ad, fs, tools, views):
        R.warns.append("%s: adopts %s %s. The founding comes first (onboarding/START.md, step 8): name these proposals "
                       "in the founding question instead. A warning only: no structure is committed before the founder "
                       "founds the organization at a close-out"
                       % (d.get("id"), ", ".join(what), ("before the founding decision %s" % fd) if fs.get("founded")
                          else "while the organization is not founded"))
    if fs.get("founded"):
        for d in ad["decisions"]:
            if d.get("founding") is True and d.get("id") != fd:
                R.warns.append("%s: it is recorded with founding: true, but the founder founded the organization on %s; "
                               "it is an ordinary decision" % (d.get("id"), fd))


def check_ledgers(R, cfg, records, study, claims_on):
    """Pins still open; claims about members without their runs; a member's own producer named in its work;
    changes after a frozen study design without a deviation line."""
    latest = {}
    for p in records["pin"].objs:
        latest[p.get("id")] = p
    for pid, p in sorted(latest.items()):
        if p.get("state") == "open":
            R.notes.append("pin %s is open: \"%s\" (comes back when: %s)" % (pid, (p.get("words") or "")[:100],
                                                                            p.get("trigger")))
    if claims_on:
        for c in records["claim"].objs:
            if c.get("about_member") and not isinstance(c.get("runs"), int):
                R.warns.append("claim %s is about how a member behaves but does not say how many runs it rests on "
                               "(runs; CLM-9)" % c.get("id"))
    for kind, field in (("claim", "claim"), ("review", "findings")):
        for o in records[kind].objs:
            ident = o.get("identity") or {}
            producer = ident.get("producer")
            if ident.get("kind") != "ai" or not producer or producer == "unknown" or len(producer) < 3:
                continue
            if producer.casefold() in (o.get(field) or "").casefold():
                R.warns.append("%s %s by %s names its own producer (%s): that producer is an interested party; say so "
                               "in the work and have another producer's member or the founder check it (MBR-9)"
                               % (kind, o.get("id"), ident.get("instance"), producer))
    if study and study.get("status") == "confirmatory":
        changes = [e for e in records["event"].objs if e.get("type") in ("structure_change", "model_swap")]
        if changes and not records["deviation"].objs:
            R.warns.append("this confirmatory study's design changed (%d structure or model change(s)) but "
                           "records/deviations.jsonl holds no line: record each change and its kind (DA-5)"
                           % len(changes))
    R.summary["open_pins"] = sum(1 for p in latest.values() if p.get("state") == "open")


def check_charter_and_goal(R, cfg, ad, info):
    """Each near-term goal in the charter names the decision that adopted it; the goal names its decision."""
    if info["stage"] == "seed":
        return
    fd = (info.get("founding") or {}).get("decision")
    for e in L.parse_entries(L.read_text("org/CHARTER.md", "")):
        if not e["id"].startswith("NG-"):
            continue
        ab = e.get("adopted_by")
        if not ab:
            R.warns.append("org/CHARTER.md %s has no adopted_by: it is a proposal until a decision the founder signs "
                           "adopts it%s" % (e["id"], (" (in a founding charter, the founding decision %s)" % fd) if fd else ""))
        elif not L.governed(ab, ad["signed"]) and ab not in ad["awaiting"]:
            R.fail_item("charter item", e["id"], "org/CHARTER.md %s: adopted_by %s is not a decision the founder signed, "
                                                 "so it is a proposal only (CORE-2)" % (e["id"], ab))
    if info["stage"] == "founded":
        goal = (L.parse_entries(L.read_text("org/GOAL.md", "")) or [{}])[0]
        dec = (goal.get("decision") or "").strip()
        if not dec or dec.startswith("(") or "pending" in dec.lower():
            R.warns.append("org/GOAL.md's decision field still reads %r: put the decision that adopted the goal there "
                           "(%s)" % (dec or "", fd or "the founding decision"))
        elif dec not in {d.get("id") for d in ad["decisions"]}:
            R.warns.append("org/GOAL.md names decision %s, which is not in records/decisions.jsonl" % dec)


def check_generated(R, cfg, records):
    try:
        import fos_rules
        text, _, _ = fos_rules.build(cfg, records)
        if (L.read_text("org/RULES_IN_FORCE.md") or "").replace("\r\n", "\n") != text:
            R.warns.append("org/RULES_IN_FORCE.md is out of date: python scripts/fos_rules.py (the close-out does this)")
    except Exception as e:  # a broken compiler must not hide the other findings
        R.warns.append("the rules compiler failed: %s" % e)
    try:
        import fos_render
        drawn = (L.read_text("view/org_view.html") or "").replace("\r\n", "\n")
        if hasattr(fos_render, "build") and drawn != fos_render.build(cfg, records):
            R.notes.append("the view is out of date: python scripts/fos_render.py (the close-out does this)")
    except Exception as e:
        R.warns.append("the view could not be drawn: %s" % e)


def check_claims(R, records, docs_changed):
    blob = "\n".join(json.dumps(o, ensure_ascii=False).lower() for o in records["claim"].objs)
    missing = []
    files = []
    for d, dirs, fs in os.walk(L.path("work")):
        for fn in fs:
            files.append(os.path.relpath(os.path.join(d, fn), L.ROOT).replace("\\", "/"))
    files += [f for f in docs_changed if os.path.exists(L.path(f))]
    for rel in sorted(set(files)):
        data = L.read_bytes(rel) or b""
        if b"\0" in data[:4096]:
            continue
        for kind, cite in L.citations_in(data.decode("utf-8", errors="replace")):
            key = cite.lower()
            doi = key.split("doi.org/", 1)[1] if "doi.org/" in key else None
            if key not in blob and not (doi and doi in blob):
                missing.append((rel, kind, cite))
    for rel, kind, cite in missing[:15]:
        R.warns.append("%s cites %s %s, but no line in records/claims.jsonl names it (CORE-13): add a claim record, "
                       "or mark it lead" % (rel, kind, cite))
    if len(missing) > 15:
        R.warns.append("... and %d more citations without a claims line" % (len(missing) - 15))


def check_fetches(R, records):
    """Every fetch a member logged (source_fetched) names a page saved in sources/, unchanged since it was saved."""
    for e in records["event"].objs:
        if e.get("type") != "source_fetched":
            continue
        rel = (e.get("saved_as") or "").replace("\\", "/")
        if not rel.startswith("sources/"):
            R.warns.append("events seq %s logs a fetch of %s but names no saved file in sources/ (saved_as): a fetched "
                           "page is a source only once it is saved there" % (e.get("seq"), e.get("url") or "?"))
        elif L.read_bytes(rel) is None:
            R.warns.append("events seq %s logs a fetch of %s saved as %s, which is not in the folder"
                           % (e.get("seq"), e.get("url") or "?", rel))
        elif e.get("saved_sha256") and e["saved_sha256"] != L.file_sha256(rel):
            R.warns.append("%s changed since it was fetched from %s (events seq %s; its SHA-256 differs)"
                           % (rel, e.get("url") or "?", e.get("seq")))


def check_quotes(R, cfg, records, ad):
    """CK-1, the mechanical core of claim checking: every verified claim's quotation occurs in its saved source,
    and every passage quoted in the organization's own files is something the founder said or adopted, or
    occurs in a saved source. (python scripts/fos_claims.py prints the same, claim by claim.)"""
    for level, cid, msg in L.claim_checks(records):
        (R.fails if level == "FAIL" else R.warns).append(msg)
    for level, rel, n, q, sfile, sline in L.org_quote_checks(cfg, records, ad):
        if level == "WARN":
            R.warns.append("QUOTES THE SEED, NOT THE FOUNDER: %s line %d puts \"%s\" in quotation marks; it is close to "
                           "the seed's own words in %s (\"%s\"), not to anything the founder said. Quote the seed "
                           "exactly and say where it comes from, or drop the quotation marks (CK-1)"
                           % (rel, n, q[:120], sfile, (sline or "")[:160]))
            continue
        R.fails.append("QUOTE NOT FROM THE FOUNDER: %s line %d quotes \"%s\", which matches nothing the founder said "
                       "or adopted (org/GOAL.md, the founder's recorded words, signed proposals), no saved source and "
                       "not the seed's own text (CK-1). If the words were changed, put back the founder's words; if "
                       "they quote a source, save it in sources/" % (rel, n, q[:120]))


def check_folders(R, st, gitok):
    """Work goes in work/; docs/ and the seed's own files stay as born. Returns docs paths that changed."""
    if st == "seed" or not gitok:
        return []
    docs = _lines_since_birth("docs")
    for f in docs:
        R.warns.append("%s changed since the organization was born: docs/ holds the seed's documentation for "
                       "people; members write work in work/ (CORE-10)" % f)
    for area in SEED_AREAS + POINTER_FILES + L.LAUNCHERS:
        if area == "docs":
            continue
        for f in _lines_since_birth(area):
            R.warns.append("seed file changed since birth: %s (the seed's own files change by proposal and decision; "
                           "members do not edit them)" % f)
    root = L.root_commit()
    code, out = L.git("ls-tree", "--name-only", root) if root else (1, "")
    born_top = set(out.split()) if code == 0 else set()
    code, out = L.git("ls-files", "--others", "--exclude-standard")
    new_top = {x.split("/")[0] for x in out.splitlines() if x.strip()} if code == 0 else set()
    code, out = L.git("ls-files")
    new_top |= {x.split("/")[0] for x in out.splitlines() if x.strip()} if code == 0 else set()
    for name in sorted(new_top - born_top - set(ORG_FOLDERS)):
        R.warns.append("'%s' is outside the organization's folders; work goes in work/, sources in sources/" % name)
    return docs


def check_tools(R, cfg, ad, tools, records=None):
    founders = L.founder_instances(cfg)
    decided = {d.get("id"): d for d in ad["decisions"]}
    today = L.now_utc()[:10]
    seen = set()
    for t in tools.get("tools", []):
        tid = t.get("id")
        seen.add(tid)
        for k in ("id", "path", "tier", "status", "adopted_by"):
            if k not in t:
                R.fail_item("tool", tid, "org/TOOLS.json: tool %s has no '%s'" % (tid, k))
        if t.get("status") not in ("proposed", "approved", "building", "testing", "active", "paused", "retired"):
            R.fail_item("tool", tid, "org/TOOLS.json: tool %s has status %r" % (tid, t.get("status")))
        if t.get("tier") == "seed":
            if not L.governed(t.get("adopted_by"), ad["signed"], "tool", tid):
                R.fail_item("tool", tid, "org/TOOLS.json: %s claims to be a seed tool but is not one of the seed's" % tid)
            elif t.get("path") and not os.path.exists(L.path(t["path"])):
                R.fail_item("tool", tid, "org/TOOLS.json: seed tool %s is missing (%s)" % (tid, t["path"]))
            continue
        if t.get("tier") not in (1, 2, 3, 4, 5):
            R.fail_item("tool", tid, "org/TOOLS.json: tool %s has tier %r; tiers are 1 to 5" % (tid, t.get("tier")))
        cred = json.dumps(t.get("credential") or "")
        if any(len(tok) >= 24 and tok.isalnum() for tok in cred.replace('"', " ").split()):
            R.fail_item("tool", tid, "org/TOOLS.json: tool %s seems to hold a secret; say only where the key is kept" % tid)
        if t.get("status") in ("active", "paused"):
            d = decided.get(t.get("adopted_by"))
            if isinstance(t.get("tier"), int) and t["tier"] >= 3 and d and d.get("decided_by") not in founders:
                R.fail_item("tool", tid, "tool %s is tier %d; only the founder may approve tier 3 and above" % (tid, t["tier"]))
            b, s = (t.get("builder") or {}).get("instance"), (t.get("tester") or {}).get("instance")
            if b and b == s:
                R.fail_item("tool", tid, "tool %s was tested by its own builder (%s); a different member tests it" % (tid, b))
            if t.get("status") == "active" and t.get("review_by") and str(t["review_by"]) < today:
                R.warns.append("tool %s is past its review date (%s): it is paused until reviewed" % (tid, t["review_by"]))
            now = L.file_sha256(t["path"]) if t.get("path") else None
            if t.get("code_sha256") and now and t["code_sha256"] != now:
                R.fail_item("tool", tid, "tool %s: its code (%s) changed since it was approved; the approval covers "
                                         "only the code it names, so the tool is unapproved until reviewed again"
                            % (tid, t["path"]))
            elif not t.get("code_sha256") and now:
                R.warns.append("tool %s gives no code_sha256, so its approval names no exact code; its code now "
                               "hashes to %s" % (tid, now))
    tdir = L.path("tools")
    if os.path.isdir(tdir):
        for name in sorted(os.listdir(tdir)):
            if os.path.isdir(os.path.join(tdir, name)) and name not in seen:
                R.warns.append("tools/%s has no row in org/TOOLS.json: an ungoverned tool may not be used" % name)
    for fn in sorted(os.listdir(L.path("scripts"))):
        if fn.endswith(".py") and fn[:-3] not in seen and fn[:-3] not in L.SEED_TOOLS:
            R.warns.append("scripts/%s is not a seed script and has no registry row: it may not be run" % fn)
    check_enforcement(R, tools, records)


ENFORCEMENT_KIND = "enforcement add-on"


def check_enforcement(R, tools, records):
    """An enforcement add-on (docs/ENFORCEMENT.md) is declared in the record: its registry row says what it covers and
    which code it is, and every recorded decline that names an add-on names a row of that kind. Only declines members
    recorded are seen here; the add-on's own log, outside the folder, holds every refusal."""
    addons = {t.get("id"): t for t in tools.get("tools", []) if t.get("kind") == ENFORCEMENT_KIND}
    for tid, t in sorted(addons.items(), key=lambda kv: str(kv[0])):
        missing = [k for k in ("covers", "code_sha256") if not t.get(k)]
        if missing:
            R.warns.append("enforcement add-on %s does not say %s in org/TOOLS.json, so the record cannot show what it "
                           "enforced (docs/ENFORCEMENT.md)"
                           % (tid, " or ".join({"covers": "which channels it covers (covers)",
                                                "code_sha256": "which code it is (code_sha256)"}[k] for k in missing)))
    declines = records.get("decline") if records else None
    for x in (declines.objs if declines else []):
        by = x.get("enforced_by")
        if not by:
            continue
        row = addons.get(by)
        if not row or row.get("status") not in ("testing", "active", "paused", "retired"):
            R.warns.append("UNDECLARED ENFORCEMENT: decline %s says the add-on %s refused the write, but org/TOOLS.json "
                           "has no row of kind '%s' for it in testing, active, paused or retired; register it, with "
                           "what it covers and its code hash, as a tool (docs/ENFORCEMENT.md)"
                           % (x.get("id"), by, ENFORCEMENT_KIND))


def check_drills(R, records):
    planted = {}
    for d in records["drill"].objs:
        if d.get("action") == "planted":
            planted[d.get("id")] = d
        elif d.get("action") == "revealed":
            p = planted.get(d.get("id"))
            seal = hashlib.sha256(((d.get("salt") or "") + (d.get("description") or "")).encode("utf-8")).hexdigest()
            if not p:
                R.fails.append("drill %s was revealed but never planted" % d.get("id"))
            elif p.get("seal") != seal:
                R.fails.append("drill %s: the revealed description does not match the seal recorded when it was "
                               "planted" % d.get("id"))
    ids = set(planted)
    for kind in ("decline", "review", "event"):
        for o in records[kind].objs:
            refs = [r for r in (o.get("refs") or []) if isinstance(r, str) and r.startswith("DR-")]
            if o.get("drill") and not any(r in ids for r in refs):
                R.warns.append("%s seq %s is marked as part of a drill but names no planted drill (DR-...)"
                               % (L.RECORD_FILES[kind], o.get("seq")))
    # A checker is trusted only after it has caught a planted drill (REV-5): until then, a review that finds
    # nothing cannot be told apart from a review that did not look.
    tested = {d.get("caught_by") for d in records["drill"].objs
              if d.get("action") == "revealed" and d.get("outcome") == "caught" and d.get("caught_by")}
    untested = {}
    for r in records["review"].objs:
        who = r.get("checker")
        if who and who not in tested:
            untested[who] = untested.get(who, 0) + 1
    for who, n in sorted(untested.items()):
        R.warns.append("UNTESTED CHECKER: %s has written %d review(s) but has not yet caught a planted drill, so its "
                       "reviews are not yet trusted (REV-5). The founder plants one: python scripts/fos_drill.py plant"
                       % (who, n))
    R.summary["tested_checkers"] = sorted(x for x in tested if x)


def check_identity(R, cfg, records):
    known = set(L.instances(cfg))
    unknown = set()
    for kind, p in records.items():
        for o in p.objs:
            ident = o.get("identity") or {}
            if ident.get("kind") in ("ai", "human") and ident.get("instance") not in known:
                unknown.add(ident.get("instance"))
    for u in sorted(x for x in unknown if x):
        R.warns.append("records name an instance '%s' that is not in org/config.json" % u)


SLOT_KEYS = ("model_id", "producer", "agent_app", "host")


def check_writers(R, cfg, records, st, corr=None):
    """Who wrote each AI member's record: shown by a launch fingerprint the check can recompute, or only stated.
    Also: launches and stated identities against the instances' model slots."""
    if st == "seed":
        return
    launches = L.witness_launches()
    insts = L.instances(cfg)
    verified, unverified, bad = 0, {}, []
    for kind, p in records.items():
        for ln, raw, o in p.rows:
            ident = o.get("identity") or {}
            if ident.get("kind") != "ai":
                continue
            lau = ident.get("launch")
            if not isinstance(lau, dict) or not lau.get("id"):
                who = ident.get("instance") or "?"
                unverified[who] = unverified.get(who, 0) + 1
                continue
            if launches is None:
                continue
            got = launches.get(lau["id"])
            where = "%s seq %s" % (L.RECORD_FILES[kind], o.get("seq"))
            rel = L.RECORD_FILES[kind]
            if corr and ((rel, "seq", o.get("seq")) in corr or (rel, "line", ln) in corr):
                genuine = got and got.get("instance") == ident.get("instance") \
                    and L.record_mac(got.get("token", ""), o) == lau.get("mac")
                if not genuine:
                    R.warns.append("corrected defect: %s claims launch %s, but that launch did not write it"
                                   % (where, lau["id"]))
                continue
            if not got:
                bad.append("%s names launch %s, which the witness folder does not hold" % (where, lau["id"]))
            elif got.get("instance") != ident.get("instance"):
                bad.append("%s says %s wrote it, but launch %s was %s" % (where, ident.get("instance"), lau["id"],
                                                                         got.get("instance")))
            elif L.record_mac(got.get("token", ""), o) != lau.get("mac"):
                bad.append("%s claims launch %s, but its fingerprint does not match: that launch did not write it as it "
                           "now reads" % (where, lau["id"]))
            else:
                verified += 1
    for b in bad[:10]:
        R.fails.append("WRITER NOT AS CLAIMED: " + b)
    if len(bad) > 10:
        R.fails.append("... and %d more records whose writer is not as claimed" % (len(bad) - 10))
    if unverified:
        R.warns.append("WRITER NOT VERIFIED: %d record(s) by AI members carry no launch fingerprint (%s), so who wrote "
                       "them rests on their own account. The founder launches each agent app with python "
                       "scripts/fos_launch.py <instance> (docs/RECORDS.md)"
                       % (sum(unverified.values()), ", ".join("%s: %d" % kv for kv in sorted(unverified.items()))))
    if launches is None and any(isinstance((o.get("identity") or {}).get("launch"), dict)
                                for p in records.values() for o in p.objs):
        R.notes.append("the witness folder cannot be read here, so launch fingerprints are checked by the founder's "
                       "close-out")
    elif verified:
        R.notes.append("%d record(s) by AI members verified against their launch" % verified)
    R.summary["verified_writers"] = verified
    for e in records["event"].objs:
        if e.get("type") == "instance_launched":
            inst, said = e.get("launched_instance"), e.get("launched") or {}
            if inst not in insts:
                R.warns.append("launch %s is for '%s', which org/config.json does not hold" % (e.get("launch_id"), inst))
                continue
            slot = insts[inst][1].get("slot") or {}
            diffs = ["%s %s (slot: %s)" % (k, said.get(k), slot.get(k)) for k in SLOT_KEYS
                     if slot.get(k) and said.get(k) not in (None, "", "unknown", slot.get(k))]
            if diffs:
                R.warns.append("launch %s runs %s on %s, which differs from its model slot: a change of model in a "
                               "slot is a proposal and a decision (CORE-2)" % (e.get("launch_id"), inst, "; ".join(diffs)))
            if launches is not None:
                got = launches.get(e.get("launch_id"))
                if not got:
                    R.fails.append("launch %s is in the records but not in the witness folder: fos_launch did not make "
                                   "it" % e.get("launch_id"))
                elif got.get("instance") != inst or (got.get("identity") or {}) != said \
                        or got.get("app_instructions") != e.get("app_instructions"):
                    R.fails.append("launch %s in the records differs from the witness folder's copy" % e.get("launch_id"))
        elif e.get("type") == "session_start":
            ident = e.get("identity") or {}
            if ident.get("kind") == "ai" and ident.get("source") == "stated" and ident.get("instance") in insts:
                slot = insts[ident["instance"]][1].get("slot") or {}
                diffs = ["%s %s (slot: %s)" % (k, ident.get(k), slot.get(k)) for k in SLOT_KEYS
                         if slot.get(k) and ident.get(k) not in (None, "", "unknown", slot.get(k))]
                if diffs:
                    R.warns.append("%s: %s said at session start that it runs on %s, which differs from its model "
                                   "slot; a change of model in a slot is a proposal and a decision (CORE-2)"
                                   % (e.get("session"), ident["instance"], "; ".join(diffs)))


def seed_identity():
    """For the seed itself: the commit and tree an organization born from this folder starts from. The tree is its
    birth hash (scripts/fos_init.py prints the same), so a reader can check a birth against the seed they hold."""
    import fos_init
    seed = L.seed_info()
    out = {"name": seed.get("name"), "version": seed.get("version")}
    if fos_init.seed_has_history():
        out["commit"] = L.git("rev-parse", "--short", "HEAD")[1].strip()
        out["tree"] = L.git("rev-parse", "HEAD^{tree}")[1].strip()
        out["uncommitted"] = bool(L.git("status", "--porcelain", "--untracked-files=no")[1].strip())
    else:
        files = fos_init.files_without_git()
        out["tree"] = L.git_tree_id(files, [rel for rel in files if L.is_executable_path(rel)])
        out["commit"] = None
    return out


def run_checks():
    R = Result()
    try:
        cfg = L.config()
    except (OSError, ValueError) as e:
        R.fails.append("org/config.json cannot be read: %s" % e)
        return R
    records = L.read_all()
    events = records["event"].objs
    info = L.stage_info(cfg, events)
    R.info = info
    st = info["stage"]
    gitok = L.git_ok() and L.has_head()
    tools = L.tools_registry()
    try:
        views = L.load_json("view/VIEWS.json")
    except (OSError, ValueError):
        views = None
    corr = corrections_index(events)
    check_json_twice(R)
    check_birth(R, info)
    check_records(R, records, corr)
    check_history(R, records, events, gitok, st)
    check_witness(R, st, gitok)
    check_stage(R, cfg, records, events, st, gitok)
    ad = L.adoption(cfg, records)
    check_decisions(R, cfg, records, events, ad)
    check_governance(R, cfg, ad, tools, views)
    check_founding(R, cfg, records, ad, info, tools, views)
    check_charter_and_goal(R, cfg, ad, info)
    study, study_problem = L.study_config()
    BASE["rev"] = study["_commit"] if study else None
    if study_problem:
        R.fails.append("RESEARCH CONFIGURATION NOT CONFIRMED: " + study_problem)
    if study:
        R.summary["configuration"] = "research: %s switched off (%s)" % (", ".join(study.get("switch_off") or []),
                                                                         study.get("status"))
        R.notes.append("RESEARCH CONFIGURATION for the study %r (org/STUDY.json, made at birth): %s switched off, "
                       "with its checks. For a study only; a founder's own organization keeps every core rule"
                       % (study.get("name"), ", ".join(study.get("switch_off") or [])))
    docs_changed = check_folders(R, st, gitok)
    claims_on = not study or "CORE-13" not in (study.get("switch_off") or [])
    if claims_on:
        check_claims(R, records, docs_changed)
        check_fetches(R, records)
        check_quotes(R, cfg, records, ad)
    check_ledgers(R, cfg, records, study, claims_on)
    check_proposals(R, cfg, records, ad, tools, views, claims_on)
    check_tools(R, cfg, ad, tools, records)
    check_drills(R, records)
    check_identity(R, cfg, records)
    check_writers(R, cfg, records, st, corr)
    check_generated(R, cfg, records)
    for x in L.role_rollcall(cfg, events):
        if x["status"] in ("due", "stale", "never"):
            R.notes.append("role roll-call: %s is %s (last ran: %s; expected every %s sessions)"
                           % (x["role"], x["status"], x["last_session"] or "never", x["expected"]))
    born = info.get("birth")
    decisions = records["decision"].objs
    pstatus, reopened = L.proposal_status(records, ad)
    for pid in sorted(reopened):
        R.notes.append("%s is still a proposal, open again: %s. Ask the founder again (by its ID), or leave it open"
                       % (pid, reopened[pid]))
    if st == "seed":
        R.summary["seed"] = seed_identity()
    R.summary.update({
        "stage": st,
        "birth_source": info.get("source"),
        "born_from": (born or {}).get("seed"),
        "events": len(events), "proposals": len(records["proposal"].objs),
        "open_proposals": sum(1 for v in pstatus.values() if v == "open"),
        "proposals_awaiting": sum(1 for v in pstatus.values() if v == "awaiting"),
        "decisions": len(decisions), "signed": len(ad["signed"]), "awaiting_signature": len(ad["awaiting"]),
        "refused": len(ad["refused"]), "declines": len(records["decline"].objs), "claims": len(records["claim"].objs),
        "session": L.current_session(events),
        "route": L.boot_route(st, cfg, events),
    })
    return R


def report(R, out=print):
    s = R.summary
    out("Organization check")
    if s:
        bf = s.get("born_from") or {}
        src = {"git": "; birth read from the history", "witness": "; birth read from the witness",
               "records": "; birth read from records/events.jsonl only"}.get(s.get("birth_source"), "")
        out("  stage: %s%s" % (s.get("stage"), (" (born from %s %s, seed tree %s%s)" % (
            bf.get("name"), bf.get("version"), (bf.get("tree") or "?")[:12], src)) if bf else ""))
        sd = s.get("seed")
        if sd and sd.get("commit"):
            out("  seed: %s %s at commit %s, seed tree %s. An organization born from this commit gets this tree as its "
                "birth hash (fos_init prints it)%s" % (sd.get("name"), sd.get("version"), sd["commit"], sd.get("tree"),
                                                       "; uncommitted changes here are not part of it"
                                                       if sd.get("uncommitted") else ""))
        elif sd:
            out("  seed: %s %s, a copy with no history; seed tree %s, computed from its files. An organization born "
                "from this folder gets this tree as its birth hash (fos_init prints it)"
                % (sd.get("name"), sd.get("version"), sd.get("tree")))
        route = s.get("route") or {}
        if route:
            out("  next, for a member opening a new session: %s (%s)" % (route.get("next"), route.get("why")))
        out("  records: %d events, %d proposals (%d open, %d named by a decision awaiting signature), %d decisions "
            "(%d signed, %d awaiting signature, %d refused), %d declines, %d claims"
            % (s["events"], s["proposals"], s["open_proposals"], s.get("proposals_awaiting", 0), s["decisions"],
               s["signed"], s["awaiting_signature"], s["refused"], s["declines"], s["claims"]))
        out("  witness: %s" % s.get("witness", "none"))
        if s.get("configuration"):
            out("  configuration: %s" % s["configuration"])
    if R.fails:
        out("  FAILED (%d):" % len(R.fails))
        for f in R.fails:
            out("   - " + f)
    if R.warns:
        out("  WARNINGS (%d):" % len(R.warns))
        for w in R.warns:
            out("   - " + w)
    if R.notes:
        out("  NOTES:")
        for n in R.notes:
            out("   - " + n)
    out("  Result: %s" % ("FAILED" if R.fails else ("OK, with %d warning(s)" % len(R.warns) if R.warns else "OK")))


def resume_report(out=print):
    """What the last session left, for a member opening a new session (onboarding/SESSION_START.md, step 1):
    the letter, the state, and the decisions the founder signed, then what still waits. It changes nothing."""
    try:
        cfg = L.config()
    except (OSError, ValueError) as e:
        out("org/config.json cannot be read: %s" % e)
        return 1
    records = L.read_all()
    events = records["event"].objs
    st = L.stage_info(cfg, events)["stage"]
    route = L.boot_route(st, cfg, events)
    out("What the organization left for this session. Read it before anything else.")
    out("  next, for a member opening a new session: %s" % route["next"])
    out("  %s" % route["why"])
    if st == "seed":
        return 0
    for rel in ("org/LETTER_TO_NEXT_SESSION.md", "org/STATE.md"):
        out("\n== %s ==" % rel)
        text = L.read_text(rel)
        out(text.rstrip() if text is not None else "(missing)")
    ad = L.adoption(cfg, records)
    sig = ad["sig_status"]
    notes = {s.get("decision_id"): s.get("note") for s in records["signature"].objs if s.get("note")}
    signed = [d for d in ad["decisions"] if sig.get(d.get("id")) == "signed"]
    out("\n== Decisions the founder signed (%d) ==" % len(signed))
    for d in signed:
        out("- %s (session %s; %s): asked \"%s\"" % (d.get("id"), d.get("session"), d.get("verdict"), d.get("question")))
        out("  the founder said: \"%s\"%s" % (d.get("words"), ("; signed with the note \"%s\"" % notes[d["id"]])
                                               if notes.get(d.get("id")) else ""))
    waiting = [d for _, _, d in L.unanswered_decisions(records)]
    out("\n== Recorded but not yet signed (%d): proposals until the founder signs them at a close-out ==" % len(waiting))
    for d in waiting:
        out("- %s (session %s): asked \"%s\"; the founder said: \"%s\"" % (d.get("id"), d.get("session"),
                                                                         d.get("question"), d.get("words")))
    other = [(d, sig[d.get("id")]) for d in ad["decisions"] if sig.get(d.get("id")) in ("refused", "sent_back")]
    if other:
        out("\n== Not signed, or sent back, by the founder (%d) ==" % len(other))
        for d, a in other:
            out("- %s (session %s): %s%s" % (d.get("id"), d.get("session"),
                                            "not signed" if a == "refused" else "sent back",
                                            (": \"%s\"" % notes[d["id"]]) if notes.get(d.get("id")) else ""))
    pstatus, why = L.proposal_status(records, ad)
    props = {p.get("id"): p for p in records["proposal"].objs}
    still = [pid for pid, v in pstatus.items() if v == "open"]
    out("\n== Proposals still open (%d) ==" % len(still))
    for pid in still:
        p = props.get(pid, {})
        out("- %s %s %s: %s%s" % (pid, p.get("kind"), p.get("target"), p.get("change"),
                                   (" (%s)" % why[pid]) if pid in why else ""))
    return 0


def from_witness(argv):
    """Run the check on a fresh clone of the witness, with the witnessed copy of the check itself: a verdict that
    rests on witnessed history only, whatever this folder holds."""
    import shutil
    import subprocess
    import tempfile
    w = L.find_witness()
    if not w or w.get("kind") != "git" or not os.path.isdir(w.get("history") or ""):
        print("No witness history can be read here.")
        return 1
    tmp = tempfile.mkdtemp(prefix="check-")
    try:
        clone = os.path.join(tmp, "c")
        if subprocess.run(["git", "clone", "-q", "-o", "witness", "--no-hardlinks", w["history"], clone],
                          capture_output=True).returncode != 0:
            print("Could not clone the witness.")
            return 1
        tip = subprocess.run(["git", "-C", clone, "rev-parse", "--short", "HEAD"], capture_output=True).stdout
        print("From a fresh clone of the witness at %s, with the witnessed copy of the check:"
              % tip.decode().strip())
        rest = [a for a in argv[1:] if a != "--from-witness"]
        r = subprocess.run([sys.executable, os.path.join(clone, "scripts", "fos_check.py")] + rest, cwd=clone)
        return r.returncode
    finally:
        def unlock(func, p, _):
            os.chmod(p, 0o700)
            func(p)
        shutil.rmtree(tmp, onerror=unlock)


def main(argv):
    if "--from-witness" in argv:
        return from_witness(argv)
    if "--resume" in argv:
        return resume_report()
    R = run_checks()
    if "--json" in argv:
        print(json.dumps({"ok": R.ok, "fails": R.fails, "warnings": R.warns, "notes": R.notes, "summary": R.summary},
                         ensure_ascii=False, indent=1, default=str))
    else:
        report(R)
    return 0 if R.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
