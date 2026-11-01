"""The founder's close-out. Run it yourself, in an ordinary terminal, at the end of a session.

Usage:
  python scripts/fos_close.py              check, sign each decision (y/n), commit, push to the witness
  python scripts/fos_close.py --check-only show what is waiting; change nothing (anyone may run this)

Why the founder runs it, not an AI member: people, not software, answer for what an
organization decides, so a decision becomes final only when a person signs it. The members
record what was asked and what the founder said; the founder reads each decision here and
signs it or not. Unsigned decisions stay proposals.

What it does, in order:
  1. Checks the records and their history (scripts/fos_check.py). If records were deleted or
     rewritten since the last close-out, it offers to restore them from the last commit, keeping
     records added since and recording what it dropped.
  2. Lists every item the check fails, numbered, before anything is signed. If any fails, the founder
     types their number to go on (any other answer, a plain 'y' included, stops the close-out with
     nothing signed), so neither a hurried founder nor a script answering prompts passes over them.
     While the organization is not founded, the founding comes next, asked first and on its own: the
     decision the members recorded as the founding, the structure prepared for it, and "Found the
     organization now on this charter? (type FOUND)". Only the founder's FOUND, typed there, founds it
     (the signature records it); nothing a member writes does. Then lists each decision not yet signed:
     the question as asked, the founder's recorded words, what it decides, and any warning. The founder
     answers y (sign) or n (do not sign). While the organization is not founded, a decision that adopts
     structure is not asked.
  3. Commits everything as the founder, with a message drawn from the records, and pushes the
     commit to the witness, which refuses rewrites and deletions. At the founding, two commits: the
     founding on its own ([FOUND], records only), then the rest, so that no commit holds structure
     before the one that founds the organization (the witness refuses any that does). While the
     organization is not founded, the structural files changed since birth stay in the folder,
     uncommitted. Without git, it saves a dated copy of records/ in the witness folder instead.
Members never need git: this script is the only place commits are made.

It refuses to run without a terminal (an agent app's shell usually has none). In Git Bash on
Windows, run it as: winpty python scripts/fos_close.py, or use PowerShell or Command Prompt.

--test-answers y,n,...  is for the seed's self-test only: answers are taken in order, and
signatures are marked as test signatures, which sign nothing in a real organization.
Standard library only; no network beyond pushing to the witness folder.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402
import fos_witness as W  # noqa: E402
import fos_check as C  # noqa: E402

TEST = {"answers": None}


def _next_test_answer(default):
    a = TEST["answers"].pop(0) if TEST["answers"] else default
    return a.strip()


def ask(prompt, choices=("y", "n"), exact=False):
    """Ask until one of the choices is given. Returns the choice, and the note for an answer written 's=...'.
    exact: the answer must match a choice letter for letter, capitals included (the founding's FOUND)."""
    if TEST["answers"] is not None:
        a = _next_test_answer("n")
        TEST["last"] = a
        print("%s %s   [test answer]" % (prompt, a))
        a = a.split("=", 1)[0] if "=" in a else a
        return a if exact else a.lower()
    while True:
        try:
            a = input(prompt + " ").strip()
        except EOFError:
            return "n"
        if not exact:
            a = a.lower()
            if a in ("yes", "no"):
                a = a[0]
        if a in choices:
            return a
        print("  Please answer %s%s." % (" or ".join(choices), " (in capitals)" if exact else ""))


def ask_note(prompt):
    if TEST["answers"] is not None:
        last = TEST.get("last") or ""
        note = last.split("=", 1)[1] if "=" in last else "test note"
        print("%s %s   [test answer]" % (prompt, note))
        return note
    while True:
        try:
            note = input(prompt + " ").strip()
        except EOFError:
            return ""
        if note:
            return note
        print("  Please write a short note.")


def say(text=""):
    print(text)


def describe_identity(ident):
    ident = ident or {}
    if ident.get("kind") != "ai":
        return ident.get("instance", "?")
    return "%s (model %s by %s, in %s, served by %s)" % (
        ident.get("instance"), ident.get("model_id", "unknown"), ident.get("producer", "unknown"),
        ident.get("agent_app", "unknown"), ident.get("host", "unknown"))


# ---------------------------------------------------------------- step 1: integrity and repair

def baseline(rel, gitok, witness):
    """The last committed (or snapshotted) content of a records file, as bytes, or None."""
    if gitok:
        return L.head_bytes(rel)
    snap = W.latest_snapshot(witness["folder"]) if witness else None
    p = os.path.join(snap, os.path.basename(rel)) if snap else None
    if p and os.path.exists(p):
        with open(p, "rb") as f:
            return f.read()
    return None


def protected_file_damage(gitok, witness):
    """Whole files written once by the seed's scripts (org/BIRTH.json): deleted or changed since the last
    close-out. Returns [(rel, baseline bytes, how)]."""
    out = []
    for rel in (L.BIRTH_FILE,):
        base = baseline(rel, gitok, witness)
        if base is None:
            continue
        cur = L.read_bytes(rel)
        if cur is None:
            out.append((rel, base, "was deleted"))
        elif cur.replace(b"\r\n", b"\n") != base.replace(b"\r\n", b"\n"):
            out.append((rel, base, "was changed"))
    return out


def restore(rel, base):
    """Put back the baseline content, then re-add records that are genuinely new (seq above the
    baseline's). Return (kept, dropped lines)."""
    base = base.replace(b"\r\n", b"\n")
    if base and not base.endswith(b"\n"):
        base += b"\n"
    max_seq = 0
    base_lines = set()
    for raw in base.split(b"\n"):
        if raw.strip():
            base_lines.add(raw)
            try:
                o = json.loads(raw)
                if isinstance(o, dict) and isinstance(o.get("seq"), int):
                    max_seq = max(max_seq, o["seq"])
            except ValueError:
                pass
    cur = (L.read_bytes(rel) or b"").replace(b"\r\n", b"\n")
    kept, dropped = [], []
    for raw in cur.split(b"\n"):
        if not raw.strip() or raw in base_lines:
            continue
        try:
            o = json.loads(raw)
            if isinstance(o, dict) and isinstance(o.get("seq"), int) and o["seq"] > max_seq:
                kept.append(raw)
                continue
        except ValueError:
            pass
        dropped.append(raw.decode("utf-8", errors="replace"))
    with open(L.path(rel), "wb") as f:   # the one place a records file is written whole: restoring it
        f.write(base + b"".join(k + b"\n" for k in kept))
    return len(kept), dropped


def integrity_step(gitok, witness):
    """Find deleted or rewritten records files; offer to restore each. Return False to stop."""
    damaged = []
    for kind, rel in L.RECORD_FILES.items():
        base = baseline(rel, gitok, witness)
        if base is None:
            continue
        cur = L.read_bytes(rel)
        if cur is None:
            damaged.append((rel, base, "was deleted"))
        elif not W.is_append(base.replace(b"\r\n", b"\n"), cur.replace(b"\r\n", b"\n")):
            damaged.append((rel, base, "had earlier lines changed or removed"))
    whole = protected_file_damage(gitok, witness)
    if not damaged and not whole:
        return True
    lost_birth = any(rel == L.RECORD_FILES["event"] and not L._born_in(L.read_bytes(rel)) and L._born_in(base)
                     for rel, base, _ in damaged)
    say("\nSince the last close-out, these records were damaged:")
    for rel, _, how in damaged + whole:
        say("  - %s %s" % (rel, how))
    if lost_birth:
        say("records/events.jsonl lost the organization's birth record with it. This folder is still an organization: "
            "its history and its witness hold the birth.")
    say("Records may only grow (AGENTS.md, CORE-4). Restoring puts back what was there at the last close-out and "
        "keeps any records added since. Lines that were changed are kept in the repair record, not lost.")
    if ask("Restore these files now?") != "y":
        say("Stopped. Nothing was committed or signed.")
        return False
    repairs = []
    # events.jsonl first, and every file before any repair record is written: a repair record appended to a
    # file that is about to be restored would itself be set aside.
    damaged.sort(key=lambda d: d[0] != L.RECORD_FILES["event"])
    for rel, base, how in damaged:
        kept, dropped = restore(rel, base)
        repairs.append({"type": "integrity_repair", "captured_by": "close_script",
                        "summary": "%s %s; restored from the last close-out, %d newer record(s) kept, %d changed "
                                   "line(s) set aside" % (rel, how, kept, len(dropped)),
                        "refs": [rel], "dropped_lines": dropped})
        say("  restored %s (%d newer record(s) kept, %d changed line(s) set aside in the repair record)"
            % (rel, kept, len(dropped)))
    for rel, base, how in whole:
        cur = L.read_bytes(rel)
        with open(L.path(rel), "wb") as f:   # a file the seed writes once: put back exactly as it was
            f.write(base)
        repairs.append({"type": "integrity_repair", "captured_by": "close_script",
                        "summary": "%s %s; restored from the last close-out" % (rel, how), "refs": [rel],
                        "dropped_lines": [] if cur is None else [cur.decode("utf-8", errors="replace")]})
        say("  restored %s" % rel)
    for rec in repairs:
        L.append_record("event", rec, writer="fos_close")
    return True


def void_foreign_signatures(gitok, witness):
    """Signature lines written since the last completed close-out were not written by one. Mark them void."""
    base = baseline(L.RECORD_FILES["signature"], gitok, witness)
    if base is None and not (gitok or witness):
        return 0
    known = {raw for raw in (base or b"").replace(b"\r\n", b"\n").split(b"\n") if raw.strip()}
    n = 0
    for _, raw, s in L.read_records(L.RECORD_FILES["signature"]).rows:
        if raw not in known:
            L.append_record("event", {"type": "record_correction", "captured_by": "close_script",
                                      "corrects": {"file": "records/signatures.jsonl", "seq": s.get("seq")},
                                      "summary": "signature line %s was written after the last close-out, not by a "
                                                 "completed close-out; it is void" % s.get("seq")}, writer="fos_close")
            n += 1
    if n:
        say("\n%d signature line(s) were written since the last close-out by something other than a completed "
            "close-out. They stay in the record, marked void. You will be asked to sign again." % n)
    return n


def mark_bad_lines():
    """Offer to note malformed lines that nobody has corrected, so the record stays readable."""
    events = L.read_records(L.RECORD_FILES["event"]).objs
    corr = C.corrections_index(events)
    todo = []
    for kind, rel in L.RECORD_FILES.items():
        for ln, raw, msg in L.read_records(rel).bad:
            if (rel, "line", ln) not in corr:
                todo.append((rel, ln, msg))
    if not todo:
        return
    say("\nThese lines are not valid records, and no correction points to them yet:")
    for rel, ln, msg in todo:
        say("  - %s line %d (%s)" % (rel, ln, msg))
    if ask("Mark them as defects? (They stay where they are, with a note.)") == "y":
        for rel, ln, msg in todo:
            L.append_record("event", {"type": "record_correction", "captured_by": "close_script",
                                      "corrects": {"file": rel, "line": ln},
                                      "summary": "line %d of %s is not a valid record (%s); noted at close-out"
                                                 % (ln, rel, msg)}, writer="fos_close")


def session_step(gitok):
    """When no session_start was recorded since the last close-out, say so and put the gap on record."""
    events = L.read_records(L.RECORD_FILES["event"]).objs
    if L.session_recorded(events):
        return None
    label = L.current_session(events)
    if any(e.get("type") == "unrecorded_session" for e in L.since_last_close(events)):
        return label          # already on record (for example, before a sync restarted this close-out)
    activity = C.activity_since_close(gitok)
    if activity:
        summary = ("no session_start was recorded for %s, but %s: a member worked without recording its session"
                   % (label, "; ".join(activity)))
        say("\nNote: " + summary + ". The close-out puts the gap on record.")
        answer = "not asked: the folder shows activity"
    else:
        say("\nNothing was recorded and no file changed since the last close-out.")
        a = ask("Did you work with an AI member in this organization since the last close-out?")
        answer = "yes" if a == "y" else "no"
        summary = ("the founder says a session took place for %s, but it left no record and changed no file" % label
                   if a == "y" else "no session took place since the last close-out (the founder's answer)")
    L.append_record("event", {"type": "unrecorded_session", "captured_by": "close_script", "session": label,
                              "summary": summary[0].upper() + summary[1:], "founder_answer": answer}, writer="fos_close")
    return label


# ---------------------------------------------------------------- step 2: signing

def unsigned_decisions(cfg, records):
    """Decisions with no signature line (signed or not) from a close-out, other than void ones."""
    return L.unanswered_decisions(records)


JUDGEMENT_KINDS = {"decision_right", "role", "role_instance", "model_slot", "tool", "records_policy", "check"}


def disk_changes():
    """What changed on disk since the last close-out: the files this close-out will commit."""
    if not (L.git_ok() and L.has_head()):
        return ["(git is not available here, so the changes since the last close-out cannot be listed)"]
    out = []
    code, numstat = L.git("diff", "--numstat", "HEAD")
    for ln in numstat.splitlines():
        parts = ln.split("\t")
        if len(parts) == 3:
            out.append("%s (+%s -%s)" % (parts[2], parts[0], parts[1]))
    code, new = L.git("ls-files", "--others", "--exclude-standard")
    out += ["%s (new)" % x for x in new.splitlines() if x.strip()]
    return out


def describe(d, props, effects, warnings):
    """The text shown to the founder for one decision; its hash goes into the signature."""
    lines = ["%s  (session %s; verdict: %s)" % (d.get("id"), d.get("session"), d.get("verdict")),
             "  Asked:       %s" % d.get("question"),
             "  You said:    \"%s\"" % d.get("words")]
    for pid in d.get("proposal_ids") or []:
        p = props.get(pid, {})
        lines.append("  It decides:  %s  %s %s: %s" % (pid, p.get("kind", "?"), p.get("target", "?"), p.get("change", "?")))
    for pid in d.get("proposal_ids") or []:
        p = props.get(pid, {})
        if p.get("background"):
            lines.append("  Background:  %s" % p["background"])
        if p.get("if_undecided"):
            lines.append("  If nobody decides: %s" % p["if_undecided"])
        if p.get("cost_of_waiting"):
            lines.append("  Waiting costs: %s" % p["cost_of_waiting"])
    if d.get("amendment"):
        lines.append("  As amended:  %s" % d.get("amendment"))
    if d.get("verdict") in ("adopted", "amended"):
        lines.append("  If you sign: %s" % ("; ".join(effects) if effects else
                                            "nothing in the organization's files names this decision yet"))
    else:
        lines.append("  If you sign: the %s verdict becomes final; nothing changes in the organization" % d.get("verdict"))
    lines.append("  Recorded by: %s" % describe_identity(d.get("identity")))
    for w in warnings:
        lines.append("  ! %s" % w)
    return "\n".join(lines)


def needs_judgement(cfg, d, props, warnings):
    """Decisions asked on their own: any warning, an amendment, the founding, a missing proposal, or a change to
    who decides, who is a member, or what tools may do. The rest form the routine group."""
    if warnings or d.get("verdict") == "amended":
        return True
    if cfg.get("organization", {}).get("founding_decision") == d.get("id") or d.get("founding") is True:
        return True
    pids = d.get("proposal_ids") or []
    if any(p not in props for p in pids):
        return True
    return bool({props[p].get("kind") for p in pids if p in props} & JUDGEMENT_KINDS)


def record_answer(cfg, raw, d, answer, note, shown_text, shown, session, founding=False):
    """Write the founder's answer as a signature. It runs only inside main(), once main() has passed its terminal
    guard (fos_lib's signing gate): a member's script that imports this file and calls it is refused."""
    if not L.signing_open():
        raise L.RecordError(L.SIGNING_REFUSED)
    rec = {"decision_id": d.get("id"), "decision_seq": d.get("seq"), "decision_sha256": L.line_sha256(raw),
           "answer": {"y": "signed", "s": "signed", "n": "refused", "b": "sent_back"}[answer],
           "mode": "test" if TEST["answers"] is not None else "terminal",
           "signer": sorted(L.founder_instances(cfg))[0] if L.founder_instances(cfg) else "founder",
           "captured_by": "close_script", "session": session, "shown": shown,
           "shown_sha256": L.line_sha256(shown_text)}
    if note:
        rec["note"] = note
    if founding:
        rec["founding"] = W.FOUNDING_WORD     # the founder typed it at the founding prompt: this founds the organization
    line, _ = L.append_record("signature", rec, writer="fos_close")
    L.PENDING_OWN_SIGNATURES.add(json.loads(line)["seq"])   # this close-out commits them next
    return rec["answer"]


def ask_one(cfg, raw, d, text, shown, session):
    say(text)
    a = ask("Sign %s?  y = sign   s = sign with a note   n = do not sign (it stays a proposal)   "
            "b = send it back to the members with a note" % d.get("id"), ("y", "s", "n", "b"))
    note = ask_note("Your note:") if a in ("s", "b") else None
    say("")
    return record_answer(cfg, raw, d, a, note, text, shown, session)


FOUND_PROMPT = "Found the organization now on this charter? (type FOUND)"
CANNOT = "cannot be put back here"


def _item_of(rel, where):
    """The structural item a change inside a JSON file belongs to, as (kind, label), the kinds put_back() knows; None for
    a change outside every item (a reserved right, a setting, a text file's line)."""
    if rel == "org/config.json" and len(where) >= 2:
        if where[0] == "roles" and len(where) >= 4 and where[2] == "instances":
            return ("role instance", "%s/%s" % (where[1], where[3]))
        kind = {"modules": "module", "roles": "role", "checks": "check", "retired_roles": "retired role"}.get(where[0])
        if kind:
            return (kind, where[1])
        if where[:2] == ["decision_rights", "delegated"]:
            return ("delegated right", None)
    if rel == "org/TOOLS.json" and len(where) >= 2 and where[0] == "tools":
        return ("tool", where[1])
    if rel == "view/VIEWS.json":
        return ("view", "view/VIEWS.json")
    return None


def founding_changes(cfg, founding_id):
    """What the structure prepared for the founding changes from the organization's birth, every change in plain words,
    each marked with what this close-out can do about it: adopted by the founding; no decision adopts it, so the close-out
    offers to put it back after the founding (choose_what_to_commit); or it cannot be put back here, so the founder who
    does not want it answers n or b. Returns (lines, how many changes in JSON files cannot be put back, the text files
    changed: this close-out puts no text file's lines back)."""
    changes = L.structure_changes() or []
    tools = L.tools_registry()
    try:
        views = L.load_json("view/VIEWS.json")
    except (OSError, ValueError):
        views = None
    named = {(k, lab): ab for k, lab, ab in L.structural_items(cfg, tools, views)}
    loose = {(k, lab) for k, lab, _ in unadopted_changes(cfg)}
    cannot, per_file = 0, {}
    for rel, where, words in changes:
        out = per_file.setdefault(rel, [])
        what = ("%s: %s" % (" > ".join(str(x) for x in where), words)) if where else words
        if not rel.endswith(".json"):
            out.append("      %s" % what)
            continue
        item = _item_of(rel, where)
        if item and item[0] == "delegated right":
            delegated = [(k, lab) for k, lab in named if k == "delegated right"]
            if any(x in loose for x in delegated):
                mark = "no decision adopts a delegated right here: the close-out offers to put it back, after the founding"
            elif delegated and all(named[x] == founding_id for x in delegated):
                mark = "adopted by %s, this founding" % founding_id
            else:
                mark = CANNOT
        elif item in loose:
            mark = "no decision adopts it: the close-out offers to put it back, after the founding"
        elif item in named and named[item] == founding_id:
            mark = "adopted by %s, this founding" % founding_id
        elif item in named and named[item]:
            mark = "named as adopted by %s: it counts only once you sign %s" % (named[item], named[item])
        else:
            mark = CANNOT
        cannot += mark == CANNOT
        out.append("      - %s   [%s]" % (what, mark))
    lines = []
    for rel, out in per_file.items():
        lines.append("    %s%s" % (rel, "" if rel.endswith(".json") else
                                   " (a text file: this close-out does not put its lines back)"))
        lines.extend(out[:30])
        if len(out) > 30:
            lines.append("      ... and %d more change(s): read the file itself before you type FOUND" % (len(out) - 30))
    return lines, cannot, [rel for rel in per_file if not rel.endswith(".json")]


def ask_founding(cfg, raw, d, props, effects, warnings, base, prepared, session):
    """The founding, asked first and on its own, once the failures are acknowledged. Only the founder's FOUND, typed
    here, founds the organization: the signature records it (founding "FOUND"), and the close-out commits that
    signature on its own ([FOUND]) before any structure. n leaves the decision unsigned and the organization not
    founded; b sends it back. Returns the answer recorded ('signed', 'refused' or 'sent_back')."""
    did = d.get("id")
    text = describe(d, props, effects, warnings)
    text += ("\n  If you found it: the organization is founded on this charter, by your signature on %s, and this "
             "close-out then commits the structure prepared for it, after the founding: %s"
             % (did, W.describe_differences(prepared) if prepared else "none (no structural file differs from birth)"))
    change_lines, cannot, texts = founding_changes(cfg, did) if prepared else ([], 0, [])
    if change_lines:
        # Every change from the birth, as it is, not only the files and keys it touches: what the founder founds on.
        text += "\n  What that structure changes from the organization's birth, every change:\n" + "\n".join(change_lines)
        if cannot or texts:
            text += ("\n  This close-out cannot put back %s. If you type FOUND, they are part of the organization you "
                     "found. If you do not want one, answer n (or b, with a note for the members), and have it undone "
                     "before the next close-out." % " or ".join(
                         (["the %d change(s) marked '%s'" % (cannot, CANNOT)] if cannot else [])
                         + (["the lines of %s" % ", ".join(texts)] if texts else [])))
    say("The founding (asked first, on its own):\n")
    say(text)
    a = ask("%s   n = not now (%s is not signed; the organization stays unfounded)   b = send it back to the members "
            "with a note" % (FOUND_PROMPT, did), (W.FOUNDING_WORD, "n", "b"), exact=True)
    if a not in (W.FOUNDING_WORD, "b"):
        a = "n"
    note = ask_note("Your note:") if a == "b" else None
    say("")
    shown = dict(base, effects=effects, warnings=warnings, asked="at the founding prompt, on its own",
                 founding_prompt=FOUND_PROMPT, structure=["%s (%s)" % x for x in prepared],
                 structure_changes=[x.strip() for x in change_lines])
    return record_answer(cfg, raw, d, "y" if a == W.FOUNDING_WORD else a, note, text, shown, session,
                         founding=a == W.FOUNDING_WORD)


def signing_step(cfg, warnings_by_decision, check_line, R=None):
    records = L.read_all()
    session = L.current_session(records["event"].objs)
    props = {p.get("id"): p for p in records["proposal"].objs}
    tools = L.tools_registry()
    try:
        views = L.load_json("view/VIEWS.json")
    except (OSError, ValueError):
        views = None
    todo = unsigned_decisions(cfg, records)
    answered = {"signed": [], "refused": [], "sent_back": [], "held": [], "founded": None}
    by = L.structure_by_decision(cfg, tools, views)   # what the files name each decision as adopting, whatever its labels
    founded = L.founding_state(cfg, records)["founded"]
    candidate = None if founded else L.founding_candidate(cfg, todo)
    cannot = None                 # a founding deferred, declined or not decided by the founder cannot found it
    if candidate and not (candidate[1].get("verdict") in L.ADOPTING_VERDICTS
                          and candidate[1].get("id") in L.authorized_decisions(cfg, [candidate[1]])):
        cannot = "%s is recorded as the founding, but %s, so it cannot found the organization; it is asked as recorded" % (
            candidate[1].get("id"), ("its verdict is %s" % candidate[1].get("verdict"))
            if candidate[1].get("verdict") not in L.ADOPTING_VERDICTS else "the founder did not decide it")
        candidate = None
    if not todo:
        say("\nNo decisions are waiting for your signature.")
        return answered
    changes = disk_changes()
    fails = list(R.fails) if R else []
    prepared = [] if founded else (L.structure_since_birth() or [])
    say("\nBefore you sign, the state of the organization:")
    say("  Check: %s" % check_line)
    if fails:
        say("  What fails, before you sign anything (%d item(s), every one):" % len(fails))
        for i, f in enumerate(fails, 1):
            say("    %d. %s" % (i, f))
    say("  Changed since the last close-out (this close-out will commit it):")
    for c in changes[:25] or ["(nothing)"]:
        say("    " + c)
    if len(changes) > 25:
        say("    ... and %d more" % (len(changes) - 25))
    if not founded:
        say("  The organization is not founded yet%s." % (
            ": the structure prepared for its founding is committed only once you found it (type FOUND): %s"
            % W.describe_differences(prepared) if prepared else ""))
    w = L.find_witness()
    refused = [p for p in (W.read_push_log(w["folder"]) if w else []) if p.get("result") == "refused"]
    if refused:
        say("  The witness has refused %d push(es) so far; the latest, at %s: %s"
            % (len(refused), refused[-1].get("ts"), "; ".join(refused[-1].get("reasons") or [])[:200]))
    say("A signature makes a decision final, and it is yours: sign only what you have read and decided.\n")
    acknowledged = None
    if fails:
        # Failures are not passed over by a 'y': whoever answers (a founder at the keyboard, or a script or plan
        # answering prompts) must give the number of failing items, or the close-out stops before any signature.
        say("The check fails on %d item(s), listed above. Signing does not repair them: the commit records them, and "
            "each decision they concern is marked when it is asked." % len(fails))
        a = ask("Type %d, the number of failing items, to say you have read them and go on to signing; or n to stop "
                "here, with nothing signed or committed:" % len(fails), (str(len(fails)), "n"))
        if a != str(len(fails)):
            say("\nStopped before signing: the %d failing item(s) were not acknowledged%s. Nothing was signed or "
                "committed. Read them (python scripts/fos_check.py), and run the close-out again when ready."
                % (len(fails), (" (the answer was %r)" % a) if a not in ("n", "") else ""))
            return None
        acknowledged = len(fails)
        say("")
    judged, routine = [], []
    adopts = {}   # decision id -> what it adopts, for a decision that adopts structure (by its proposals or its effects)
    found_item = None
    for ln, raw, d in todo:
        warnings = list(warnings_by_decision.get(d.get("id"), []))
        items = set(L.effect_items(cfg, d.get("id"), tools, views))
        if d.get("verdict") in L.ADOPTING_VERDICTS and not (candidate and d is candidate[1]):
            what = L.structural_proposals(d, props) + by.get(d.get("id"), [])
            if what:
                adopts[d.get("id")] = what
        for kind, label, msg in (R.item_fails if R else []):
            if (kind, label) in items:
                warnings.append("THE CHECK FAILS for what this decision adopts: " + msg)
        for msg in (R.decision_fails.get(d.get("id"), []) if R else []):
            warnings.append("THE CHECK FAILS for this decision: " + msg)
        effects = L.effects_of(cfg, d.get("id"), tools, views)
        item = (raw, d, effects, warnings)
        if candidate and d is candidate[1]:
            found_item = item
        else:
            (judged if needs_judgement(cfg, d, props, warnings) else routine).append(item)
    hashes = {p: L.file_sha256(p) for _, p in changed_paths()[:25]}
    base = {"check": check_line, "check_failures": fails, "failures_acknowledged": acknowledged,
            "changed_files": changes[:25], "changed_files_sha256": {p: h for p, h in hashes.items() if h}}
    if found_item:
        raw, d, effects, warnings = found_item
        answer = ask_founding(cfg, raw, d, props, effects, warnings, base, prepared, session)
        answered[answer].append(d.get("id"))
        if answer == "signed":
            founded, answered["founded"] = True, d.get("id")
    elif not founded:
        say("%s. The organization is not founded, and cannot be at this close-out (onboarding/START.md, step 8).\n"
            % (cannot or "No decision is recorded as the founding"))

    def held(d):
        """While the organization is not founded, a decision that adopts structure would come before its founding
        (onboarding/START.md, step 8): it is not asked, and waits."""
        if founded or d.get("id") not in adopts:
            return False
        say("Not asked: %s adopts structure (%s), and the organization is not founded%s, so nothing is adopted before "
            "its founding (onboarding/START.md, step 8). %s stays waiting; its proposals can be named in the next "
            "founding question.\n" % (d.get("id"), ", ".join(adopts[d.get("id")]),
                                       " (you did not found it just now)" if found_item else "", d.get("id")))
        answered["held"].append(d.get("id"))
        return True

    judged = [item for item in judged if not held(item[1])]
    if judged:
        say("Needs your judgement (%d): each is asked on its own.\n" % len(judged))
        for raw, d, effects, warnings in judged:
            text = describe(d, props, effects, warnings)
            shown = dict(base, effects=effects, warnings=warnings, asked="on its own")
            answer = ask_one(cfg, raw, d, text, shown, session)
            answered[answer].append(d.get("id"))
    routine = [item for item in routine if not held(item[1])]
    if routine:
        say("Routine (%d): no warnings, and nothing that changes who decides, who is a member, or what tools may do.\n"
            % len(routine))
        texts = [describe(d, props, effects, warnings) for raw, d, effects, warnings in routine]
        for t in texts:
            say(t)
            say("")
        together = ask("Sign all %d routine decisions together? (y = sign all; n = go through them one by one)"
                       % len(routine))
        for (raw, d, effects, warnings), text in zip(routine, texts):
            if together == "y":
                shown = dict(base, effects=effects, warnings=warnings, asked="in the routine group, signed together")
                answered[record_answer(cfg, raw, d, "y", None, text, shown, session)].append(d.get("id"))
            else:
                shown = dict(base, effects=effects, warnings=warnings, asked="from the routine group, on its own")
                answered[ask_one(cfg, raw, d, text, shown, session)].append(d.get("id"))
    return answered


# ---------------------------------------------------------------- step 3: commit and witness

def waiting_list():
    text = L.read_text("org/STATE.md", "")
    out, on = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            on = line[3:].strip().lower().startswith("waiting for close-out")
            continue
        if on and line.lstrip().startswith(("-", "*")):
            out.append(line.rstrip())
    return out


def regenerate():
    import fos_rules
    import fos_render
    fos_rules.main()
    if hasattr(fos_render, "build"):
        fos_render.main()


def ensure_author():
    """The founder's name for this organization's commits, kept in this folder's own git settings. A name or
    e-mail address set for git on the whole machine is never used, so it cannot enter the history unasked."""
    code, out = L.git("config", "--local", "--get", "user.name")
    name = out.strip() if code == 0 else ""
    if not name:
        if TEST["answers"] is not None:
            name = "Test Founder"
        else:
            say("\nGit needs a name to record as the author of this close-out. It stays in the organization's history "
                "and is kept for this organization only.")
            while not name:
                try:
                    name = input("Your name: ").strip()
                except EOFError:
                    return None
        L.git("config", "--local", "user.name", name)
    if L.git("config", "--local", "--get", "user.email")[0] != 0:
        L.git("config", "--local", "user.email", "")
    return name


def commit(message, paths):
    """Commit exactly `paths` (additions, changes and deletions), nothing else."""
    stamp = "%d +0000" % int(__import__("time").time())
    env = dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    import subprocess
    subprocess.run(["git", "-C", L.ROOT, "reset", "-q"], capture_output=True)      # start from an empty selection
    for i in range(0, len(paths), 100):
        subprocess.run(["git", "-C", L.ROOT, "add", "-A", "--"] + paths[i:i + 100], capture_output=True)
    r = subprocess.run(["git", "-C", L.ROOT, "commit", "-q", "-F", "-"], input=message.encode("utf-8"),
                       capture_output=True, env=env)
    if r.returncode != 0:
        say(r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace"))
        return None
    return L.git("rev-parse", "--short", "HEAD")[1].strip()


# ---------------------------------------------------------------- what gets committed: a choice, not everything

def changed_paths():
    """[(status, path)] for every path changed since the last commit, untracked files included."""
    code, out = L.git("status", "--porcelain", "--untracked-files=all", "--no-renames")
    rows = []
    for ln in (out.splitlines() if code == 0 else []):
        if ln.strip():
            rows.append((ln[:2], ln[3:].strip().strip('"')))
    return [(s, p) for s, p in rows if not p.startswith(".fos-lock")]


def _head_json(rel):
    data = L.head_bytes(rel)
    try:
        return json.loads(data.decode("utf-8")) if data else None
    except (ValueError, UnicodeDecodeError):
        return None


def _find(items, key, value):
    for i, x in enumerate(items or []):
        if isinstance(x, dict) and x.get(key) == value:
            return i, x
    return None, None


def item_json(cfg, tools, views, kind, label):
    """The JSON of one structural item, for comparing it with the last close-out."""
    if kind == "module":
        return _find(cfg.get("modules"), "id", label)[1]
    if kind == "role":
        return _find(cfg.get("roles"), "id", label)[1]
    if kind == "role instance":
        rid, _, iid = label.partition("/")
        role = _find(cfg.get("roles"), "id", rid)[1] or {}
        return _find(role.get("instances"), "id", iid)[1]
    if kind == "check":
        return _find(cfg.get("checks"), "id", label)[1]
    if kind == "delegated right":
        for g in (cfg.get("decision_rights") or {}).get("delegated", []):
            if "%s -> %s" % (g.get("right"), g.get("to")) == label:
                return g
        return None
    if kind == "retired role":
        return _find(cfg.get("retired_roles"), "id", label)[1]
    if kind == "tool":
        return _find((tools or {}).get("tools"), "id", label)[1]
    if kind == "view":
        return views
    return None


def unadopted_changes(cfg):
    """Structural items with no signed decision (and none awaiting one) that changed since the last close-out."""
    records = L.read_all()
    ad = L.adoption(cfg, records)
    tools = L.tools_registry()
    try:
        views = L.load_json("view/VIEWS.json")
    except (OSError, ValueError):
        views = None
    hc = _head_json("org/config.json") or {}
    ht, hv = _head_json("org/TOOLS.json") or {"tools": []}, _head_json("view/VIEWS.json")
    out = []
    for kind, label, ab in L.structural_items(cfg, tools, views):
        if L.governed(ab, ad["signed"], kind, label) or ab in ad["awaiting"]:
            continue
        if item_json(cfg, tools, views, kind, label) == item_json(hc, ht, hv, kind, label):
            continue
        out.append((kind, label, ab))
    return out


def put_back(items):
    """Return each item to how it was at the last close-out (or remove it, if it did not exist then).
    Returns the items as they were before, for the record."""
    cfg = L.config()
    tools = L.tools_registry()
    hc = _head_json("org/config.json") or {}
    ht = _head_json("org/TOOLS.json") or {"tools": []}
    before = []
    view_back = False
    order = {"role": 0, "retired role": 1, "role instance": 2}
    for kind, label, ab in sorted(items, key=lambda x: order.get(x[0], 3)):
        before.append({"kind": kind, "label": label, "adopted_by": ab,
                       "was": item_json(cfg, tools, None, kind, label) if kind != "view" else "view/VIEWS.json"})
        if kind in ("module", "role", "check", "retired role", "tool"):
            key = {"module": "modules", "role": "roles", "check": "checks", "retired role": "retired_roles"}.get(kind)
            here = tools.setdefault("tools", []) if kind == "tool" else cfg.setdefault(key, [])
            there = (ht.get("tools") if kind == "tool" else hc.get(key)) or []
            i, _ = _find(here, "id", label)
            _, old = _find(there, "id", label)
            if i is None:
                continue
            if old is not None:
                here[i] = old
            elif kind == "module":
                here[i] = {"id": label, "state": "off", "adopted_by": None}
            else:
                here.pop(i)
            if kind == "retired role":
                _, old_role = _find(hc.get("roles"), "id", label)
                if old_role is not None and _find(cfg.get("roles"), "id", label)[0] is None:
                    cfg.setdefault("roles", []).append(old_role)
        elif kind == "role instance":
            rid, _, iid = label.partition("/")
            _, role = _find(cfg.get("roles"), "id", rid)
            _, old_role = _find(hc.get("roles"), "id", rid)
            if role is None:
                continue
            i, _ = _find(role.get("instances"), "id", iid)
            _, old = _find((old_role or {}).get("instances"), "id", iid)
            if i is not None:
                if old is not None:
                    role["instances"][i] = old
                else:
                    role["instances"].pop(i)
        elif kind == "delegated right":
            here = (cfg.setdefault("decision_rights", {})).setdefault("delegated", [])
            there = (hc.get("decision_rights") or {}).get("delegated", [])
            match = [j for j, g in enumerate(here) if "%s -> %s" % (g.get("right"), g.get("to")) == label]
            olds = [g for g in there if "%s -> %s" % (g.get("right"), g.get("to")) == label]
            for j in reversed(match):
                here.pop(j)
            here.extend(olds)
        elif kind == "view":
            view_back = True
    with open(L.path("org/config.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    if any(k == "tool" for k, _, _ in items):
        with open(L.path("org/TOOLS.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(tools, f, indent=2, ensure_ascii=False)
            f.write("\n")
    if view_back:
        data = L.head_bytes("view/VIEWS.json")
        if data is not None:
            with open(L.path("view/VIEWS.json"), "wb") as f:
                f.write(data)
    return before


def seed_owned_tops():
    """Top-level names the seed itself shipped (at the first commit) other than the organization's folders."""
    root = L.root_commit()
    code, out = L.git("ls-tree", "--name-only", root) if root else (1, "")
    tops = set(out.split()) if code == 0 else set()
    return tops - set(C.ORG_FOLDERS), tops


def set_aside_copies(witness, paths, why):
    """Copy files into <witness>/set_aside/<UTC time>/close_out/ before putting them back. Returns the folder."""
    import datetime
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    dest = os.path.join(witness["folder"], "set_aside", stamp, "close_out")
    for p in paths:
        data = L.read_bytes(p)
        if data is None:
            continue
        out = os.path.join(dest, *p.split("/"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(data)
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(os.path.dirname(dest), "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"why": why, "files": paths}, f, indent=1)
    return dest


def choose_what_to_commit(cfg, witness):
    """Let the founder keep unadopted structure, the seed's own files and stray files out of the commit.
    Returns the list of paths to commit."""
    excluded = set()
    unadopted = unadopted_changes(cfg)
    if unadopted:
        say("\nThese structural changes have no signed decision behind them:")
        for kind, label, ab in unadopted:
            say("  - %s '%s' (adopted_by: %s)" % (kind, label, ab))
        if ask("Put each back as it was at the last close-out? (n = commit them as they are, still proposals)") == "y":
            before = put_back(unadopted)
            L.append_record("event", {"type": "structure_change", "captured_by": "close_script",
                                      "summary": "Put back as at the last close-out, because no signed decision "
                                                 "adopts them: %s" % "; ".join("%s '%s'" % (k, l) for k, l, _ in unadopted),
                                      "refs": [ab for _, _, ab in unadopted if ab], "put_back": before},
                            writer="fos_close")
            say("  put back; what they were is kept in the record")
    rows = changed_paths()
    seed_tops, born_tops = seed_owned_tops()
    seed_files = [p for _, p in rows if p.split("/")[0] in seed_tops]
    outside = [p for _, p in rows if p.split("/")[0] not in born_tops and p.split("/")[0] not in C.ORG_FOLDERS]
    if seed_files:
        say("\nThese are the seed's own files or its documentation, which members do not edit (CORE-9):")
        for p in seed_files[:20]:
            say("  - " + p)
        put = "n"
        if witness and os.path.isdir(witness.get("folder") or ""):
            put = ask("Put them back as they were at the last close-out? (a copy of each changed version is kept "
                      "in the witness folder)")
        if put == "y":
            dest = set_aside_copies(witness, seed_files, "the seed's own files, changed by members, put back at close-out")
            tracked = names_in_head(seed_files)
            for p in seed_files:
                if p in tracked:
                    L.git("checkout", "HEAD", "--", p)
                elif os.path.exists(L.path(p)):
                    os.remove(L.path(p))
            rel_dest = os.path.relpath(dest, os.path.dirname(L.ROOT)).replace("\\", "/")
            L.append_record("event", {"type": "integrity_repair", "captured_by": "close_script",
                                      "summary": "Put back %d of the seed's own file(s) as at the last close-out; the "
                                                 "changed versions are kept in %s" % (len(seed_files), rel_dest),
                                      "refs": seed_files[:50] + [rel_dest]}, writer="fos_close")
            say("  put back; the changed versions are in %s" % dest)
        elif ask("Leave them out of this commit? (they stay changed in the folder, uncommitted)") == "y":
            excluded.update(seed_files)
    if outside:
        say("\nThese are outside the organization's folders (work goes in work/, sources in sources/):")
        for p in outside[:20]:
            say("  - " + p)
        if ask("Leave them out of this commit? (they stay in the folder, uncommitted)") == "y":
            excluded.update(outside)
    return [p for _, p in changed_paths() if p not in excluded], sorted(excluded)


def write_founding(did):
    """At the founding, the close-out itself writes org/config.json's organization block: founded, the date (UTC) and
    the decision. The history is what counts (fos_lib.founding_state); this keeps config.json saying the same."""
    cfg = L.config()
    cfg.setdefault("organization", {}).update(founded=True, founded_on=L.now_utc()[:10], founding_decision=did)
    with open(L.path("org/config.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")


def unfound_config():
    """While no close-out has founded the organization, org/config.json does not say it is founded: a founded, founded_on
    written by a member is set back (the founding happens when the founder types FOUND at a close-out)."""
    cfg = L.config()
    org = cfg.get("organization") or {}
    if not (org.get("founded") or org.get("founded_on")):
        return
    org.update(founded=False, founded_on=None)
    with open(L.path("org/config.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    say("\norg/config.json said the organization is founded. No close-out has founded it, so founded is set back to "
        "false: it is founded when you type FOUND at a close-out.")


def held_structure():
    """The structural files that differ from the organization's birth, while it is not founded: the close-out leaves
    them out of its commit, so no commit holds structure before the founding."""
    diffs = L.structure_since_birth() or []
    changed = {p for _, p in changed_paths()}
    return [rel for rel, _ in diffs if rel in changed]


def names_in_head(paths):
    code, out = L.git("ls-tree", "-r", "--name-only", "HEAD", "--", *paths) if paths else (1, "")
    return set(out.split("\n")) if code == 0 else set()


def records_waiting_list(cfg, answered):
    """The commit's list of what this close-out decided, drawn from the records, whatever org/STATE.md says."""
    tools = L.tools_registry()
    try:
        views = L.load_json("view/VIEWS.json")
    except (OSError, ValueError):
        views = None
    out = []
    decisions = {d.get("id"): d for d in L.read_records(L.RECORD_FILES["decision"]).objs}
    for label, ids in (("signed", answered["signed"]), ("not signed", answered["refused"]),
                       ("sent back", answered["sent_back"])):
        for did in ids:
            eff = L.effects_of(cfg, did, tools, views)
            line = "- %s %s%s" % (did, label, (": " + "; ".join(eff)) if eff else "")
            if label != "signed" and (decisions.get(did) or {}).get("proposal_ids"):
                line += " (still open: %s)" % ", ".join(decisions[did]["proposal_ids"])
            out.append(line)
    return out


def push_to_witness(witness):
    import subprocess
    code, branch = L.git("branch", "--show-current")
    branch = branch.strip() or "main"
    r = subprocess.run(["git", "-C", L.ROOT, "push", "witness", branch], capture_output=True)
    text = (r.stdout + r.stderr).decode("utf-8", "replace")
    lines = [ln.replace("remote: ", "  ").rstrip() for ln in text.splitlines()
             if ln.startswith("remote:") and ln.strip() != "remote:"]
    for ln in lines:
        say(ln)
    return r.returncode == 0


def offer_witness():
    folder = L.default_witness_folder()
    say("\nThis organization has no witness: a copy of its history, kept outside this folder, that refuses "
        "rewrites and deletions.")
    if ask("Create one now at %s?" % folder) != "y":
        return None
    if W.setup(folder) != 0:
        return None
    L.git("remote", "add", "witness", os.path.join(folder, "history.git"))
    return L.find_witness()


def main(argv):
    check_only = "--check-only" in argv
    if "--test-answers" in argv:
        i = argv.index("--test-answers")
        TEST["answers"] = [a for a in (argv[i + 1] if i + 1 < len(argv) else "").split(",") if a]
    cfg = L.config()
    records = L.read_all()
    st = L.stage(cfg, records["event"].objs)
    name = cfg.get("organization", {}).get("name") or "this organization"
    say("Close-out for %s" % name)
    if st == "seed":
        say("This folder is the seed itself, not an organization. Make one with: "
            "python scripts/fos_init.py ../my-organization")
        return 2
    if check_only:
        R = C.run_checks()
        C.report(R)
        todo = unsigned_decisions(cfg, records)
        say("\nWaiting for the founder's signature: %s" % (", ".join(d.get("id") for _, _, d in todo) or "none"))
        return 0
    if TEST["answers"] is None and not (sys.stdin.isatty() and sys.stdout.isatty()):
        say("This close-out asks you, the founder, to sign decisions, so it runs only in a terminal you are typing "
            "in. It will not run from an agent app's shell. Open PowerShell, Command Prompt or a terminal in this "
            "folder and run: python scripts/fos_close.py   (in Git Bash on Windows: winpty python scripts/fos_close.py). "
            "Or double-click Close-out.cmd (Windows) or Close-out.command (macOS) in this folder: it opens a terminal "
            "window of its own.")
        return 3
    L.open_signing(main.__code__)   # past the terminal guard: signatures may be written, from this main() only
    gitok = L.git_ok() and L.has_head()
    witness = L.find_witness()

    # 1. integrity
    if not integrity_step(gitok, witness):
        return 1
    void_foreign_signatures(gitok, witness)
    mark_bad_lines()
    unrecorded = session_step(gitok)
    R = C.run_checks()
    blocking = [f for f in R.fails if f.startswith(("history:", "witness history:", "BEHIND THE WITNESS",
                                                    "REWRITTEN OR SPLIT", "the birth record names"))]
    if blocking:
        say("\nThis folder's history is out of line with its witness, so a close-out cannot commit on top of it:")
        for f in blocking:
            say("  - " + f)
        say("A sync (python scripts/fos_sync.py) returns this folder to the witness's last close-out and carries "
            "this folder's own work forward: in place where it cannot collide, otherwise copied into the witness "
            "folder. Nothing is discarded.")
        if "--after-sync" in argv or not witness or witness.get("kind") != "git":
            say("Nothing was committed or signed.")
            return 1
        if ask("Run the sync now?") != "y":
            say("Nothing was committed or signed.")
            return 1
        import fos_sync
        rest = TEST["answers"]
        args = ["fos_sync.py", "--yes"] + (["--test-answers", ",".join(rest) if rest else ""] if rest is not None else [])
        code = fos_sync.main(args)
        if code != 0:
            say("The sync did not finish; nothing was committed or signed.")
            return 1
        say("\nThe close-out starts again, from the witnessed history.\n")
        again = ["fos_close.py", "--after-sync"]
        if rest is not None:
            again += ["--test-answers", ",".join(fos_sync.TEST["answers"] or [])]
        return main(again)

    # 2. signing
    warn_by = {}
    for w in R.warns:
        did = w.split(":", 1)[0].strip()
        if did.startswith("D-"):
            warn_by.setdefault(did, []).append(w.split(":", 1)[1].strip())
    check_line = "FAILED (%d)" % len(R.fails) if R.fails else ("OK, %d warning(s)" % len(R.warns) if R.warns else "OK")
    answered = signing_step(cfg, warn_by, check_line, R)
    if answered is None:
        return 1
    signed, refused, sent_back = answered["signed"], answered["refused"], answered["sent_back"]
    founded_now = answered["founded"]
    records = L.read_all()
    events = records["event"].objs
    session = L.current_session(events)

    def close_out_event(held=()):
        """The close-out on record. held: the structural files left out of the commit until the founding, with their
        SHA-256, so the next check does not take them for a member's unrecorded work."""
        rec = {"type": "close_out", "captured_by": "close_script", "session": session,
               "summary": "Close-out of %s: %s%d signed, %d not signed, %d sent back"
                          % (session, ("the founder founded the organization on %s; " % founded_now) if founded_now
                             else "", len(signed), len(refused), len(sent_back)),
               "refs": signed + refused + sent_back}
        if held:
            rec["held_until_founding"] = {p: L.file_sha256(p) for p in held}
        L.append_record("event", rec, writer="fos_close")
    if founded_now:
        write_founding(founded_now)
    elif not L.founding_state(cfg)["founded"]:
        unfound_config()

    # 3. commit and witness
    if not gitok:
        close_out_event()
        say("\nGit is not available here, so nothing can be committed.")
        if not witness:
            folder = L.default_witness_folder()
            os.makedirs(os.path.join(folder, "snapshots"), exist_ok=True)
            data = L.local_settings()
            data["witness"] = os.path.relpath(folder, L.ROOT)
            L.write_local_settings(data)
            witness = {"kind": "folder", "folder": folder, "history": None}
        if W.snapshot(L.ROOT, witness["folder"]) != 0:
            return 1
        say("The witness folder now holds a dated copy of records/. Keep the 'Waiting for close-out' list in "
            "org/STATE.md until you can commit with git.")
        return 0
    paths, left_out = choose_what_to_commit(L.config(), witness)
    unfounded = not L.founding_state()["founded"]
    held_back = held_structure() if unfounded else []
    if held_back:
        say("\nThese files hold structure prepared for the founding: %s. The organization is not founded, so they stay "
            "changed in the folder, uncommitted; a close-out commits them once you found it there (type FOUND)."
            % ", ".join(held_back))
    left_out = sorted(set(left_out) | set(held_back))
    close_out_event(held_back)
    regenerate()                    # the view's "since the last close-out" now ends with this close-out
    R = C.run_checks()
    paths = [p for _, p in changed_paths() if p not in set(left_out)]
    say("\n%d file(s) will be committed:" % len(paths))
    for p in paths[:40]:
        say("  " + p)
    if len(paths) > 40:
        say("  ... and %d more" % (len(paths) - 40))
    if left_out:
        say("%d file(s) stay changed in the folder, left out of this commit: %s" % (len(left_out), ", ".join(left_out[:8])))
    if founded_now:
        say("They are committed in two commits: first the founding, on its own (records/ only), then the rest, so that "
            "no commit holds structure before the one that founds the organization.")
    if R.fails:
        say("\nThe check still reports these failures; they will be recorded in the commit:")
        for f in R.fails:
            say("  - " + f)
    if ask("Commit these changes as yours?") != "y":
        say("Not committed. Your signatures are recorded in the folder and will be committed at the next close-out.")
        return 1
    if not ensure_author():
        return 1
    msg = ["[CLOSE] %s: %d signed, %d not signed, %d sent back" % (session, len(signed), len(refused),
                                                                   len(sent_back)), ""]
    decided = records_waiting_list(L.config(), answered)
    if decided:
        msg += ["Decided at this close-out (from the records):"] + decided + [""]
    wl = waiting_list()
    if wl:
        msg += ["Waiting-for-close-out list (org/STATE.md, as the members wrote it):"] + wl + [""]
    if set(left_out) - set(held_back):
        msg += ["Left out of this commit by the founder: %s" % ", ".join(sorted(set(left_out) - set(held_back))[:20]), ""]
    if held_back:
        msg += ["Held until the founding (structure, not founded yet): %s" % ", ".join(held_back), ""]
    msg += ["Session: %s%s" % (session, " (no session_start was recorded)" if unrecorded else ""),
            "Signed: %s" % (", ".join(signed) or "none"),
            "Not-signed: %s" % (", ".join(refused) or "none"),
            "Sent-back: %s" % (", ".join(sent_back) or "none")]
    if answered["held"]:
        msg += ["Not-asked: %s (the organization is not founded, so they wait)" % ", ".join(answered["held"])]
    if founded_now:
        msg += ["Founded: %s (in the commit before this one, where the founder typed FOUND)" % founded_now]
    msg += ["Check: %s" % ("FAILED (%d)" % len(R.fails) if R.fails else "OK, %d warning(s)" % len(R.warns)),
            "Closed-by: the founder, at a terminal (scripts/fos_close.py)"]
    if TEST["answers"] is not None:
        msg[-1] = "Closed-by: the seed's self-test (test mode; its signatures sign nothing)"
    paths = [p for _, p in changed_paths() if p not in set(left_out)]   # the view and rules were just redrawn
    if founded_now:
        # The founding first, on its own: the records only, so that no commit holds structure before the one that
        # founds the organization (scripts/fos_witness.py, founding_history). The structure follows in the next commit.
        sig = [s for s in L.read_records(L.RECORD_FILES["signature"]).objs
               if s.get("decision_id") == founded_now and s.get("founding") == W.FOUNDING_WORD]
        fmsg = ["[FOUND] %s: the founder founded the organization on %s" % (session, founded_now), "",
                "Founded: %s, signature %s: the founder typed FOUND at the close-out's prompt." % (
                    founded_now, sig[-1].get("id") if sig else "?"),
                "This commit holds the records only. The structure prepared for the founding follows in the next "
                "commit.", "", "Session: %s" % session, msg[-1]]
        h0 = commit("\n".join(fmsg) + "\n", [p for p in paths if p.startswith("records/")])
        if not h0:
            say("The founding commit failed; nothing was pushed.")
            return 1
        say("\nCommitted %s: the founding." % h0)
        paths = [p for _, p in changed_paths() if p not in set(left_out)]
    h = commit("\n".join(msg) + "\n", paths) if paths or not founded_now else "(nothing more)"
    if not h:
        say("The commit failed; nothing was pushed.")
        return 1
    say("\nCommitted %s." % h)
    if not witness:
        witness = offer_witness()
    if not witness:
        say("UNWITNESSED: the history is only in this folder.")
        return 0
    if witness["kind"] != "git":
        return W.snapshot(L.ROOT, witness["folder"])
    if push_to_witness(witness):
        say("The witness has the close-out. Done.")
        return 0
    say("The witness refused the push (see above). Your commit stays in this folder; the witness kept the "
        "history it had.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
