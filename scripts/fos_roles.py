"""Role roll-call: each role's trigger, when it last ran, and whether it is due or stale.

Usage:  python scripts/fos_roles.py

A role ran when a record is written by one of its instances (identity.instance), or when a
role_ran event names it in refs. A role is stale when it has not run within its expected
interval (expected_every_sessions, or settings.default_expected_every_sessions). The founder
decides what happens to a stale role: revive it (re-wire its trigger), merge it into another
role, retire it, or keep it as it is. The drill role is held by the founder: when it is due,
the founder plants a drill (python scripts/fos_drill.py plant).
Reads only. Standard library only; no network.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402


def main():
    cfg = L.config()
    events = L.read_records(L.RECORD_FILES["event"]).objs
    rows = L.role_rollcall(cfg, events)
    print("Role roll-call")
    for x in rows:
        trig = x["trigger"] or {}
        print("  %-14s %-10s trigger: %s (%s); last ran: %s; expected every %s sessions"
              % (x["role"], x["status"].upper(), trig.get("on", "none"), trig.get("when", ""),
                 x["last_session"] or "never", x["expected"] if x["expected"] is not None else "-"))
    flagged = [x for x in rows if x["status"] in ("stale", "never", "no_trigger")]
    if flagged:
        print("Ask the founder, for each role above marked STALE, NEVER or NO_TRIGGER:")
        print("  revive (re-wire its trigger), merge into another role, retire, or keep as is.")
    pins = {}
    for p in L.read_records(L.RECORD_FILES["pin"]).objs:
        pins[p.get("id")] = p
    open_pins = [p for p in pins.values() if p.get("state") == "open"]
    if open_pins:
        print("Pins the founder asked to come back to (MEM-13); raise any whose moment has come:")
        for p in open_pins:
            print("  %s \"%s\" (when: %s)" % (p.get("id"), p.get("words"), p.get("trigger")))
    for r in cfg.get("retired_roles", []):
        print("  retired: %s (%s%s; decision %s)" % (r.get("id"), r.get("end", "retired"),
              " into " + r["absorbed_into"] if r.get("absorbed_into") else "", r.get("retired_by")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
