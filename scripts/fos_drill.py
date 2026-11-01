"""Drills: the founder plants a known fault to see whether the organization's checks catch it.

Usage (the founder, in an ordinary terminal):
  python scripts/fos_drill.py plant [--announced] [--hint "where members should look"]
  python scripts/fos_drill.py reveal DR-0001
  python scripts/fos_drill.py list

How a drill works:
  1. The founder plants a fault in the work, by hand: a wrong number in a table, a quotation that
     differs from its source, a claim with no source. Members are not told what or where (with
     --announced they are told only that a drill is under way, and the hint, if any).
  2. plant asks the founder to describe the fault. The description is kept outside the folder, in
     the witness folder's drills/; the records hold only its fingerprint (a SHA-256 seal), so no
     member can read it, and nobody can change it afterwards without the seal showing it.
  3. Once the work has been checked, reveal adds the description and whether the fault was caught,
     and by whom. Anyone can recompute the seal from the revealed text.
A drill is always recorded as a drill. A check that finds nothing looks the same as a check that
has stopped working; only a planted fault tells them apart. The drill role in org/config.json
reminds the founder at session start when no drill has run for three sessions.

A member never plants a drill: a drill its checker planted tests nothing. Like the close-out, this
script runs only in a terminal (--test-answers "a|b|c" is for the seed's self-test).
Standard library only; no network.
"""
import hashlib
import json
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402

TEST = {"queue": None}


def ask(prompt, yes_no=True):
    if TEST["queue"] is not None:
        a = TEST["queue"].pop(0) if TEST["queue"] else ("n" if yes_no else "")
        print("%s %s   [test]" % (prompt, a))
        return a.strip().lower() if yes_no else a.strip()
    while True:
        try:
            a = input(prompt + " ").strip()
        except EOFError:
            return ""
        if not yes_no:
            return a
        if a.lower() in ("y", "n"):
            return a.lower()
        print("  Please answer y or n.")


def drills_folder():
    w = L.find_witness()
    folder = w["folder"] if w else L.default_witness_folder()
    if not os.path.isdir(folder):
        return None
    d = os.path.join(folder, "drills")
    os.makedirs(d, exist_ok=True)
    return d


def plant(argv):
    store = drills_folder()
    if not store:
        print("A drill's description is kept outside this folder, in the witness folder, and there is none yet. "
              "The witness is created by python scripts/fos_init.py, or by the first close-out.")
        return 1
    print("Describe the fault you planted: what you changed, and where. Members will see only a fingerprint "
          "of this text until you reveal it.")
    desc = ask("Description:", yes_no=False)
    if not desc:
        print("No description given; nothing was recorded.")
        return 1
    salt = secrets.token_hex(16)
    seal = hashlib.sha256((salt + desc).encode("utf-8")).hexdigest()
    rec = {"action": "planted", "seal": seal, "announced": "--announced" in argv, "captured_by": "drill_script"}
    if "--hint" in argv:
        rec["hint"] = argv[argv.index("--hint") + 1]
    line, _ = L.append_record("drill", rec, writer="fos_drill")
    did = json.loads(line)["id"]
    with open(os.path.join(store, did + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"id": did, "description": desc, "salt": salt, "seal": seal}, f, indent=1)
    L.append_record("event", {"type": "role_ran", "captured_by": "drill_script", "refs": ["drill", did],
                              "summary": "The founder planted drill %s%s" % (did, " (announced)" if rec["announced"] else ""),
                              "drill": True}, writer="fos_drill")
    print("Drill %s planted. When the work has been checked: python scripts/fos_drill.py reveal %s" % (did, did))
    return 0


def reveal(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    did = argv[2]
    planted = [d for d in L.read_records(L.RECORD_FILES["drill"]).objs if d.get("id") == did]
    if not planted or planted[0].get("action") != "planted":
        print("No planted drill %s in records/drills.jsonl" % did)
        return 1
    if any(d.get("action") in ("revealed", "cancelled") for d in planted[1:]):
        print("Drill %s was already revealed" % did)
        return 1
    store = drills_folder()
    p = os.path.join(store or "", did + ".json")
    if not store or not os.path.exists(p):
        print("The description of %s is not in the witness folder (%s); it cannot be revealed." % (did, p))
        return 1
    with open(p, encoding="utf-8") as f:
        kept = json.load(f)
    print("Drill %s: %s" % (did, kept["description"]))
    caught = ask("Was the planted fault caught?") == "y"
    by = ask("By whom (a role instance, or a check such as CK-1)?", yes_no=False) if caught else ""
    rec = {"id": did, "action": "revealed", "description": kept["description"], "salt": kept["salt"],
           "outcome": "caught" if caught else "missed", "captured_by": "drill_script", "drill": True}
    if caught and by:
        rec["caught_by"] = by     # a miss has no catcher: the field is left out, never written empty
    L.append_record("drill", rec, writer="fos_drill")
    if caught:
        print("Drill %s revealed: caught%s." % (did, " by " + by if by else ""))
    else:
        print("Drill %s revealed: MISSED. Nothing in the organization caught it; that is now on record. Consider a "
              "check that would have caught it (a proposal), and plant another drill later." % did)
    return 0


def list_drills():
    rows = L.read_records(L.RECORD_FILES["drill"]).objs
    if not rows:
        print("No drills yet.")
    for d in rows:
        print("  %s %-9s %s" % (d.get("id"), d.get("action"), d.get("outcome") or ("seal " + d.get("seal", "")[:12])))
    return 0


def main(argv):
    if "--test-answers" in argv:   # answers separated by |, for the seed's self-test only
        TEST["queue"] = argv[argv.index("--test-answers") + 1].split("|")
    testing = TEST["queue"] is not None
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "list":
        return list_drills()
    if cmd in ("plant", "reveal") and not testing and not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("Drills are planted and revealed by the founder, in a terminal; this will not run from an agent app's "
              "shell.")
        return 3
    if cmd == "plant":
        return plant(argv)
    if cmd == "reveal":
        return reveal(argv)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
