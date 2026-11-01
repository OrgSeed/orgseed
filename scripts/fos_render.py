"""Draw view/org_view.html from the organization's files and view/VIEWS.json.

Usage:  python scripts/fos_render.py

A fixed renderer. It writes one self-contained HTML file with no scripts and a
content-security policy that forbids loading anything, so opening the view reaches nothing
outside the file. The output depends only on the organization's files (no clock), so the same
files always draw the same view.

Two layers:
  - The frame, drawn whatever view/VIEWS.json says: whose organization this is and what seed it
    was born from (with its birth hash), whether it is witnessed, what waits for the founder
    (open proposals, decisions not yet signed), anything not part of the organization (in red),
    the members with the model each runs on, and what was turned back.
  - The panels listed in view/VIEWS.json, in its order, drawn from a fixed set of sources.
    Changing that file is a structural change: a proposal and a decision the founder signs.
Members never edit this script or the HTML it writes; they change the organization, then
re-run it (the close-out does).
Standard library only; no network.
"""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402

def E(value):
    """Escape for HTML; a missing or non-text value (a record that does not fit its schema) is drawn as text."""
    return html.escape("" if value is None else str(value))


DEFAULT_PANELS = [{"id": x, "title": t, "source": x} for x, t in (
    ("goal", "Goal and movement"), ("queue", "Waiting for a decision"), ("decisions", "Recent decisions"),
    ("modules", "Structure: modules"), ("rules", "Rules in force"), ("memory", "Memory"),
    ("since", "Since the last close-out"))]


def table(headers, rows, empty="None yet."):
    if not rows:
        return "<p class='muted'>%s</p>" % E(empty)
    h = "".join("<th>%s</th>" % E(x) for x in headers)
    body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in rows)
    return "<div class='scroll'><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>" % (h, body)


def badge(text, kind):
    return "<span class='badge %s'>%s</span>" % (kind, E(text))


def panel(title, inner, pid, extra=""):
    return "<section id='%s'%s><h2>%s</h2>%s</section>" % (E(pid), extra, E(title), inner)


def origin(slot, kind):
    if kind == "human":
        return "person"
    slot = slot or {}
    return "%s by %s, in %s, served by %s (id from: %s)" % (
        slot.get("model_id") or "unknown model", slot.get("producer") or "unknown producer",
        slot.get("agent_app") or "unknown app", slot.get("host") or "unknown host", slot.get("model_id_source") or "unknown")


def witness_state(st):
    if st == "seed":
        return ("the seed itself: no witness", "off")
    w = L.find_witness()
    if not w:
        return ("UNWITNESSED: the history could be rewritten without anyone noticing", "bad")
    if w["kind"] == "git":
        h = w.get("history") or ""
        if not os.path.isdir(h):
            return ("WITNESS MISSING: %s" % os.path.basename(w["folder"]), "bad")
        return ("witnessed: %s" % os.path.basename(w["folder"]), "ok")
    return ("witnessed by dated copies: %s" % os.path.basename(w["folder"]), "warn")


class Model:
    """Everything the view needs, computed once from the files."""

    def __init__(self, cfg, records):
        self.cfg, self.rec = cfg, records
        self.events = records["event"].objs
        self.info = L.stage_info(cfg, self.events)
        self.stage = self.info["stage"]
        self.ad = L.adoption(cfg, records)
        self.ok = self.ad["signed"]
        self.tools = L.tools_registry()
        try:
            self.views = L.load_json("view/VIEWS.json")
        except (OSError, ValueError):
            self.views = None
        self.pstatus, self.reopened = L.proposal_status(records, self.ad)
        self.open = [p for p in records["proposal"].objs if self.pstatus.get(p.get("id")) in ("open", "awaiting")]
        self.unanswered = [d for _, _, d in L.unanswered_decisions(records)]
        self.items = list(L.structural_items(cfg, self.tools, self.views))
        self.ungoverned = [(k, lbl, a) for k, lbl, a in self.items
                           if not L.governed(a, self.ok, k, lbl) and a not in self.ad["awaiting"]]
        self.provisional = [(k, lbl, a) for k, lbl, a in self.items
                            if not L.governed(a, self.ok, k, lbl) and a in self.ad["awaiting"]]
        last_close = max([i for i, e in enumerate(self.events) if e.get("type") == "close_out"] or [-1])
        self.since = self.events[last_close + 1:]

    def status_of(self, adopted_by, kind=None, label=None):
        if L.governed(adopted_by, self.ok, kind, label):
            return badge("part of the organization", "ok")
        if adopted_by in self.ad["awaiting"]:
            return badge("awaiting signature", "warn")
        if adopted_by in self.ad["refused"]:
            return badge("signature refused", "bad")
        if adopted_by in self.ad.get("sent_back", set()):
            return badge("sent back", "bad")
        return badge("proposal only", "bad")


# ---------------------------------------------------------------- the frame (not removable)

def frame(m):
    org = m.cfg.get("organization", {})
    born = m.info.get("birth")
    seed = L.seed_info()
    if born:
        s = born.get("seed") or {}
        birth = ("Born from %s %s &middot; birth hash (seed tree) <code>%s</code> &middot; anyone can check it: "
                 "<code>git rev-parse &lt;release&gt;^{tree}</code> in the seed's repository"
                 % (E(s.get("name", "?")), E(s.get("version", "?")), E((s.get("tree") or "?")[:12])))
    else:
        birth = "This is the seed itself (%s %s). Organizations are born from it with scripts/fos_init.py." % (
            E(seed.get("name", "")), E(seed.get("version", "")))
    wtext, wkind = witness_state(m.stage)
    founded = ("founded %s" % (org.get("founded_on") or "")).strip() if m.stage == "founded" else "not yet founded"
    strip = [
        "<li>%s</li>" % badge(wtext, wkind),
    ]
    study, _ = L.study_config()
    if study:
        strip.append("<li>%s</li>" % badge("RESEARCH CONFIGURATION: %s switched off (org/STUDY.json)"
                                           % ", ".join(study.get("switch_off") or []), "warn"))
    if m.info.get("damaged"):
        strip.append("<li>%s</li>" % badge("BIRTH RECORD LOST from records/events.jsonl (the history holds it)", "bad"))
    strip += [
        "<li><b>%d</b> open proposal(s)</li>" % len(m.open),
        "<li><b>%d</b> decision(s) not yet signed by the founder</li>" % len(m.unanswered),
        "<li><b>%d</b> provisional item(s), awaiting signature</li>" % len(m.provisional),
        "<li>%s</li>" % (badge("%d item(s) not part of the organization" % len(m.ungoverned), "bad")
                         if m.ungoverned else badge("nothing ungoverned", "ok")),
        "<li><b>%d</b> event(s) since the last close-out</li>" % len(m.since),
    ]
    head = ("<header><h1>%s</h1><p class='muted'>%s. %s</p><ul class='strip'>%s</ul></header>"
            % (E(org.get("name") or "An organization not yet founded"), E(founded), birth, "".join(strip)))
    out = [head]
    if m.ungoverned:
        out.append(panel("Not part of the organization",
                         "<p>These appear in the organization's files without a decision by someone holding the right, "
                         "or with one the founder refused to sign. They are proposals only (CORE-2).</p>"
                         + table(["Kind", "Item", "adopted_by"], [[E(k), E(lbl), E(str(a))] for k, lbl, a in m.ungoverned]),
                         "ungoverned", " class='alarm'"))
    members = []
    for r in m.cfg.get("roles", []):
        for inst in r.get("instances", []) or [{}]:
            members.append([E(r.get("title", r.get("id"))), E(inst.get("id", "vacant")),
                            E(origin(inst.get("slot"), r.get("kind"))),
                            m.status_of(inst.get("adopted_by"), "role instance", "%s/%s" % (r.get("id"), inst.get("id")))])
    out.append(panel("Members", table(["Role", "Instance", "Runs on", "Status"], members), "members"))
    dl = m.rec["decline"].objs[-10:][::-1]
    rows = [[E(x.get("id")), E(x.get("rule_id")), E(x.get("what")), E(x.get("why_declined")), E(x.get("outcome")),
             badge("drill", "warn") if x.get("drill") else ""] for x in dl]
    out.append("<details open class='declines'><summary>Turned back by a rule, a check or the founder (%d)</summary>%s"
               "</details>" % (len(m.rec["decline"].objs), table(["ID", "Rule", "What", "Why", "Outcome", ""], rows,
                                                                  "Nothing turned back yet.")))
    return out


# ---------------------------------------------------------------- panels (chosen in view/VIEWS.json)

def src_goal(m, p):
    goal = (L.parse_entries(L.read_text("org/GOAL.md", "")) or [{}])[0]
    words = goal.get("words") or ""
    if not words or words.startswith("("):   # the template's placeholder: nothing set yet
        goal, words = {}, "Not yet set: the first session writes the founder's goal here, in their own words."
    g = "<p class='goal'>%s</p>" % E(words)
    if goal.get("reason"):
        g += "<p><b>Why it matters:</b> %s</p>" % E(goal["reason"])
    ngs = [e for e in L.parse_entries(L.read_text("org/CHARTER.md", "")) if e["id"].startswith("NG-")]
    if ngs:
        g += table(["Near-term goal", "Kind", "Done when", "Status"],
                   [[E(n.get("goal", n.get("title", ""))), E(n.get("kind", "")), E(n.get("done_when", "")),
                     m.status_of(n.get("adopted_by"))] for n in ngs])
    founders = L.founder_instances(m.cfg)
    counts = [
        ("Decisions by the founder", sum(1 for d in m.ad["decisions"] if d.get("decided_by") in founders)),
        ("Signed by the founder", len(m.ad["signed"])),
        ("Declined proposals", sum(1 for d in m.ad["decisions"] if d.get("verdict") == "declined")),
        ("Proposals by the founder", sum(1 for x in m.rec["proposal"].objs if x.get("proposed_by") in founders)),
        ("Turned back", sum(1 for x in m.rec["decline"].objs if not x.get("drill"))),
        ("Corrections", len(m.rec["correction"].objs)),
        ("Work finished", sum(1 for e in m.events if e.get("type") == "work_done")),
        ("Drills planted", sum(1 for d in m.rec["drill"].objs if d.get("action") == "planted")),
        ("Sessions", sum(1 for e in m.events if e.get("type") == "session_start")),
    ]
    g += "<h3>Counts from the records</h3><p class='muted'>Behaviour in the records only; nothing here is estimated.</p>"
    g += "<ul class='counts'>%s</ul>" % "".join("<li><b>%d</b> %s</li>" % (v, E(k)) for k, v in counts)
    return g


def src_queue(m, p):
    def standing(pid):
        if pid in m.reopened:
            return badge("open again: " + m.reopened[pid], "bad")
        return badge("awaiting signature", "warn") if m.pstatus.get(pid) == "awaiting" else badge("open", "off")
    rows = [[E(x.get("id")), standing(x.get("id")), E(x.get("kind")), E(x.get("change")), E(x.get("why")),
             E(x.get("proposed_by"))] for x in m.open]
    return table(["ID", "Standing", "Kind", "Change", "Why", "Proposed by"], rows, "Nothing waiting.")


def src_decisions(m, p):
    sig = m.ad["sig_status"]
    rows = []
    for d in m.ad["decisions"][-int(p.get("limit", 12)):][::-1]:
        s = sig.get(d.get("id"))
        st = {"signed": badge("signed", "ok"), "refused": badge("not signed", "bad"),
              "sent_back": badge("sent back", "bad")}.get(s, badge("awaiting signature", "warn"))
        rows.append([E(d.get("id")), E(d.get("verdict")), E(d.get("question")), "<q>%s</q>" % E(d.get("words", "")),
                     E(d.get("framed_by")), st])
    return table(["ID", "Verdict", "Question as asked", "The founder's words", "Framed by", "Signature"], rows)


def src_signatures(m, p):
    rows = [[E(s.get("id")), E(s.get("decision_id")), E(s.get("answer")), E(s.get("mode")), E(s.get("session"))]
            for s in m.rec["signature"].objs[-int(p.get("limit", 20)):][::-1]]
    return table(["ID", "Decision", "Answer", "Mode", "Session"], rows)


def src_modules(m, p):
    rows = []
    for mod in m.cfg.get("modules", []):
        st = m.status_of(mod.get("adopted_by"), "module", mod.get("id")) if mod.get("state") == "on" else badge("off", "off")
        rows.append([E(mod.get("id")), st, E(L.module_title_line(mod.get("id"))), E(str(mod.get("adopted_by") or ""))])
    return "<p class='muted'>Any combination may be on. Presets are shortcuts, not levels.</p>" + \
        table(["Module", "State", "For", "Adopted by"], rows)


def src_members(m, p):
    return src_roles(m, p)


def src_roles(m, p):
    roll = {x["role"]: x for x in L.role_rollcall(m.cfg, m.events)}
    names = {"ok": ("ok", "ok"), "due": ("due", "warn"), "stale": ("stale", "bad"), "never": ("never run", "bad"),
             "exempt": ("on call", "off"), "no_trigger": ("no trigger", "bad")}
    rows = []
    for r in m.cfg.get("roles", []):
        rc = roll.get(r.get("id"), {})
        trig = r.get("trigger") or {}
        n = names.get(rc.get("status"), ("?", "off"))
        rows.append([E(r.get("title", r.get("id"))), E("%s: %s" % (trig.get("on", "none"), trig.get("when", ""))),
                     E(rc.get("last_session") or "never"), badge(n[0], n[1]), m.status_of(r.get("adopted_by"), "role", r.get("id"))])
    inner = table(["Role", "Trigger", "Last ran", "Roll-call", "Status"], rows)
    retired = m.cfg.get("retired_roles", [])
    if retired:
        inner += "<h3>Retired roles</h3>" + table(["Role", "End", "Into", "Decision", "Reason"],
                                                  [[E(x.get("id")), E(x.get("end", "retired")), E(x.get("absorbed_into", "")),
                                                    E(str(x.get("retired_by"))), E(x.get("reason", ""))] for x in retired])
    return inner


def src_rules(m, p):
    reasons = m.cfg.get("settings", {}).get("rule_reasons", "shown") != "hidden"
    core = L.core_rule_ids()
    rows = []
    for mod in L.modules_in_force(m.cfg, m.ok):
        for e in L.module_rules(mod):
            rows.append([E(e["id"]), E(e.get("title", "")), E(e.get("why", "")) if reasons else "<span class='muted'>hidden</span>"])
    lead = ("<p class='muted'>The core rules %s to %s (AGENTS.md) are always in force.</p>" % (core[0], core[-1])) if core else ""
    return lead + table(["Rule", "Title", "Why it exists"], rows, "No module rules in force.")


def src_declines(m, p):
    dl = m.rec["decline"].objs[-int(p.get("limit", 20)):][::-1]
    return table(["ID", "Rule", "What", "Why", "Outcome", ""],
                 [[E(x.get("id")), E(x.get("rule_id")), E(x.get("what")), E(x.get("why_declined")), E(x.get("outcome")),
                   badge("drill", "warn") if x.get("drill") else ""] for x in dl])


def src_claims(m, p):
    rows = [[E(c.get("id")), E(c.get("claim")), E(c.get("cites") or c.get("source_file") or ""), E(c.get("status"))]
            for c in m.rec["claim"].objs[-int(p.get("limit", 12)):][::-1]]
    return table(["ID", "Claim", "Source", "Status"], rows)


def src_tools(m, p):
    rows = [[E(t.get("id")), E(str(t.get("tier", ""))), E(t.get("status", "")), E(t.get("purpose", "")),
             m.status_of(t.get("adopted_by"), "tool", t.get("id"))] for t in m.tools.get("tools", [])]
    return table(["Tool", "Tier", "Stage", "Purpose", "Status"], rows)


def src_needs(m, p):
    latest = {}
    for n in m.rec["need"].objs:
        latest[n.get("id")] = n
    return table(["ID", "Need", "State"], [[E(n.get("id")), E(n.get("task")), E(n.get("state"))] for n in latest.values()])


def src_drills(m, p):
    rows = []
    for d in m.rec["drill"].objs:
        if d.get("action") == "planted":
            rows.append([E(d.get("id")), "planted" + (" (announced)" if d.get("announced") else ""), E(d.get("session")),
                         "<code>%s</code>" % E((d.get("seal") or "")[:12]), ""])
        else:
            rows.append([E(d.get("id")), E(d.get("action")), E(d.get("session")), E(d.get("description", "")),
                         E((d.get("outcome") or "") + (" by " + d["caught_by"] if d.get("caught_by") else ""))])
    return "<p class='muted'>Planted by the founder. Until revealed, only a fingerprint of the description is recorded.</p>" + \
        table(["Drill", "Step", "Session", "Seal or description", "Outcome"], rows)


def src_recall(m, p):
    if not m.rec["recall"].objs:
        return "<p class='muted'>No recall checks yet.</p>"
    r = m.rec["recall"].objs[-1]
    marks = [i.get("mark") for i in r.get("items", [])]
    return "<p>Last recall check (%s, %s): %d correct, %d wrong, %d missing.</p>" % (
        E(r.get("session", "")), E(r.get("instance", "")), marks.count("correct"), marks.count("wrong"), marks.count("missing"))


def src_memory(m, p):
    inner = "<h3>Current state</h3><pre>%s</pre>" % E(L.read_text("org/STATE.md", ""))
    inner += "<h3>Letter to the next session</h3><pre>%s</pre>" % E(L.read_text("org/LETTER_TO_NEXT_SESSION.md", ""))
    return inner + src_recall(m, p)


def src_since(m, p):
    rows = [[E(str(e.get("seq"))), E(e.get("session", "")), E(e.get("type", "")),
             E((e.get("identity") or {}).get("instance", "")), E(e.get("captured_by", "")), E(e.get("summary", ""))]
            for e in m.since[-int(p.get("limit", 40)):]]
    return table(["#", "Session", "Event", "Who", "Written by", "Summary"], rows, "Nothing since the last close-out.")


SOURCES = {name[4:]: fn for name, fn in globals().items() if name.startswith("src_")}


def build(cfg=None, records=None):
    cfg = cfg or L.config()
    records = records or L.read_all()
    m = Model(cfg, records)
    out = frame(m)
    panels = (m.views or {}).get("panels") if isinstance(m.views, dict) else None
    if not isinstance(panels, list):
        out.append("<p class='muted'>view/VIEWS.json is missing or unreadable; the starter panels are drawn.</p>")
        panels = DEFAULT_PANELS
    elif not L.governed((m.views or {}).get("adopted_by"), m.ok, "view", "view/VIEWS.json"):
        out.append(panel("This layout is a proposal", "<p>view/VIEWS.json was changed without a decision the founder "
                         "signed. The panels below follow it, as a proposal.</p>", "view-proposal", " class='alarm'"))
    for p in panels:
        if not isinstance(p, dict):
            continue
        fn = SOURCES.get(p.get("source"))
        inner = fn(m, p) if fn else "<p class='muted'>Unknown source %r: not drawn.</p>" % E(str(p.get("source")))
        out.append(panel(p.get("title") or p.get("source") or "Panel", inner, "p-" + str(p.get("id") or p.get("source"))))
    footer = ("<footer class='muted'>Drawn by scripts/fos_render.py from the organization's files (config %s; %d events). "
              "The view changes only when the organization changes. No scripts; nothing is loaded from outside this "
              "file.</footer>" % (E(L.config_hash()), len(m.events)))
    return TEMPLATE.format(title=E(cfg.get("organization", {}).get("name") or "Organization view"),
                           body="\n".join(out) + footer)


def main():
    doc = build()
    os.makedirs(L.path("view"), exist_ok=True)
    with open(L.path("view/org_view.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    print("wrote view/org_view.html")
    return 0


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>{title}</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#dcd9d0; --card:#ffffff;
  --ok:#1f6f43; --okbg:#e3f2e8; --warn:#7a5a00; --warnbg:#fbf0cc; --bad:#9b1c1c; --badbg:#fde4e1; --offbg:#eceae4; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#161614; --fg:#ecebe6; --muted:#a3a19a; --line:#3a3934; --card:#1f1f1c;
    --ok:#8fd3a8; --okbg:#1e3a29; --warn:#e8c96a; --warnbg:#3b3117; --bad:#f2a49b; --badbg:#3f1f1c; --offbg:#2b2a26; }}
}}
* {{ box-sizing: border-box; }}
body {{ margin:0 auto; max-width:1100px; padding:16px; background:var(--bg); color:var(--fg);
  font:16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
header h1 {{ margin:8px 0 4px; font-size:1.6rem; }}
.muted {{ color:var(--muted); }}
section, details.declines {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 16px; margin:14px 0; }}
section.alarm {{ border-color:var(--bad); }}
summary {{ font-weight:600; cursor:pointer; }}
h2 {{ font-size:1.15rem; margin:4px 0 10px; }}
h3 {{ font-size:1rem; margin:14px 0 6px; }}
.goal {{ font-size:1.15rem; }}
.scroll {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:.92rem; }}
th, td {{ text-align:left; vertical-align:top; padding:6px 8px; border-bottom:1px solid var(--line); }}
pre {{ white-space:pre-wrap; word-wrap:break-word; background:var(--bg); border:1px solid var(--line); border-radius:6px; padding:8px; font-size:.88rem; }}
code {{ font-size:.88rem; }}
.badge {{ display:inline-block; padding:1px 8px; border-radius:999px; font-size:.8rem; }}
.ok {{ color:var(--ok); background:var(--okbg); }} .warn {{ color:var(--warn); background:var(--warnbg); }}
.bad {{ color:var(--bad); background:var(--badbg); }} .off {{ color:var(--muted); background:var(--offbg); }}
ul.strip, ul.counts {{ list-style:none; padding:0; display:grid; grid-template-columns:repeat(auto-fill,minmax(210px,1fr)); gap:6px; }}
ul.strip li, ul.counts li {{ border:1px solid var(--line); border-radius:6px; padding:6px 8px; background:var(--card); }}
footer {{ margin:20px 0; font-size:.85rem; }}
q {{ quotes: "\\201C" "\\201D"; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main())
