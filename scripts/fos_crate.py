"""Export an organization's witnessed history as an RO-Crate, with a W3C PROV file inside.

Usage (anyone, in a terminal; the organization's folder is only read):
  python scripts/fos_crate.py <output-folder> [--rev <commit or tag>] [--with-pushlog]

It writes a new folder, outside the organization, holding:
  ro-crate-metadata.json   an RO-Crate 1.3 that declares the Process Run Crate 0.6 profile: every
                           file, the people and software involved, and what happened (sessions,
                           close-outs, decisions, signatures, what was turned back) as schema.org
                           actions. Only terms from the RO-Crate 1.3 context are used.
  prov/run.prov.jsonld     the same history in W3C PROV-O: each record line as an entity, with who
                           wrote it (role instance, and the model, producer, agent app and host on
                           record), in which session, and which signature endorses which decision.
  the organization's files, exactly as committed at that revision, each listed with its SHA-256.
  witness_pushlog.jsonl    with --with-pushlog only: the witness's log of push attempts.

It reads a fresh clone of the witness at the revision (default: the witness's latest close-out), never
the working folder. So nothing uncommitted, no transcript, no sealed drill description, and nothing else
from the witness folder can enter it. No clock is read: the same revision always gives the same bytes.

An AI member enters the crate as an instrument (a SoftwareApplication) of the actions it took part in,
because schema.org's agent is a person or an organization; the PROV file keeps it as a software agent
acting in a role. A crate is an account of the history, not evidence that it is untouched: that evidence is
the witness, which refused every rewrite. Checksums alone cannot show that nobody altered a crate.
Standard library only; no network.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402
import fos_witness as W  # noqa: E402

CRATE_CONTEXT = "https://w3id.org/ro/crate/1.3/context"
CRATE_SPEC = "https://w3id.org/ro/crate/1.3"
PROFILE = "https://w3id.org/ro/wfrun/process/0.6"
PROV_CONTEXT = {"prov": "http://www.w3.org/ns/prov#", "xsd": "http://www.w3.org/2001/XMLSchema#"}
MEDIA = {".md": "text/markdown", ".json": "application/json", ".html": "text/html", ".txt": "text/plain",
         ".pdf": "application/pdf", ".csv": "text/csv"}
SCHEMA = "http://schema.org/"


def git(args, cwd):
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True)
    return r.returncode, r.stdout


def ref(x):
    return {"@id": x}


def one_or_many(items):
    items = sorted({json.dumps(i, sort_keys=True) for i in items})
    items = [json.loads(i) for i in items]
    return items[0] if len(items) == 1 else items


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "x"


def known(v):
    return isinstance(v, str) and v and v != "unknown"


class Crate:
    def __init__(self):
        self.nodes = {}

    def add(self, node):
        cur = self.nodes.get(node["@id"])
        if cur is None:
            self.nodes[node["@id"]] = node
        else:
            for k, v in node.items():
                cur.setdefault(k, v)
        return ref(node["@id"])

    def graph(self):
        return [self.nodes[k] for k in sorted(self.nodes)]


def parse_lines(data):
    out = []
    for raw in (data or b"").replace(b"\r\n", b"\n").split(b"\n"):
        if not raw.strip():
            continue
        try:
            o = json.loads(raw)
        except ValueError:
            continue
        if isinstance(o, dict):
            out.append(o)
    return out


def build(clone, rev, with_pushlog, witness_folder):
    """Return {relative path: bytes} for the crate folder."""
    code, listing = git(["ls-tree", "-r", "-z", "--name-only", rev], clone)
    paths = sorted(p for p in listing.decode("utf-8").split("\0") if p)
    files = {}
    for p in paths:
        code, data = git(["show", "%s:%s" % (rev, p)], clone)
        files[p] = data
    code, out = git(["log", "-1", "--format=%cI", rev], clone)
    published = out.decode().strip()
    code, out = git(["rev-parse", rev], clone)
    commit = out.decode().strip()
    code, out = git(["log", "--reverse", "--format=%H%x09%cI%x09%an%x09%s", rev], clone)
    commits = [ln.split("\t", 3) for ln in out.decode("utf-8", "replace").splitlines() if ln.count("\t") >= 3]
    cfg = json.loads(files.get("org/config.json", b"{}").decode("utf-8") or "{}")
    seed = json.loads(files.get("seed.json", b"{}").decode("utf-8") or "{}")
    recs = {rel: parse_lines(files.get(rel)) for rel in L.RECORD_FILES.values()}
    events = recs[L.RECORD_FILES["event"]]
    born = next((e for e in events if e.get("type") == "born"), {}) or {}
    birth = (born.get("seed") or {}).get("tree")
    name = (cfg.get("organization") or {}).get("name") or "An organization grown from %s" % seed.get("name", "a seed")
    founder_name = next((c[2] for c in reversed(commits) if c[3].startswith("[CLOSE]")), None)
    founders = {i.get("id") for r in cfg.get("roles", []) if r.get("id") == "founder" for i in r.get("instances", [])}

    C = Crate()
    founder = C.add({"@id": "#founder", "@type": "Person", "name": founder_name or "the founder",
                     "description": "The organization's founder: sets its goal and signs its decisions."})
    C.add({"@id": PROFILE, "@type": "CreativeWork", "name": "Process Run Crate", "version": "0.6"})
    C.add({"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "conformsTo": ref(CRATE_SPEC), "about": ref("./")})
    seed_node = C.add({"@id": "#seed", "@type": "SoftwareSourceCode", "name": seed.get("name", "seed"),
                       "version": seed.get("version", "unknown"),
                       "description": "The seed this organization was born from; its git tree id is the birth hash.",
                       "identifier": birth or "unknown"})
    # The seed's own LICENSE files cover the seed; an organization's records and work take the founder's licence.
    license_file = next((p for p in ("org/LICENSE.md", "org/LICENSE", "org/LICENSE.txt") if p in files), None)
    parts = []
    for p in paths:
        data = files[p]
        types = ["File", "SoftwareSourceCode"] if p.startswith("scripts/") else "File"
        node = {"@id": p, "@type": types, "name": p, "contentSize": str(len(data)),
                "sha256": L.hashlib.sha256(data).hexdigest()}
        ext = os.path.splitext(p)[1].lower()
        if ext in MEDIA:
            node["encodingFormat"] = MEDIA[ext]
        if p.startswith("records/"):
            node["description"] = "Append-only records, one JSON object per line (%d lines)." % len(parse_lines(data))
        parts.append(C.add(node))
    if with_pushlog:
        log = os.path.join(witness_folder, W.PUSH_LOG)
        if os.path.exists(log):
            with open(log, "rb") as f:
                data = f.read()
            files["witness_pushlog.jsonl"] = data
            parts.append(C.add({"@id": "witness_pushlog.jsonl", "@type": "File", "name": "witness_pushlog.jsonl",
                                "sha256": L.hashlib.sha256(data).hexdigest(), "contentSize": str(len(data)),
                                "description": "The witness's own log of push attempts, accepted and refused. It sits "
                                               "outside the organization's history and is not covered by it."}))

    def who(ident):
        """(agent ref or None, [instrument refs]) for one record's identity."""
        ident = ident or {}
        if ident.get("kind") == "human":
            return (founder if ident.get("instance") in founders or not founders else
                    C.add({"@id": "#person-%s" % slug(ident.get("instance")), "@type": "Person",
                           "name": ident.get("instance")})), []
        if ident.get("kind") == "script":
            return None, [ref("scripts/%s.py" % ident.get("instance"))] if \
                "scripts/%s.py" % ident.get("instance") in files else []
        inst = []
        model = ident.get("model_id")
        if known(model):
            node = {"@id": "#model-%s-%s" % (slug(ident.get("producer")), slug(model)), "@type": "SoftwareApplication",
                    "name": model}
            if known(ident.get("producer")):
                node["producer"] = C.add({"@id": "#org-%s" % slug(ident["producer"]), "@type": "Organization",
                                          "name": ident["producer"]})
            if known(ident.get("model_snapshot")):
                node["softwareVersion"] = ident["model_snapshot"]
            inst.append(C.add(node))
        if known(ident.get("agent_app")):
            node = {"@id": "#app-%s" % slug(ident["agent_app"]), "@type": "SoftwareApplication",
                    "name": ident["agent_app"]}
            inst.append(C.add(node))
        if not inst:
            inst.append(C.add({"@id": "#member-%s" % slug(ident.get("instance")), "@type": "SoftwareApplication",
                               "name": "AI member %s (model not on record)" % ident.get("instance")}))
        return None, inst

    actions = []
    sessions = {}
    for rel, rows in recs.items():
        for o in rows:
            s = o.get("session")
            if not s or s == "S000":
                continue
            sess = sessions.setdefault(s, {"times": [], "inst": [], "agents": [], "files": set(), "roles": set()})
            if o.get("ts"):
                sess["times"].append(o["ts"])
            agent, inst = who(o.get("identity"))
            sess["inst"] += inst
            if agent:
                sess["agents"].append(agent)
            sess["files"].add(rel)
            if (o.get("identity") or {}).get("kind") in ("ai", "human") and o["identity"].get("instance"):
                sess["roles"].add(o["identity"]["instance"])
    for s, v in sorted(sessions.items()):
        props = [C.add({"@id": "#%s-role-%s" % (s, slug(r)), "@type": "PropertyValue", "name": "role instance at work",
                        "value": r}) for r in sorted(v["roles"])]
        node = {"@id": "#session-%s" % s, "@type": "CreateAction", "name": "Session %s" % s,
                "description": "The records written in session %s, through the seed's appender." % s,
                "instrument": one_or_many([ref("scripts/fos_log.py")] + v["inst"]) if "scripts/fos_log.py" in files
                else one_or_many(v["inst"] or [seed_node]),
                "agent": founder, "result": one_or_many([ref(f) for f in sorted(v["files"])]),
                "startTime": min(v["times"]) if v["times"] else published,
                "endTime": max(v["times"]) if v["times"] else published,
                "actionStatus": ref(SCHEMA + "CompletedActionStatus")}
        if props:
            node["additionalProperty"] = one_or_many(props)
        actions.append(C.add(node))
    for h, when, author, subject in commits:
        if subject.startswith("[CLOSE]"):
            actions.append(C.add({"@id": "#commit-%s" % h[:12], "@type": "UpdateAction", "name": subject,
                                  "identifier": h, "endTime": when, "agent": founder,
                                  "instrument": ref("scripts/fos_close.py") if "scripts/fos_close.py" in files else seed_node,
                                  "object": ref("./"), "actionStatus": ref(SCHEMA + "CompletedActionStatus")}))
        elif subject.startswith(("[SEED]", "[BIRTH]")):
            actions.append(C.add({"@id": "#commit-%s" % h[:12], "@type": "CreateAction", "name": subject,
                                  "identifier": h, "endTime": when, "object": seed_node, "result": ref("./"),
                                  "instrument": ref("scripts/fos_init.py") if "scripts/fos_init.py" in files else seed_node,
                                  "actionStatus": ref(SCHEMA + "CompletedActionStatus")}))
    for p in recs[L.RECORD_FILES["proposal"]]:
        node = {"@id": "#%s" % p.get("id"), "@type": "CreativeWork", "name": "%s: %s" % (p.get("id"), p.get("change")),
                "description": p.get("why") or "", "dateCreated": p.get("ts") or published}
        by = p.get("proposed_by")
        if by in founders:
            node["author"] = founder
        elif by:
            node["additionalProperty"] = C.add({"@id": "#%s-proposed-by" % p.get("id"), "@type": "PropertyValue",
                                                "name": "proposed by", "value": by})
        C.add(node)
    for d in recs[L.RECORD_FILES["decision"]]:
        kind = {"adopted": "AcceptAction", "amended": "AcceptAction", "declined": "RejectAction"}.get(d.get("verdict"),
                                                                                                    "ChooseAction")
        agent, inst = who(d.get("identity"))
        node = {"@id": "#%s" % d.get("id"), "@type": kind, "name": d.get("question") or d.get("id"),
                "description": "Reply, word for word: %s" % (d.get("words") or ""), "endTime": d.get("ts") or published,
                "object": one_or_many([ref("#%s" % x) for x in d.get("proposal_ids") or []] or [ref("./")])}
        if d.get("decided_by") in founders:
            node["agent"] = founder
        node["instrument"] = one_or_many(inst or [ref("scripts/fos_log.py")])
        actions.append(C.add(node))
    for s in recs[L.RECORD_FILES["signature"]]:
        if s.get("mode") == "test":
            kind, label = "AssessAction", "Test signature (signs nothing)"
        else:
            kind = {"signed": "EndorseAction", "refused": "RejectAction"}.get(s.get("answer"), "AssessAction")
            label = {"signed": "Signed", "refused": "Not signed", "sent_back": "Sent back"}.get(s.get("answer"), "Answered")
        node = {"@id": "#%s" % s.get("id"), "@type": kind, "name": "%s: %s %s" % (s.get("id"), label, s.get("decision_id")),
                "object": ref("#%s" % s.get("decision_id")), "agent": founder, "endTime": s.get("ts") or published,
                "instrument": ref("scripts/fos_close.py") if "scripts/fos_close.py" in files else seed_node,
                "additionalProperty": one_or_many([
                    C.add({"@id": "#%s-decision-sha256" % s.get("id"), "@type": "PropertyValue",
                           "name": "SHA-256 of the decision line signed", "value": s.get("decision_sha256") or ""}),
                    C.add({"@id": "#%s-shown-sha256" % s.get("id"), "@type": "PropertyValue",
                           "name": "SHA-256 of the text the founder was shown", "value": s.get("shown_sha256") or ""})])}
        if s.get("note"):
            node["description"] = "The founder's note: %s" % s["note"]
        actions.append(C.add(node))
    for x in recs[L.RECORD_FILES["decline"]]:
        if not x.get("id"):
            continue
        rule = C.add({"@id": "#rule-%s" % slug(x.get("rule_id")), "@type": "DefinedTerm", "name": x.get("rule_id") or "?"})
        agent, inst = who(x.get("identity"))
        node = {"@id": "#%s" % x.get("id"), "@type": "Action", "name": "Turned back: %s" % (x.get("what") or ""),
                "actionStatus": ref(SCHEMA + "FailedActionStatus"), "error": x.get("why_declined") or "",
                "instrument": one_or_many([rule] + inst), "endTime": x.get("ts") or published}
        if agent:
            node["agent"] = agent
        actions.append(C.add(node))
    root = {"@id": "./", "@type": "Dataset", "name": "%s, at %s" % (name, commit[:12]),
            "description": "The witnessed history of an organization grown from %s %s: its records, its files, and "
                           "what it did, as of commit %s." % (seed.get("name", "a seed"), seed.get("version", ""), commit),
            "datePublished": published, "conformsTo": ref(PROFILE), "hasPart": one_or_many(parts),
            "mentions": one_or_many(actions), "isBasedOn": seed_node,
            "identifier": one_or_many([
                C.add({"@id": "#commit", "@type": "PropertyValue", "name": "git commit", "value": commit}),
                C.add({"@id": "#birth-hash", "@type": "PropertyValue", "name": "birth hash (seed tree)",
                       "value": birth or "unknown"})]),
            "license": ref(license_file) if license_file else
            "The founder has chosen no licence for this organization's records and work (none in org/LICENSE.md); ask the "
            "founder before reusing them. The seed's own files keep the seed's licences (LICENSE, LICENSE-docs)."}
    C.add(root)
    crate = {"@context": CRATE_CONTEXT, "@graph": C.graph()}
    files["ro-crate-metadata.json"] = (json.dumps(crate, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    files["prov/run.prov.jsonld"] = (json.dumps(build_prov(recs, files, commits, founders, published), indent=1,
                                                sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    return files


def dt(value):
    return {"@value": value, "@type": "xsd:dateTime"}


def build_prov(recs, files, commits, founders, published):
    """PROV-O: record lines as entities attributed to their writers, sessions and close-outs as activities."""
    g = {}

    def node(n):
        cur = g.setdefault(n["@id"], {"@id": n["@id"]})
        for k, v in n.items():
            cur.setdefault(k, v)
        return {"@id": n["@id"]}
    founder = node({"@id": "#founder", "@type": "prov:Person"})
    for rel, rows in sorted(recs.items()):
        for o in rows:
            ident = o.get("identity") or {}
            eid = "%s#%s" % (rel, o.get("seq"))
            ent = {"@id": eid, "@type": "prov:Entity"}
            if o.get("ts"):
                ent["prov:generatedAtTime"] = dt(o["ts"])
            kind = ident.get("kind")
            if kind == "human":
                who = founder if ident.get("instance") in founders or not founders else \
                    node({"@id": "#person-%s" % slug(ident.get("instance")), "@type": "prov:Person"})
            elif kind == "script":
                who = node({"@id": "#script-%s" % slug(ident.get("instance")), "@type": "prov:SoftwareAgent",
                            "prov:actedOnBehalfOf": founder})
            else:
                who = node({"@id": "#instance-%s" % slug(ident.get("instance")), "@type": "prov:SoftwareAgent"})
                desc = {k: ident.get(k) for k in ("model_id", "producer", "agent_app", "host", "model_id_source", "source")
                        if ident.get(k)}
                if isinstance(ident.get("launch"), dict):
                    desc["launch"] = ident["launch"].get("id")
                ent["prov:wasAttributedTo"] = who
                if desc:
                    ent["rdfs:comment"] = "written by %s; %s" % (ident.get("instance"), json.dumps(desc, sort_keys=True))
            ent.setdefault("prov:wasAttributedTo", who)
            s = o.get("session")
            if s and s != "S000":
                act = node({"@id": "#session-%s" % s, "@type": "prov:Activity"})
                ent["prov:wasGeneratedBy"] = act
                assoc_id = "#session-%s-%s" % (s, slug(ident.get("instance") or "unknown"))
                node({"@id": assoc_id, "@type": "prov:Association", "prov:agent": who,
                      "prov:hadRole": {"@id": "#role-%s" % slug(ident.get("instance") or "unknown")}})
                quals = g[act["@id"]].setdefault("prov:qualifiedAssociation", [])
                if {"@id": assoc_id} not in quals:
                    quals.append({"@id": assoc_id})
                node({"@id": "#role-%s" % slug(ident.get("instance") or "unknown"), "@type": "prov:Role"})
            if rel.endswith("claims.jsonl") and o.get("quote") and o.get("source_file") in files:
                ent["prov:wasQuotedFrom"] = {"@id": o["source_file"]}
                node({"@id": o["source_file"], "@type": "prov:Entity"})
            if rel.endswith("signatures.jsonl"):
                dec = next((x for x in recs[L.RECORD_FILES["decision"]] if x.get("id") == o.get("decision_id")), None)
                if dec:
                    ent["prov:wasDerivedFrom"] = {"@id": "%s#%s" % (L.RECORD_FILES["decision"], dec.get("seq"))}
            node(ent)
    for h, when, author, subject in commits:
        if subject.startswith("[CLOSE]"):
            node({"@id": "#commit-%s" % h[:12], "@type": ["prov:Bundle", "prov:Entity"],
                  "prov:wasAttributedTo": founder, "prov:generatedAtTime": dt(when)})
    for act in [v for k, v in g.items() if k.startswith("#session-") and v.get("@type") == "prov:Activity"]:
        times = sorted(e["prov:generatedAtTime"]["@value"] for e in g.values()
                       if e.get("prov:wasGeneratedBy") == {"@id": act["@id"]} and e.get("prov:generatedAtTime"))
        if times:
            act["prov:startedAtTime"], act["prov:endedAtTime"] = dt(times[0]), dt(times[-1])
        act["prov:wasAssociatedWith"] = founder
    for v in g.values():
        if isinstance(v.get("prov:qualifiedAssociation"), list):
            v["prov:qualifiedAssociation"] = sorted(v["prov:qualifiedAssociation"], key=lambda x: x["@id"])
    ctx = dict(PROV_CONTEXT, rdfs="http://www.w3.org/2000/01/rdf-schema#")
    return {"@context": ctx, "@graph": [g[k] for k in sorted(g)]}


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    rev = argv[argv.index("--rev") + 1] if "--rev" in argv and argv.index("--rev") + 1 < len(argv) else None
    if rev in args:
        args.remove(rev)
    if not args:
        print(__doc__)
        return 2
    out = os.path.abspath(args[0])
    try:
        inside = os.path.commonpath([L.ROOT, out]) == L.ROOT
    except ValueError:
        inside = False
    if inside:
        print("Write the crate outside the organization's folder, so it never enters its history.")
        return 1
    if os.path.exists(out) and os.listdir(out):
        print("%s exists and is not empty; choose a new folder" % out)
        return 1
    w = L.find_witness()
    if not w or w.get("kind") != "git" or not os.path.isdir(w.get("history") or ""):
        print("A crate is made from the witnessed history, and no witness history is readable here.")
        return 1
    tmp = tempfile.mkdtemp(prefix="crate-")
    try:
        clone = os.path.join(tmp, "c")
        code, _ = git(["clone", "-q", "--no-hardlinks", w["history"], clone], tmp)
        if code != 0:
            print("Could not clone the witness.")
            return 1
        rev = rev or L.witness_branch(w["history"])
        code, _ = git(["rev-parse", "--verify", "--quiet", rev + "^{commit}"], clone)
        if code != 0:
            print("Revision %s is not in the witnessed history." % rev)
            return 1
        files = build(clone, rev, "--with-pushlog" in argv, w["folder"])
    finally:
        def unlock(func, p, _):
            os.chmod(p, 0o700)     # git keeps its object files read-only
            func(p)
        shutil.rmtree(tmp, onerror=unlock)
    for rel, data in files.items():
        p = os.path.join(out, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
    print("wrote %s: %d files, ro-crate-metadata.json and prov/run.prov.jsonld" % (out, len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
