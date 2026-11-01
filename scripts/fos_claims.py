"""CK-1, claim by claim: the mechanical core of checking claims. Any member may run it; it changes nothing.

Usage:  python scripts/fos_claims.py [--json]

For every claim in records/claims.jsonl marked verified, it checks that:
  - the saved source named in source_file is in the folder (a PDF is read through a text copy saved
    beside it with the same name and .txt);
  - the claim's quotation occurs in that source, word for word once typographic quotes, dashes and
    spacing are made plain (a quotation with "..." must match each part, in order);
  - the source has not changed since the claim was recorded (source_sha256).
Then, for the organization's own files in org/, that every passage of four words or more in quotation
marks is something the founder said or adopted (org/GOAL.md, the founder's recorded replies and notes,
records the founder wrote, proposals adopted by a signed decision) or occurs in a saved source. A passage
that quotes the seed's own text (an interview question, say) passes when exact; when it is close to the
seed's words and not to the founder's, it is a warning, not a misquotation of the founder.

What it cannot check, and a checker reads for: whether a quotation supports the sentence it is used for,
whether a claim keeps the source's scope, and whether "finding" and "ours" are marked rightly. A check
that only runs this script is a mechanical check, not a review.

A checker role runs it first and records the result as a review (check_id CK-1), then reads for what
the script cannot check. Like every checker, this script is tested by drills: the founder plants a
misquotation (python scripts/fos_drill.py plant) and reveals afterwards whether CK-1 caught it.
Exit code 0 when nothing fails, 1 otherwise. Standard library only; no network.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402


def run():
    cfg = L.config()
    records = L.read_all()
    rows = []
    problems = {cid: (level, msg) for level, cid, msg in L.claim_checks(records)}
    for c in records["claim"].objs:
        cid = c.get("id")
        if c.get("status") != "verified":
            rows.append({"id": cid, "status": c.get("status"), "result": "not checked (%s)" % c.get("status")})
            continue
        level, msg = problems.get(cid, (None, None))
        rows.append({"id": cid, "status": "verified", "source": c.get("source_file"),
                     "result": {"FAIL": "FAIL", "WARN": "warning"}.get(level, "quotation found in source"),
                     "detail": msg})
    org = [{"file": rel, "line": n, "quote": q, "result": level, "seed_file": sfile, "seed_line": sline}
           for level, rel, n, q, sfile, sline in L.org_quote_checks(cfg, records)]
    return rows, org


def main(argv):
    rows, org = run()
    failed = any(r["result"] == "FAIL" for r in rows) or any(o["result"] == "FAIL" for o in org)
    if "--json" in argv:
        print(json.dumps({"ok": not failed, "claims": rows, "org_quotes_unmatched": org}, ensure_ascii=False, indent=1))
        return 1 if failed else 0
    print("CK-1: quotations against their sources")
    if not rows:
        print("  no claims recorded")
    for r in rows:
        print("  %-8s %-9s %s%s" % (r["id"], r["status"], r["result"],
                                   (" - " + r["detail"]) if r.get("detail") else ""))
    print("CK-1: passages quoted in org/")
    if not org:
        print("  every quoted passage matches the founder's words, a saved source or the seed's own text")
    for o in org:
        if o["result"] == "WARN":
            print("  WARN %s line %d: \"%s\" is close to the seed's own words in %s, not to the founder's: quote the "
                  "seed exactly, or drop the quotation marks" % (o["file"], o["line"], o["quote"][:120], o["seed_file"]))
            continue
        print("  FAIL %s line %d: \"%s\" matches nothing the founder said or adopted, no saved source and not the "
              "seed's own text" % (o["file"], o["line"], o["quote"][:120]))
    print("Result: %s" % ("FAILED" if failed else "OK"))
    print("Not checked by any script: whether each quotation supports its sentence, keeps the source's scope, and is "
          "marked as the source's finding or our inference. A checker reads for those.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
