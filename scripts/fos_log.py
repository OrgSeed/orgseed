"""Append records to the organization's records. The only way a record is written.

Usage (pick one form):
  python scripts/fos_log.py <kind> --json-file records.json   records from a file
  python scripts/fos_log.py <kind> --json -                   records from standard input
  python scripts/fos_log.py <kind> key=value [key=value ...]  one short record; values that parse as
                                                              JSON are read as JSON
  python scripts/fos_log.py batch --json-file records.json    records of several kinds in one call:
                                                              each record names its kind in "record"
Add --check to validate without writing.

The file (or standard input) holds one JSON object, a JSON list of objects, or one JSON object per
line. Several records in one call are checked together, in order, each seeing the ones before it;
if any one does not fit, nothing is written. One call can therefore carry a session's proposals,
or a decision and the event that goes with it.

kind: event, proposal, decision, decline, claim, correction, commitment, recall, dissent,
      review, need   (signatures and drills are written only by fos_close and fos_drill)

What it does for you:
  - seq, id, ts (UTC) and session are filled in; seq is one more than the highest in the file;
  - identity is filled from your model slot in org/config.json (give "instance" if the
    organization has more than one AI instance; give "identity" to state it yourself);
  - each record is checked against its schema and refused, with the reasons, if it does not fit;
  - each is appended as one line, under a lock, so members working side by side never collide.
    A records file is never rewritten, and a missing one is never re-created: a missing file was
    deleted, and that must stay visible.

Never open a records file with an agent app's file tools, not even to add one line (AGENTS.md,
CORE-4). If you cannot run Python, write the records, one JSON object per line, into a file in
work/, and ask the founder to add them: python scripts/fos_log.py batch --json-file work/<file>

Writing records through a file avoids shell quoting problems:
  1. write the records as JSON into a file outside records/ (for example work/tmp_records.json);
  2. python scripts/fos_log.py decision --json-file work/tmp_records.json
  3. delete the file.

Example record for a decision (the reply is the founder's own words, exactly):
  {"question": "Do you adopt P-0004 (switch on the claim-discipline module)?",
   "proposal_ids": ["P-0004"], "framed_by": "member-1", "decided_by": "founder",
   "decider_kind": "human", "right": "founder", "verdict": "adopted",
   "words": "Yes, I adopt P-0004."}

Exit code 0 when written (or valid with --check), 1 when refused, 2 for usage errors.
Standard library only; no network.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402


def parse_value(v):
    try:
        return json.loads(v)
    except ValueError:
        return v


def parse_records(text):
    """One object, a list of objects, or one object per line. Returns a list; raises ValueError."""
    text = text.strip()
    if not text:
        raise ValueError("no record was given")
    try:
        data = json.loads(text)
    except ValueError:
        recs = []
        for n, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                recs.append(json.loads(line))
            except ValueError as e:
                raise ValueError("line %d is not one JSON object (%s)" % (n, getattr(e, "msg", e)))
        return recs
    return data if isinstance(data, list) else [data]


def main(argv):
    args = argv[1:]
    kinds = list(L.RECORD_FILES) + ["batch"]
    if not args or args[0] in ("-h", "--help") or args[0] not in kinds:
        print(__doc__)
        return 2
    kind, rest = args[0], args[1:]
    check_only = "--check" in rest
    rest = [a for a in rest if a != "--check"]
    try:
        if rest[:1] == ["--json-file"] and len(rest) == 2:
            with open(rest[1], encoding="utf-8-sig") as f:
                recs = parse_records(f.read())
        elif rest[:1] == ["--json"] and len(rest) == 2 and rest[1] == "-":
            stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8-sig")
            recs = parse_records(stdin.read())
        elif rest and all("=" in a for a in rest) and kind != "batch":
            rec = {}
            for a in rest:
                k, v = a.split("=", 1)
                rec[k] = parse_value(v)
            recs = [rec]
        else:
            print("Give the records as --json-file FILE, --json - (standard input), or key=value pairs.")
            return 2
    except (OSError, ValueError) as e:
        print("not written: the records could not be read as JSON (%s)" % e)
        return 1
    items = []
    for i, rec in enumerate(recs, 1):
        if not isinstance(rec, dict):
            print("not written: record %d is not a JSON object" % i)
            return 1
        if kind == "batch":
            rec = dict(rec)
            k = rec.pop("record", None)
            if k not in L.RECORD_FILES:
                print("not written: record %d needs \"record\": one of %s" % (i, ", ".join(L.RECORD_FILES)))
                return 1
            items.append((k, rec))
        else:
            items.append((kind, rec))
    try:
        lines, warnings = L.append_records(items, writer="member", dry_run=check_only)
    except L.RecordError as e:
        print(str(e))
        return 1
    for w in warnings:
        print("note: " + w)
    for line in lines:
        print(("valid (not written): " if check_only else "") + line)
    if len(lines) > 1:
        print("%s %d records." % ("Checked" if check_only else "Wrote", len(lines)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
