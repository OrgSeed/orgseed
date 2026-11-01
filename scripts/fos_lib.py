"""Shared helpers for the seed's scripts.

Standard library only; no network. The one function that writes records is
append_record(): every script and every member goes through it (through
scripts/fos_log.py), so every record is checked before it is written and no
records file is ever written whole.
"""
import datetime
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_witness as W  # noqa: E402  (the self-contained history check)

# ---------------------------------------------------------------- record files

RECORD_FILES = {
    "event": "records/events.jsonl",
    "proposal": "records/proposals.jsonl",
    "decision": "records/decisions.jsonl",
    "signature": "records/signatures.jsonl",
    "decline": "records/declines.jsonl",
    "claim": "records/claims.jsonl",
    "drill": "records/drills.jsonl",
    "correction": "records/corrections.jsonl",
    "commitment": "records/commitments.jsonl",
    "recall": "records/recall.jsonl",
    "dissent": "records/dissent.jsonl",
    "review": "records/reviews.jsonl",
    "need": "records/needs.jsonl",
    "pin": "records/pins.jsonl",
    "deviation": "records/deviations.jsonl",
    "success": "records/successes.jsonl",
}
SCHEMA_OF = {
    "records/events.jsonl": ("event.schema.json", None),
    "records/proposals.jsonl": ("proposal.schema.json", None),
    "records/decisions.jsonl": ("decision.schema.json", None),
}
ID_PREFIX = {
    "proposal": "P", "decision": "D", "signature": "SG", "decline": "X", "claim": "CL",
    "drill": "DR", "correction": "C", "commitment": "K", "recall": "RC", "dissent": "DS",
    "review": "RV", "need": "N", "pin": "PN", "deviation": "DV", "success": "SU",
}
REPEATABLE_IDS = {"commitment", "need", "drill", "pin"}      # a later line with the same id records a new state
SCRIPT_ONLY_KINDS = {"signature", "drill"}             # written only by fos_close / fos_drill
SCRIPT_ONLY_EVENTS = {"born", "witness_created", "close_out", "integrity_repair", "unrecorded_session", "sync",
                      "instance_launched", "study_configured"}
SCRIPT_CAPTURES = {"script", "close_script", "init_script", "drill_script", "sync_script", "launch_script"}
KEY_ORDER = ["seq", "id", "ts", "session", "type", "identity", "captured_by"]


class RecordError(Exception):
    pass


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def path(rel):
    return os.path.join(ROOT, *rel.split("/"))


def exists(rel):
    return os.path.exists(path(rel))


def read_bytes(rel):
    """File contents as bytes, or None when the file does not exist."""
    p = path(rel)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return f.read()


def read_text(rel, default=None):
    """File contents as text, or `default` (None) when the file does not exist."""
    data = read_bytes(rel)
    return default if data is None else data.decode("utf-8", errors="replace")


def load_json(rel):
    with open(path(rel), encoding="utf-8") as f:
        return json.load(f)


def config():
    return load_json("org/config.json")


def seed_info():
    try:
        return load_json("seed.json")
    except (OSError, ValueError):
        return {"name": "seed", "version": "unknown"}


def config_hash():
    """A short hash of org/config.json, the same whether the file was checked out with LF or CRLF line endings."""
    return hashlib.sha256((read_bytes("org/config.json") or b"").replace(b"\r\n", b"\n")).hexdigest()[:12]


def tools_registry():
    try:
        return load_json("org/TOOLS.json")
    except (OSError, ValueError):
        return {"tools": []}


def local_settings():
    """Machine-local settings (.local.json, never committed): for example where the witness is."""
    try:
        return load_json(".local.json")
    except (OSError, ValueError):
        return {}


def write_local_settings(data):
    with open(path(".local.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, sort_keys=True)


# ---------------------------------------------------------------- reading records

class Parsed:
    def __init__(self, rel):
        self.rel = rel
        self.rows = []      # (line_no, raw_line, obj)
        self.bad = []       # (line_no, raw_line, message)
        self.missing = False
        self.max_seq = 0

    @property
    def objs(self):
        return [o for _, _, o in self.rows]


def read_records(rel):
    """Parse a records file. Nothing is skipped silently: bad lines are listed with their numbers."""
    p = Parsed(rel)
    data = read_bytes(rel)
    if data is None:
        p.missing = True
        return p
    for i, raw in enumerate(data.split(b"\n"), 1):
        line = raw.rstrip(b"\r")
        if not line.strip():
            continue
        try:
            text = line.decode("utf-8")
            obj = W.strict_loads(text)    # a key written twice makes the line say two things: it is not a record
        except W.DuplicateKey as e:
            p.bad.append((i, line, "not a valid record (%s, so the line says two things)" % e))
            continue
        except (UnicodeDecodeError, ValueError) as e:
            p.bad.append((i, line, "not valid JSON (%s)" % (getattr(e, "msg", None) or e.__class__.__name__)))
            continue
        if not isinstance(obj, dict):
            p.bad.append((i, line, "not a JSON object"))
            continue
        p.rows.append((i, line, obj))
        s = obj.get("seq")
        if isinstance(s, int) and not isinstance(s, bool) and s > p.max_seq:
            p.max_seq = s
    return p


def read_all():
    return {kind: read_records(rel) for kind, rel in RECORD_FILES.items()}


def line_sha256(raw):
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    return hashlib.sha256(raw.rstrip(b"\r\n")).hexdigest()


# ---------------------------------------------------------------- schema check (type, required, enum, properties, items, $ref, allOf)

_TYPES = {"string": str, "integer": int, "boolean": bool, "object": dict, "array": list,
          "null": type(None), "number": (int, float)}
_SCHEMAS = {}


def _schema_file(name):
    if name not in _SCHEMAS:
        _SCHEMAS[name] = load_json("schemas/" + name)
    return _SCHEMAS[name]


def _resolve(ref, doc):
    file, _, pointer = ref.partition("#")
    target = _schema_file(file) if file else doc
    node = target
    for part in [x for x in pointer.split("/") if x]:
        node = node[part]
    return node, target


def _type_ok(value, t):
    if t in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, _TYPES[t])


def check(obj, schema, where="", doc=None):
    """Return a list of problems; empty when obj fits the schema."""
    doc = doc if doc is not None else schema
    probs = []
    if "$ref" in schema:
        sub, subdoc = _resolve(schema["$ref"], doc)
        probs += check(obj, sub, where, subdoc)
    for sub in schema.get("allOf", []):
        probs += check(obj, sub, where, doc)
    t = schema.get("type")
    if t:
        ts = t if isinstance(t, list) else [t]
        if not any(_type_ok(obj, x) for x in ts):
            return probs + ["%s: expected %s" % (where or "value", "/".join(ts))]
    if "enum" in schema and obj not in schema["enum"]:
        probs.append("%s: %r is not one of %s" % (where or "value", obj, [x for x in schema["enum"] if x is not None]))
    if isinstance(obj, dict):
        for k in schema.get("required", []):
            if k not in obj:
                probs.append("%s: missing required field '%s'" % (where or "record", k))
        for k, sub in schema.get("properties", {}).items():
            if k in obj:
                probs += check(obj[k], sub, (where + "." if where else "") + k, doc)
    if isinstance(obj, list) and "items" in schema:
        for i, item in enumerate(obj):
            probs += check(item, schema["items"], "%s[%d]" % (where, i), doc)
    return probs


def schema_for(rel):
    if rel in SCHEMA_OF:
        return _schema_file(SCHEMA_OF[rel][0]), _schema_file(SCHEMA_OF[rel][0])
    led = _schema_file("ledgers.schema.json")
    name = led.get("x-files", {}).get(rel)
    if name:
        return led["$defs"][name], led
    return None, None


def validate(rel, obj):
    schema, doc = schema_for(rel)
    return check(obj, schema, "", doc) if schema else []


# ---------------------------------------------------------------- identity (AGENTS.md, CORE-6)

def instances(cfg):
    """Map instance id -> (role, instance dict)."""
    out = {}
    for role in cfg.get("roles", []):
        for inst in role.get("instances", []):
            out[inst.get("id")] = (role, inst)
    return out


def ai_instances(cfg):
    return [i for i, (r, _) in instances(cfg).items() if r.get("kind") == "ai"]


def identity_for(cfg, instance):
    """An identity block filled from the instance's model slot. 'unknown' where the slot is empty."""
    found = instances(cfg).get(instance)
    if not found:
        raise RecordError("no role instance '%s' in org/config.json" % instance)
    role, inst = found
    if role.get("kind") == "human":
        return {"instance": instance, "kind": "human", "source": "config_slot"}
    slot = inst.get("slot") or {}
    return {"instance": instance, "kind": "ai",
            "model_id": slot.get("model_id") or "unknown", "producer": slot.get("producer") or "unknown",
            "agent_app": slot.get("agent_app") or "unknown", "host": slot.get("host") or "unknown",
            "model_id_source": slot.get("model_id_source") or "unknown", "source": "config_slot"}


def script_identity(name):
    return {"instance": name, "kind": "script"}


# ---------------------------------------------------------------- launches: identity the member did not write

LAUNCH_FILE = ".fos_launch.json"
LAUNCH_ENV = "FOS_LAUNCH"


def current_launch():
    """(launch id, instance, secret) set by the founder's fos_launch for this agent app, or None.
    Read from the environment variable FOS_LAUNCH, else from .fos_launch.json in the folder."""
    line = os.environ.get(LAUNCH_ENV, "").strip()
    if not line:
        try:
            line = (load_json(LAUNCH_FILE) or {}).get("launch", "").strip()
        except (OSError, ValueError, AttributeError):
            line = ""
    parts = line.split(":", 2)
    if len(parts) == 3 and parts[0].startswith("L-") and all(parts):
        return tuple(parts)
    return None


def record_mac(secret, rec):
    """The fingerprint of one record: HMAC-SHA256 over its canonical JSON, without the fingerprint itself."""
    import hmac
    r = json.loads(json.dumps(rec))
    ident = r.get("identity") or {}
    launch = dict(ident.get("launch") or {})
    launch.pop("mac", None)
    ident["launch"] = launch
    r["identity"] = ident
    msg = json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def launch_event(events, launch_id):
    for e in events:
        if e.get("type") == "instance_launched" and e.get("launch_id") == launch_id:
            return e
    return None


def witness_launches():
    """{launch id: launch} from the witness folder's launches/, or None when the witness cannot be read here."""
    w = find_witness()
    d = os.path.join(w["folder"], "launches") if w else None
    if not d or not os.path.isdir(w["folder"]):
        return None
    out = {}
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(d, fn), encoding="utf-8") as f:
                        x = json.load(f)
                    out[x.get("id")] = x
                except (OSError, ValueError):
                    pass
    return out


def is_terminal():
    return sys.stdin.isatty() and sys.stdout.isatty()


def session_number(label):
    return int(label[1:]) if isinstance(label, str) and label[:1] == "S" and label[1:].isdigit() else None


SESSION_MARKS = ("session_start", "close_out")   # a session is counted when it starts or when it is closed


def next_session(events):
    """The label a new session gets: one more than any session started or closed so far. Counting close-outs
    too means a session nobody recorded still uses up its number."""
    n = 0
    for e in events:
        if e.get("type") in SESSION_MARKS:
            v = session_number(e.get("session"))
            if v is not None:
                n = max(n, v)
    return "S%03d" % (n + 1)


def current_session(events):
    """The session a record written now belongs to: the latest session_start, unless a close-out came after it;
    then a new session has begun, even if nobody has recorded its start yet."""
    label, last_start, last_close = None, -1, -1
    for i, e in enumerate(events):
        t = e.get("type")
        if t == "session_start" and session_number(e.get("session")) is not None:
            label, last_start = e["session"], i
        elif t == "close_out":
            last_close = i
    if label is not None and last_start > last_close:
        return label
    return next_session(events)


def since_last_close(events):
    """The events written since the last close-out (all of them before the first close-out)."""
    last = max([i for i, e in enumerate(events) if e.get("type") == "close_out"] or [-1])
    return events[last + 1:]


def session_recorded(events):
    """True when a session_start was recorded since the last close-out."""
    return any(e.get("type") == "session_start" for e in since_last_close(events))


def counted_sessions(events):
    """Session labels in order, counting every session started or closed (an unrecorded session counts once
    its close-out names it)."""
    out = []
    for e in events:
        s = e.get("session")
        if e.get("type") in SESSION_MARKS and session_number(s) and s not in out:
            out.append(s)
    return out


def boot_route(stage, cfg, events):
    """Which file a member opening a new session follows. It is read from the sessions on record, never from
    'founded' alone: the first session (onboarding/START.md) only while no session is on record; every session
    after that starts from what the last one left (onboarding/SESSION_START.md), founded or not. Founded is the
    stage, read from the history (founding_state), not org/config.json's word for it.
    Returns {'next', 'why', 'sessions', 'founded'}."""
    founded = stage == "founded"
    if stage == "seed":
        return {"next": "python scripts/fos_init.py ../my-organization in a terminal, or double-click "
                        "Found-an-organization (no AI is involved)",
                "why": "this folder is the seed itself, not an organization", "sessions": [], "founded": False}
    sessions = counted_sessions(events)
    if not sessions:
        return {"next": "onboarding/START.md", "why": "no session is on record yet: this is the first session",
                "sessions": [], "founded": founded}
    why = "%d session(s) on record (%s)" % (len(sessions), ", ".join(sessions[-6:]))
    if not founded:
        why += ("; not founded yet: an earlier session stopped before the founding decision, so finish the founding "
                "from where the records stop, without starting the first session again")
    return {"next": "onboarding/SESSION_START.md", "why": why, "sessions": sessions, "founded": founded}


# ---------------------------------------------------------------- the one writer

# The signing gate. A signature is written only by the founder's close-out, from its main() and only once that main()
# has passed its terminal guard (scripts/fos_close.py): there it opens the gate with its own code, and every signature
# is refused unless that main() is running further up the call. A member's script that imports the close-out and
# calls its functions is refused. A member who can write files and run git can still write a signature line by hand,
# and the seed cannot tell that line from the close-out's (docs/SECURITY.md); the lock for that is a founder secret.
_SIGNING = {"main": None}


def open_signing(main_code):
    """Called by the close-out's main() once its terminal guard has passed (in the self-test, its test mode)."""
    _SIGNING["main"] = main_code


def signing_open():
    """True when the close-out's main() opened the signing gate and is running further up this call."""
    code = _SIGNING["main"]
    f = sys._getframe(1) if code is not None else None
    while f is not None:
        if f.f_code is code:
            return True
        f = f.f_back
    return False


SIGNING_REFUSED = ("a signature is written only by the founder's close-out, from a terminal the founder is typing in "
                   "(python scripts/fos_close.py); it was asked for from elsewhere, so nothing was signed")


def _next_id(kind, parsed):
    prefix = ID_PREFIX[kind] + "-"
    n = 0
    for o in parsed.objs:
        v = o.get("id")
        if isinstance(v, str) and v.startswith(prefix) and v[len(prefix):].isdigit():
            n = max(n, int(v[len(prefix):]))
    return "%s%04d" % (prefix, n + 1)


LOCK_FILE = ".fos-lock"
_LOCK = {"depth": 0}


class RecordsLock:
    """One writer at a time in this folder, so members working side by side never get the same seq and
    never interleave their lines. A lock older than `stale` seconds was left by a writer that stopped."""

    def __init__(self, timeout=30.0, stale=120.0):
        self.timeout, self.stale = timeout, stale

    def __enter__(self):
        if _LOCK["depth"]:
            _LOCK["depth"] += 1
            return self
        p = path(LOCK_FILE)
        start = time.time()
        while True:
            try:
                fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except (FileExistsError, PermissionError):
                try:
                    age = time.time() - os.path.getmtime(p)
                except OSError:
                    continue
                if age > self.stale:
                    try:
                        os.remove(p)
                    except OSError:
                        pass
                    continue
                if time.time() - start > self.timeout:
                    raise RecordError("another writer holds %s, so nothing was written. Try again in a moment; if no "
                                      "other member is writing, the founder may delete that file" % LOCK_FILE)
                time.sleep(0.05)
                continue
            os.write(fd, ("%d %s\n" % (os.getpid(), now_utc())).encode("ascii"))
            os.close(fd)
            _LOCK["depth"] = 1
            return self

    def __exit__(self, *exc):
        _LOCK["depth"] -= 1
        if _LOCK["depth"] == 0:
            try:
                os.remove(path(LOCK_FILE))
            except OSError:
                pass
        return False


def append_record(kind, rec, writer="member", dry_run=False):
    """Validate one record and append it as one line. Return (line, warnings)."""
    lines, warnings = append_records([(kind, rec)], writer, dry_run)
    return lines[0], warnings


def append_records(items, writer="member", dry_run=False):
    """Validate several records, given as [(kind, record)], and append them in order. Return (lines, warnings).

    All of them are checked first, each seeing the ones before it; if any one does not fit, nothing is
    written. writer is "member" for fos_log, or the seed script's name. Records files are never created
    here: a missing file was deleted, and that must stay visible."""
    with RecordsLock():
        state, out, warnings = {}, [], []
        for i, (kind, rec) in enumerate(items, 1):
            try:
                rel, line, w = _prepare(kind, rec, writer, state)
            except RecordError as e:
                if len(items) > 1:
                    raise RecordError("record %d of %d (%s): %s\nNothing was written." % (i, len(items), kind, e))
                raise
            out.append((rel, line))
            warnings += [x for x in w if x not in warnings]
        if not dry_run:
            groups = {}
            for rel, line in out:
                groups.setdefault(rel, []).append(line)
            for rel, lines in groups.items():
                data = read_bytes(rel)
                with open(path(rel), "ab") as f:
                    if data and not data.endswith(b"\n"):
                        f.write(b"\n")
                    f.write(b"".join(x.encode("utf-8") + b"\n" for x in lines))
        return [line for _, line in out], warnings


def _parsed(state, rel):
    if rel not in state:
        state[rel] = read_records(rel)
    return state[rel]


def _prepare(kind, rec, writer, state):
    """Fill in and check one record against the files as they stand plus the records before it in this call."""
    if kind not in RECORD_FILES:
        raise RecordError("unknown record kind '%s'; use one of: %s" % (kind, ", ".join(RECORD_FILES)))
    rel = RECORD_FILES[kind]
    if kind == "signature" and writer != "member" and not signing_open():   # a member is refused below, as before
        raise RecordError(SIGNING_REFUSED)
    if not isinstance(rec, dict):
        raise RecordError("a record must be one JSON object")
    parsed = _parsed(state, rel)
    if parsed.missing:
        raise RecordError("%s is missing. Records files are never deleted or re-created (CORE-4). "
                          "Tell the founder; the founder's close-out (python scripts/fos_close.py) "
                          "offers to restore it from the last commit." % rel)
    warnings = []
    if parsed.bad:
        warnings.append("%s has %d line(s) that are not valid records (line %s). Leave them; append a "
                        "record_correction event that points to each (CORE-4)."
                        % (rel, len(parsed.bad), ", ".join(str(b[0]) for b in parsed.bad)))
    rec = dict(rec)
    if writer == "member":
        if kind in SCRIPT_ONLY_KINDS:
            raise RecordError("%s records are written only by the seed's scripts (fos_close signs, "
                              "fos_drill plants drills), never by a member" % kind)
        if kind == "event" and rec.get("type") in SCRIPT_ONLY_EVENTS:
            raise RecordError("'%s' events are written only by the seed's scripts" % rec.get("type"))
        if rec.get("captured_by") in SCRIPT_CAPTURES:
            raise RecordError("captured_by '%s' is reserved for the seed's scripts" % rec.get("captured_by"))
        rec.setdefault("captured_by", "member")
    if "seq" in rec and rec["seq"] != parsed.max_seq + 1:
        warnings.append("seq is assigned by the appender; %r was replaced" % rec["seq"])
    rec["seq"] = parsed.max_seq + 1
    rec.setdefault("ts", now_utc())
    if "session" not in rec:
        evs = _parsed(state, RECORD_FILES["event"]).objs
        if kind == "event" and rec.get("type") == "session_start":
            rec["session"] = next_session(evs)
        else:
            rec["session"] = current_session(evs)
    if kind in ID_PREFIX:
        given = rec.get("id")
        if given is not None and not (isinstance(given, str) and given.startswith(ID_PREFIX[kind] + "-")):
            raise RecordError("a %s id starts with %s- (or leave id out and one is assigned)" % (kind, ID_PREFIX[kind]))
        if given and kind not in REPEATABLE_IDS and given in {o.get("id") for o in parsed.objs}:
            raise RecordError("id %s is already used in %s" % (given, rel))
        if not given:
            rec["id"] = _next_id(kind, parsed)
    if kind == "claim" and rec.get("source_file") and "source_sha256" not in rec:
        digest = file_sha256(rec["source_file"])     # the saved source as it was when the claim was made
        if digest:
            rec["source_sha256"] = digest
    if kind == "event" and rec.get("type") == "source_fetched" and rec.get("saved_as") and "saved_sha256" not in rec:
        digest = file_sha256(rec["saved_as"])        # the page as it was saved when the fetch was logged
        if digest:
            rec["saved_sha256"] = digest
    inst = rec.pop("instance", None)
    launch = current_launch() if writer == "member" else None
    if writer == "member" and isinstance(rec.get("identity"), dict) and inst is None:
        inst = rec["identity"].get("instance")
    if launch and inst is not None and inst != launch[1]:
        raise RecordError("this agent app was launched as %s (%s), so it writes as %s, not as %s"
                          % (launch[1], launch[0], launch[1], inst))
    if "identity" not in rec:
        if writer != "member":
            rec["identity"] = script_identity(writer)
        else:
            cfg = config()
            if inst is None and launch:
                inst = launch[1]
            if inst is None:
                if rec.get("captured_by") == "founder":
                    inst = "founder"
                else:
                    ais = ai_instances(cfg)
                    if len(ais) != 1:
                        raise RecordError("say which instance you are: add instance=<id> (one of %s)" % ", ".join(ais))
                    inst = ais[0]
            ident = identity_for(cfg, inst)
            le = launch_event(_parsed(state, RECORD_FILES["event"]).objs, launch[0]) if launch else None
            if le and ident.get("kind") == "ai":
                ident.update({k: v for k, v in (le.get("launched") or {}).items() if v})
                ident["source"] = "launch"
            rec["identity"] = ident
    elif isinstance(rec["identity"], dict):
        rec["identity"] = dict(rec["identity"])
        rec["identity"].setdefault("source", "stated")
    ident = rec["identity"]
    if writer == "member" and isinstance(ident, dict) and ident.get("kind") == "human":
        # A record in a person's name comes only from that person's own terminal, never from an agent app.
        if is_terminal():
            ident["source"] = "terminal"
        elif os.environ.get("SEED_SELFTEST") != "1":
            raise RecordError("records in a person's name (%s) are written only from that person's own terminal; an "
                              "agent app cannot write them. Write the record as yourself, or ask the founder to run "
                              "this command" % ident.get("instance"))
        if ident.get("instance") in founder_instances(config()):
            rec["captured_by"] = "founder"
    if launch and isinstance(ident, dict):
        ident["launch"] = {"id": launch[0]}
    ordered = {k: rec[k] for k in KEY_ORDER if k in rec}
    ordered.update({k: v for k, v in rec.items() if k not in ordered})
    if launch and isinstance(ordered.get("identity"), dict):
        ordered["identity"]["launch"]["mac"] = record_mac(launch[2], ordered)
    problems = validate(rel, ordered)
    if problems:
        raise RecordError("not written; the record does not fit %s:\n  - %s" % (rel, "\n  - ".join(problems)))
    line = json.dumps(ordered, ensure_ascii=False)
    parsed.rows.append((None, line.encode("utf-8"), ordered))   # later records in this call see this one
    parsed.max_seq = ordered["seq"]
    return rel, line, warnings


# ---------------------------------------------------------------- git (optional, but the witness needs it)

def git(*args, data=None):
    """Run git in the organization's folder. Return (exit code, stdout text); (None, '') if git is unavailable."""
    if os.environ.get("SEED_NO_GIT") == "1":     # the self-test's way of simulating a machine without git
        return None, ""
    try:
        r = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, input=data)
    except (OSError, ValueError):
        return None, ""
    return r.returncode, r.stdout.decode("utf-8", errors="replace")


def git_ok():
    code, out = git("rev-parse", "--is-inside-work-tree")
    return code == 0 and out.strip() == "true"


def has_head():
    return git("rev-parse", "--verify", "--quiet", "HEAD")[0] == 0


def head_bytes(rel, rev="HEAD"):
    if os.environ.get("SEED_NO_GIT") == "1":
        return None
    try:
        r = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (rev, rel)], capture_output=True)
    except OSError:
        return None
    return r.stdout if r.returncode == 0 else None


def root_commit():
    code, out = git("rev-list", "--max-parents=0", "HEAD")
    roots = out.split() if code == 0 else []
    return roots[0] if len(roots) == 1 else None


def tree_of(rev):
    code, out = git("rev-parse", rev + "^{tree}")
    return out.strip() if code == 0 else None


def history_problems(rev="HEAD"):
    """Whole-history check of the records (the same check the witness runs on every push)."""
    if not git_ok() or not has_head():
        return []
    try:
        return W.check_history(["-C", ROOT], rev)
    except W.GitError as e:
        return [str(e)]


def _remote_url_from_config(name="witness"):
    """A remote's url read straight from .git/config, for places where git itself cannot start
    (some agent apps' sandboxes). None when there is no such remote or no readable config."""
    text = read_text(".git/config")
    if not text:
        return None
    section = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            section = s[1:-1].strip()
            continue
        if section == 'remote "%s"' % name and "=" in s:
            key, _, value = s.partition("=")
            if key.strip().lower() == "url":
                return value.strip().strip('"')
    return None


def find_witness():
    """Where this organization's witness is: {'kind': 'git'|'folder', 'folder', 'history', 'found_by'} or None.

    Looked for, in order: git's own remote 'witness'; the same remote read from .git/config without
    git; the machine-local setting (.local.json); the default folder next to this one."""
    url, found_by = None, None
    if git_ok():
        code, out = git("remote", "get-url", "witness")
        if code == 0 and out.strip():
            url, found_by = out.strip(), "git"
    if url is None:
        url = _remote_url_from_config("witness")
        found_by = "git_config_file" if url else None
    if url:
        hist = os.path.normpath(os.path.join(ROOT, url))
        return {"kind": "git", "folder": os.path.dirname(hist), "history": hist, "found_by": found_by}
    loc = local_settings().get("witness")
    if loc:
        folder = os.path.normpath(os.path.join(ROOT, loc))
        hist = os.path.join(folder, "history.git")
        return {"kind": "git" if os.path.isdir(hist) and git_ok() else "folder", "folder": folder,
                "history": hist if os.path.isdir(hist) else None, "found_by": "local_settings"}
    folder = default_witness_folder()
    if os.path.isdir(folder):
        hist = os.path.join(folder, "history.git")
        return {"kind": "git" if os.path.isdir(hist) else "folder", "folder": folder,
                "history": hist if os.path.isdir(hist) else None, "found_by": "default_folder"}
    return None


def default_witness_folder():
    return os.path.join(os.path.dirname(ROOT), os.path.basename(ROOT) + "-witness")


def witness_branch(hist):
    code, out, _ = W.run_git(["--git-dir", hist, "config", "--get", "witness.branch"])
    return out.decode().strip() if code == 0 and out.strip() else W.DEFAULT_BRANCH


def witness_relation(witness=None):
    """How this folder's history stands to its witness's. Returns a dict with 'state':
      equal      the same commit;
      ahead      this folder has close-outs the witness does not yet hold (n = how many);
      behind     the witness holds close-outs this folder never had: another copy was closed out (n);
      diverged   each has commits the other lacks, from a common commit 'base';
      unrelated  no commit in common: this folder's history was replaced;
      empty / unknown  the witness holds nothing yet, or cannot be read here.
    It never fetches: a witness tip this folder has never seen is looked up in the witness itself."""
    w = witness or find_witness()
    if not w or w.get("kind") != "git" or not w.get("history") or not os.path.isdir(w["history"]) \
            or not git_ok() or not has_head():
        return {"state": "unknown"}
    wg = ["--git-dir", w["history"]]
    tip = W.rev_parse(wg, "refs/heads/" + witness_branch(w["history"]))
    if not tip:
        return {"state": "empty"}
    head = git("rev-parse", "HEAD")[1].strip()
    out = {"tip": tip, "head": head, "base": None, "n": 0}
    if tip == head:
        return dict(out, state="equal", base=tip)

    def count(gp, a, b):
        code, txt, _ = W.run_git(list(gp) + ["rev-list", "--count", "%s..%s" % (a, b)])
        return int(txt.strip() or 0) if code == 0 else 0
    here = ["-C", ROOT]
    if git("cat-file", "-e", tip + "^{commit}")[0] == 0:
        if W.is_ancestor(here, tip, head):
            return dict(out, state="ahead", base=tip, n=count(here, tip, head))
        if W.is_ancestor(here, head, tip):
            return dict(out, state="behind", base=head, n=count(here, head, tip))
        code, base = git("merge-base", head, tip)
        if code == 0 and base.strip():
            base = base.strip()
            return dict(out, state="diverged", base=base, n=count(here, base, head), behind_n=count(here, base, tip))
        return dict(out, state="unrelated")
    if W.run_git(wg + ["cat-file", "-e", head + "^{commit}"])[0] == 0 and W.is_ancestor(wg, head, tip):
        return dict(out, state="behind", base=head, n=count(wg, head, tip))
    code, revs = git("rev-list", "--max-count=2000", "HEAD")
    for c in (revs.split() if code == 0 else []):
        if W.run_git(wg + ["cat-file", "-e", c + "^{commit}"])[0] == 0:
            return dict(out, state="diverged", base=c, n=count(here, c, head), behind_n=count(wg, c, tip))
    return dict(out, state="unrelated")


# ---------------------------------------------------------------- birth: from the history, never from events.jsonl alone

BIRTH_FILE = "org/BIRTH.json"


def _born_in(data):
    for raw in (data or b"").split(b"\n"):
        try:
            o = json.loads(raw)
        except ValueError:
            continue
        if isinstance(o, dict) and o.get("type") == "born":
            return o
    return None


def birth_from_git():
    """(birth record, [BIRTH] commit) as the history holds them, or (None, None).

    fos_init makes the [BIRTH] commit right after the first one; its records/events.jsonl holds the
    birth record. A member who overwrites events.jsonl, or even commits that, does not change it."""
    if not (git_ok() and has_head()):
        return None, None
    root = root_commit()
    if not root:
        return None, None
    # The birth commit is the first commit's child on the way to HEAD, and its subject starts with [BIRTH].
    # (Matching the subject only: a message body may mention "[BIRTH]" without being one.)
    code, out = git("rev-list", "--reverse", "--ancestry-path", "%s..HEAD" % root)
    child = out.split()[0] if code == 0 and out.split() else None
    if not child:
        return None, None
    code, subject = git("log", "-1", "--format=%s", child)
    if code != 0 or not subject.startswith("[BIRTH]"):
        return None, None
    return _born_in(head_bytes(RECORD_FILES["event"], child)), child


def birth_from_witness():
    """The birth record as the witness folder's latest dated copy holds it (used without git)."""
    w = find_witness()
    snap = W.latest_snapshot(w["folder"]) if w else None
    if not snap:
        return None
    p = os.path.join(snap, "events.jsonl")
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return _born_in(f.read())


def stage_info(cfg=None, events=None):
    """What this folder is, decided from the history and the witness, never from events.jsonl alone.

    Returns {'stage': 'seed'|'born'|'founded', 'birth': the birth record or None, 'source': where the
    birth was found ('git', 'witness', 'records' or None), 'damaged': True when the history or the
    witness holds a birth record that records/events.jsonl no longer has, 'unconfirmed': True when
    events.jsonl has a birth line that the history does not hold, 'commit': the [BIRTH] commit,
    'founding': founding_state()}. Founded comes from the history alone (founding_state), never from
    org/config.json or the decision records."""
    cfg = cfg if cfg is not None else config()
    if events is None:
        events = read_records(RECORD_FILES["event"]).objs
    here = next((e for e in events if e.get("type") == "born"), None)
    info = {"birth": None, "source": None, "damaged": False, "unconfirmed": False, "commit": None}
    if git_ok() and has_head():
        born, commit = birth_from_git()
        if commit:
            info.update(birth=born or here, source="git", commit=commit, damaged=bool(born) and here is None)
        elif here:
            info.update(birth=here, source="records", unconfirmed=True)
    else:
        born = birth_from_witness()
        if born:
            info.update(birth=born, source="witness", damaged=here is None)
        elif here:
            info.update(birth=here, source="records")
    if not info["birth"] and not info["commit"]:
        info["stage"] = "seed"
        info["founding"] = {"founded": False, "commit": None, "decision": None, "source": None}
    else:
        info["founding"] = founding_state(cfg)
        info["stage"] = "founded" if info["founding"]["founded"] else "born"
    return info


# ---------------------------------------------------------------- the founding: read from the history, never from labels

def founding_state(cfg=None, records=None):
    """Whether the organization is founded, and on which decision. Only one thing founds it: a close-out commit
    ([FOUND]) holding the founder's signature with founding "FOUND", which the founder typed at the close-out's prompt
    (fos_witness.founding_history, the same check the witness runs on every push). Without git, the same signature as
    the witness's dated copy holds it. A close-out that has just written one counts it, before its commit. What
    config.json or the decision records say plays no part. Returns {'founded', 'commit', 'decision', 'source'}."""
    cfg = cfg if cfg is not None else config()
    records = records if records is not None else read_all()
    founders = founder_instances(cfg) or {"founder"}
    for s in records["signature"].objs:
        if s.get("seq") in PENDING_OWN_SIGNATURES and W.is_founding_signature(s, founders):
            return {"founded": True, "commit": None, "decision": s.get("decision_id"), "source": "this close-out"}
    if git_ok() and has_head():
        try:
            fh = W.founding_history(["-C", ROOT], "HEAD")
            return {"founded": bool(fh["commit"]), "commit": fh["commit"], "decision": fh["decision"], "source": "git"}
        except W.GitError:
            pass
    counted, how = counted_signature_seqs(records["signature"])
    voided = void_signature_seqs(records["event"].objs)
    for s in records["signature"].objs:
        if s.get("seq") in counted and s.get("seq") not in voided and W.is_founding_signature(s, founders):
            return {"founded": True, "commit": None, "decision": s.get("decision_id"), "source": how}
    return {"founded": False, "commit": None, "decision": None, "source": "git" if git_ok() and has_head() else how}


def birth_structure():
    """{file: structure part} as the organization was born (its first commit), or None without git."""
    root = root_commit() if git_ok() and has_head() else None
    if not root:
        return None
    try:
        return W.structure_at(["-C", ROOT], root)
    except W.GitError:
        return None


def current_structure():
    """{file: structure part} as the folder holds the structural files now (fos_witness.STRUCTURE_FILES)."""
    return {rel: W.structure_part(rel, read_bytes(rel)) for rel in W.STRUCTURE_FILES}


def structure_since_birth():
    """[(file, what changed)] where the folder's structure now differs from its birth; None when that cannot be read
    (no git)."""
    birth = birth_structure()
    return None if birth is None else W.structure_differences(birth, current_structure())


def _short(v, n=110):
    if v is None:
        return "none"
    t = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, sort_keys=True)
    t = '"%s"' % t if isinstance(v, str) else t
    return t if len(t) <= n else t[:n - 3] + "..."


def _by_id(items):
    """{id: item} for a list whose items are all objects with distinct ids, else None."""
    if not all(isinstance(x, dict) and "id" in x for x in items):
        return None
    ids = [x["id"] for x in items]
    return dict(zip(ids, items)) if len(set(map(str, ids))) == len(ids) else None


def _json_changes(a, b, where, out):
    """Append (path, words) for each place two JSON values differ: objects key by key, lists of items with ids item by
    item, lists of plain values as values added and removed, anything else as was / now."""
    if a == b:
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in list(a) + [k for k in b if k not in a]:
            if k not in b:
                out.append((where + [k], "removed (it was %s)" % _short(a[k])))
            elif k not in a:
                out.append((where + [k], "added: %s" % _short(b[k])))
            else:
                _json_changes(a[k], b[k], where + [k], out)
        return
    if isinstance(a, list) and isinstance(b, list):
        by_a, by_b = _by_id(a), _by_id(b)
        if by_a is not None and by_b is not None:
            for k in by_a:
                if k not in by_b:
                    out.append((where + [k], "removed (it was %s)" % _short(by_a[k])))
            for k in by_b:
                if k not in by_a:
                    out.append((where + [k], "added: %s" % _short(by_b[k])))
                else:
                    _json_changes(by_a[k], by_b[k], where + [k], out)
            if [k for k in by_a if k in by_b] != [k for k in by_b if k in by_a]:
                out.append((where, "the order changed"))
            return
        if not any(isinstance(x, (dict, list)) for x in a + b):
            for x in a:
                if x not in b:
                    out.append((where, "removed: %s" % _short(x)))
            for x in b:
                if x not in a:
                    out.append((where, "added: %s" % _short(x)))
            if all(x in b for x in a) and all(x in a for x in b):
                out.append((where, "the order or the count of its entries changed"))
            return
    out.append((where, "was %s, now %s" % (_short(a), _short(b))))


def structure_changes():
    """What the folder's structure changes from the organization's birth, in plain words, for the founder to read before
    founding it (scripts/fos_close.py): [(file, path, words)], where path is a list of keys and ids inside a JSON file
    ([] for a whole file or a text file's line). The organization block and the model slots are not structure (as for
    the invariant, fos_witness.structure_part). None without git."""
    birth = birth_structure()
    if birth is None:
        return None
    now = current_structure()
    out = []
    for rel, _ in W.structure_differences(birth, now):
        a, b = birth.get(rel), now.get(rel)
        if b is None:
            out.append((rel, [], "the file is deleted"))
            continue
        if rel.endswith(".json"):
            twice = W.duplicate_key(b)
            if twice:
                out.append((rel, [], twice + ": the scripts read the last copy, and a person reading it may stop at "
                                             "the first"))
                continue
            try:
                ja = None if a is None else json.loads(a.decode("utf-8"))
                jb = json.loads(b.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                out.append((rel, [], "changed (it is not valid JSON)"))
                continue
            if ja is None:
                out.append((rel, [], "the file is new"))
                continue
            found = []
            _json_changes(ja, jb, [], found)
            out.extend((rel, p, w) for p, w in found)
            continue
        old = [] if a is None else a.decode("utf-8", "replace").splitlines()
        new = b.decode("utf-8", "replace").splitlines()
        if a is None:
            out.append((rel, [], "the file is new, %d line(s):" % len(new)))
        for line in difflib.ndiff(old, new):
            if line[:2] in ("+ ", "- ") and line[2:].strip():
                out.append((rel, [], ("added line:   " if line[0] == "+" else "removed line: ") + line[2:]))
    return out


# ---------------------------------------------------------------- the birth hash, computed without git

# The double-click launchers at the top of the folder (README.md). The macOS ones (.command) must be executable to
# open on a double-click, so they are kept with git's mode 100755; the Windows ones (.cmd) keep CRLF line endings.
LAUNCHERS = ("Found-an-organization.cmd", "Found-an-organization.command", "Start-a-member.cmd",
             "Start-a-member.command", "Close-out.cmd", "Close-out.command")


def is_executable_path(rel):
    """Files the seed keeps with git's mode 100755, however the copy at hand was made (a ZIP keeps no modes)."""
    return rel.endswith(".command")


def canonical_bytes(rel, data):
    """A file's bytes as the seed commits them: CRLF line endings for Windows launchers (.cmd), LF for the rest."""
    data = data.replace(b"\r\n", b"\n")
    return data.replace(b"\n", b"\r\n") if rel.lower().endswith(".cmd") else data


def git_tree_id(files, executable=()):
    """Git's tree id for {relative path: bytes}, computed in Python (plain files: mode 100644, or 100755 for the
    paths in executable)."""
    executable = set(executable)
    tree = {}
    for rel, data in files.items():
        parts = rel.split("/")
        node = tree
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = (rel, data)

    def build(node):
        entries = []
        for name, v in node.items():
            if isinstance(v, dict):
                entries.append((name.encode() + b"/", b"40000 " + name.encode() + b"\0" + bytes.fromhex(build(v))))
            else:
                rel, data = v
                blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
                mode = b"100755 " if rel in executable else b"100644 "
                entries.append((name.encode(), mode + name.encode() + b"\0" + bytes.fromhex(blob)))
        body = b"".join(e[1] for e in sorted(entries, key=lambda e: e[0]))
        return hashlib.sha1(b"tree %d\0" % len(body) + body).hexdigest()
    return build(tree)


# ---------------------------------------------------------------- research configurations (for studies only)

STUDY_FILE = "org/STUDY.json"
# What a study may switch off, and exactly how. Nothing in the record-keeping core is switchable: the
# record a study scores from has to exist in the same form under every condition.
STUDY_SWITCHES = {
    "CORE-13": {
        "about": "the core claim rule (facts sourced or marked lead) and its checks: claims lines for citations, "
                 "and CK-1's quotation checks",
        "replace": [
            ("onboarding/START.md",
             "such as a few sources on the founder's question, each saved in `sources/` with a line in "
             "`records/claims.jsonl`.",
             "such as a few sources on the founder's question."),
            ("onboarding/START.md",
             "If something fails (a claim with no source, a quotation that differs from its source, a conclusion "
             "broader than its evidence), leave it out,",
             "If something fails (the work breaks a rule in force), leave it out,"),
            ("onboarding/START.md",
             " What you remember is never a source: a name, date, number or quotation you recall stays a lead until "
             "its source is saved and the words are found in it.",
             ""),
        ],
    },
}


def remove_core_rule(text, rule_id):
    """AGENTS.md without one core rule: its bullet and the lines under it, up to the next bullet or heading."""
    out, skipping = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith("- **%s." % rule_id):
            skipping = True
            continue
        if skipping and (line.startswith("- **") or line.startswith("#") or not line.strip()):
            skipping = False
        if not skipping:
            out.append(line)
    return "".join(out)


def study_transform(texts, switch_off):
    """The seed's files as a research configuration has them. texts: {path: text}. Returns the changed ones."""
    out = {}
    for rid in switch_off:
        spec = STUDY_SWITCHES[rid]
        out["AGENTS.md"] = remove_core_rule(out.get("AGENTS.md", texts["AGENTS.md"]), rid)
        for rel, old, new in spec["replace"]:
            cur = out.get(rel, texts[rel])
            if old not in cur:
                raise RecordError("the research configuration expects text in %s that is not there" % rel)
            out[rel] = cur.replace(old, new)
    return out


def study_config():
    """(the study configuration, None) when org/STUDY.json was made by fos_init in the commit right after the
    birth; (None, why) when it is present but cannot be confirmed; (None, None) when there is none."""
    data = read_bytes(STUDY_FILE)
    if data is None:
        return None, None
    if not (git_ok() and has_head()):
        return None, ("org/STUDY.json is present, but without git it cannot be confirmed as made at birth, so every "
                      "rule stays on")
    born, bcommit = birth_from_git()
    code, out = git("rev-list", "--reverse", "--ancestry-path", "%s..HEAD" % bcommit) if bcommit else (1, "")
    child = out.split()[0] if code == 0 and out.split() else None
    subject = git("log", "-1", "--format=%s", child)[1] if child else ""
    made = head_bytes(STUDY_FILE, child) if child and subject.startswith("[STUDY]") else None
    if made is None or made.replace(b"\r\n", b"\n") != data.replace(b"\r\n", b"\n"):
        return None, ("org/STUDY.json was not made by fos_init at birth (or was changed since), so it switches "
                      "nothing off")
    try:
        cfg = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None, "org/STUDY.json cannot be read"
    cfg["_commit"] = child
    return cfg, None


def claim_rule_on():
    study, _ = study_config()
    return not (study and "CORE-13" in (study.get("switch_off") or []))


# ---------------------------------------------------------------- decisions, signatures, adoption

def human_instances(cfg):
    return {i for i, (r, _) in instances(cfg).items() if r.get("kind") == "human"}


def founder_instances(cfg):
    return {i for i, (r, _) in instances(cfg).items() if r.get("id") == "founder" and r.get("kind") == "human"}


def instance_role(cfg):
    return {i: r.get("id") for i, (r, _) in instances(cfg).items()}


def effective_decisions(decisions):
    """Decisions minus those replaced by a later decision that corrects a recording error."""
    replaced = {d.get("corrects") for d in decisions if d.get("corrects")}
    return [d for d in decisions if d.get("id") not in replaced]


def authorized_decisions(cfg, decisions):
    """IDs of decisions that adopt something and were made by someone holding the right."""
    founders = founder_instances(cfg)
    roles = instance_role(cfg)
    by_founder = {d.get("id") for d in decisions
                  if d.get("verdict") in ("adopted", "amended") and d.get("decider_kind") == "human"
                  and d.get("decided_by") in founders}
    ok = set(by_founder)
    for d in decisions:
        if d.get("id") in ok or d.get("verdict") not in ("adopted", "amended"):
            continue
        for g in cfg.get("decision_rights", {}).get("delegated", []):
            if g.get("right") == d.get("right") and g.get("to") == roles.get(d.get("decided_by")) \
                    and g.get("adopted_by") in by_founder:
                ok.add(d.get("id"))
    return ok


PENDING_OWN_SIGNATURES = set()   # seqs a running close-out has just written and is about to commit


def counted_signature_seqs(sig_parsed):
    """Which signature lines may count. With git: only lines already committed (a line that appeared
    since the last close-out was not written by a close-out that finished), plus those the running
    close-out wrote itself. Without git: the lines in the witness's last snapshot. With neither: all
    lines, and the check says they cannot be verified."""
    seqs, how = _counted_signature_seqs(sig_parsed)
    return seqs | PENDING_OWN_SIGNATURES, how


def _counted_signature_seqs(sig_parsed):
    if git_ok() and has_head():
        data = head_bytes(RECORD_FILES["signature"])
        if data is None:
            return set(), "git"
        seqs = set()
        for raw in data.split(b"\n"):
            try:
                o = json.loads(raw)
                if isinstance(o, dict) and isinstance(o.get("seq"), int):
                    seqs.add(o["seq"])
            except ValueError:
                pass
        return seqs, "git"
    w = find_witness() or ({"folder": default_witness_folder()} if os.path.isdir(default_witness_folder()) else None)
    snap = W.latest_snapshot(w["folder"]) if w else None
    if snap and os.path.exists(os.path.join(snap, "signatures.jsonl")):
        seqs = set()
        with open(os.path.join(snap, "signatures.jsonl"), "rb") as f:
            for raw in f.read().split(b"\n"):
                try:
                    o = json.loads(raw)
                    if isinstance(o, dict) and isinstance(o.get("seq"), int):
                        seqs.add(o["seq"])
                except ValueError:
                    pass
        return seqs, "snapshot"
    return {o.get("seq") for o in sig_parsed.objs}, "unverified"


def signature_state(cfg, records, counted=None):
    """Return (status by decision id, problems). status: 'signed' | 'refused'.

    A signature counts only if: written by the close-out script; by the founder; for a decision that
    exists, whose line still has the hash that was signed; in terminal mode (test mode counts only inside
    the seed's self-test); and committed or snapshotted (see counted_signature_seqs). The latest wins.
    """
    status, problems = {}, []
    decisions = {o.get("id"): (raw, o) for _, raw, o in records["decision"].rows}
    founders = founder_instances(cfg)
    allow_test = os.environ.get("SEED_SELFTEST") == "1"
    if counted is None:
        counted, _ = counted_signature_seqs(records["signature"])
    voided = void_signature_seqs(records["event"].objs)
    for _, raw, s in records["signature"].rows:
        sid, did = s.get("id"), s.get("decision_id")
        if s.get("seq") in voided:
            continue
        if s.get("captured_by") != "close_script":
            problems.append(("FAIL", "signature %s was not written by the close-out script; it does not count" % sid))
            continue
        if did not in decisions:
            problems.append(("FAIL", "signature %s names decision %s, which does not exist" % (sid, did)))
            continue
        draw, dobj = decisions[did]
        if s.get("decision_sha256") != line_sha256(draw) or s.get("decision_seq") != dobj.get("seq"):
            problems.append(("FAIL", "signature %s does not match decision %s as it now reads: the decision line "
                                     "changed after it was signed" % (sid, did)))
            continue
        if s.get("signer") not in founders:
            problems.append(("FAIL", "signature %s is by '%s', who is not the founder" % (sid, s.get("signer"))))
            continue
        if s.get("mode") == "test" and not allow_test:
            problems.append(("WARN", "signature %s was made in test mode; it signs nothing in a real organization" % sid))
            continue
        if s.get("seq") not in counted:
            problems.append(("WARN", "signature %s is not yet committed; it counts once the close-out commit "
                                     "exists" % sid))
            continue
        status[did] = s.get("answer")
    return status, problems


def adoption(cfg, records, counted=None):
    """Return a dict: signed (adopted and signed), awaiting (authorized, not yet signed), refused,
    sig_status, sig_problems, decisions (effective)."""
    decisions = effective_decisions(records["decision"].objs)
    authorized = authorized_decisions(cfg, decisions)
    sig, sig_problems = signature_state(cfg, records, counted)
    return {"signed": {d for d in authorized if sig.get(d) == "signed"},
            "awaiting": {d for d in authorized if d not in sig},
            "refused": {d for d, a in sig.items() if a == "refused"},
            "sent_back": {d for d, a in sig.items() if a == "sent_back"},
            "sig_status": sig, "sig_problems": sig_problems, "decisions": decisions}


def proposal_status(records, ad):
    """Each proposal's standing, derived from decisions and signatures (proposals carry no status field):
      adopted / declined  a decision the founder signed settled it;
      awaiting            a decision names it and waits for the founder's signature;
      open                no decision yet, or only decisions the founder refused, sent back, or that deferred it.
    Returns ({proposal id: standing}, {proposal id: why it is open again})."""
    status = {p.get("id"): "open" for p in records["proposal"].objs}
    why = {}
    sig = ad["sig_status"]
    waiting = {d.get("id") for _, _, d in unanswered_decisions(records)}
    for d in ad["decisions"]:
        did, verdict, answer = d.get("id"), d.get("verdict"), sig.get(d.get("id"))
        for pid in d.get("proposal_ids") or []:
            if pid not in status:
                continue
            if answer == "signed":
                status[pid] = {"adopted": "adopted", "amended": "adopted", "declined": "declined"}.get(verdict, "open")
                why.pop(pid, None)
            elif answer in ("refused", "sent_back"):
                if status[pid] in ("open", "awaiting"):
                    status[pid] = "open"
                    why[pid] = "the founder %s %s" % ("did not sign" if answer == "refused" else "sent back", did)
            elif did in waiting and status[pid] == "open":
                status[pid] = "awaiting"
    return status, why


STRUCTURAL_PROPOSAL_KINDS = {"module", "role", "role_instance", "model_slot", "rule", "check", "tool", "charter",
                             "decision_right", "records_policy", "view"}


ADOPTING_VERDICTS = ("adopted", "amended")
ADOPTING_TEXTS = ("org/OUR_RULES.md", "org/NORMS.md", "org/CHARTER.md")
_ADOPTED_BY_LINE = re.compile(r"^adopted_by:\s*(\S+)\s*$")


def structure_by_decision(cfg, tools=None, views=None):
    """What the organization's files name each decision as adopting: {decision ID: ["module 'memory'", ...]}. It is
    read from what the files say (every structural item's adopted_by in org/config.json, the tool registry and the
    view; the entries of OUR_RULES.md, NORMS.md and CHARTER.md; the records policy), never from a proposal's kind: a
    decision adopts structure if it changes structure, whatever its proposals are called."""
    out = {}
    for kind, label, ab in structural_items(cfg, tools, views):
        if isinstance(ab, str) and ab not in ("core", "seed"):
            out.setdefault(ab, []).append("%s '%s'" % (kind, label))
    for rel in ADOPTING_TEXTS:
        for e in parse_entries(read_text(rel, "")):
            if e.get("adopted_by"):
                out.setdefault(e["adopted_by"], []).append("%s %s (%s)" % (e["id"], e.get("title", ""), rel))
    text, comment = read_text("org/RECORDS_POLICY.md", "") or "", False
    for line in text.splitlines():
        if comment or line.strip().startswith("<!--"):
            comment = "-->" not in line
            continue
        m = _ADOPTED_BY_LINE.match(line.strip())
        if m:
            out.setdefault(m.group(1), []).append("the records policy (org/RECORDS_POLICY.md)")
    return out


def founding_candidate(cfg, todo):
    """Which waiting decision the close-out puts to the founder as the founding: the one org/config.json names
    (organization.founding_decision), else the latest one recorded with founding: true. todo: [(line, raw, decision)].
    The pointer only picks what is shown at the founding prompt: the organization is founded only if the founder types
    FOUND there (founding_state). Returns (raw, decision) or None."""
    named = cfg.get("organization", {}).get("founding_decision")
    for _, raw, d in todo:
        if named and d.get("id") == named:
            return raw, d
    marked = [(raw, d) for _, raw, d in todo if d.get("founding") is True]
    return marked[-1] if marked else None


def structural_proposals(d, props):
    """The proposals a decision names whose kind is structural."""
    return [pid for pid in d.get("proposal_ids") or [] if (props.get(pid) or {}).get("kind") in STRUCTURAL_PROPOSAL_KINDS]


def early_adoptions(cfg, records, ad, fs, tools=None, views=None):
    """Decisions whose labels or effects adopt structure before the founding: a structural proposal kind, or an item the
    files name as adopted by it (structure_by_decision). For warnings only: what enforces the founding is the history
    (fos_witness.founding_history), where no structure is committed before the founder founds the organization at a
    close-out. fs is founding_state(). Before the founding, the decision put to the founder as the founding (founding:
    true, or named in config.json) is left out. Returns [(decision, [what it adopts])]."""
    props = {p.get("id"): p for p in records["proposal"].objs}
    by = structure_by_decision(cfg, tools, views)
    seqs = {d.get("id"): d.get("seq") for d in ad["decisions"]}
    fd, named = fs.get("decision"), cfg.get("organization", {}).get("founding_decision")
    out = []
    for d in ad["decisions"]:
        did = d.get("id")
        if did == fd or d.get("verdict") not in ADOPTING_VERDICTS:
            continue
        if fs.get("founded"):
            if not (isinstance(d.get("seq"), int) and isinstance(seqs.get(fd), int) and d["seq"] < seqs[fd]):
                continue
        elif d.get("founding") is True or did == named:
            continue
        what = structural_proposals(d, props) + by.get(did, [])
        if what and ad["sig_status"].get(did) not in ("refused", "sent_back"):
            out.append((d, what))
    return out


def effect_items(cfg, decision_id, tools=None, views=None):
    """The structural items, as (kind, label), that a decision adopts."""
    return [(kind, label) for kind, label, ab in structural_items(cfg, tools, views) if ab == decision_id]


def effects_of(cfg, decision_id, tools=None, views=None):
    """What signing a decision makes part of the organization: every item whose adopted_by names it."""
    out = []
    for kind, label, ab in structural_items(cfg, tools, views):
        if ab == decision_id:
            out.append("%s '%s'" % (kind, label))
    if cfg.get("organization", {}).get("founding_decision") == decision_id:
        out.insert(0, "founds the organization")
    for rel in ("org/OUR_RULES.md", "org/NORMS.md", "org/CHARTER.md"):
        for e in parse_entries(read_text(rel, "")):
            if e.get("adopted_by") == decision_id:
                out.append("%s %s (%s)" % (e["id"], e.get("title", ""), rel))
    return out


def void_signature_seqs(events):
    return {(e.get("corrects") or {}).get("seq") for e in events
            if e.get("type") == "record_correction" and e.get("captured_by") == "close_script"
            and str((e.get("corrects") or {}).get("file", "")).endswith("signatures.jsonl")}


def unanswered_decisions(records):
    """Decision rows (line, raw, obj) with no signature line, signed or not, from a close-out (void ones aside)."""
    voided = void_signature_seqs(records["event"].objs)
    answered = {s.get("decision_id") for s in records["signature"].objs
                if s.get("captured_by") == "close_script" and s.get("seq") not in voided}
    effective = effective_decisions(records["decision"].objs)
    return [(ln, raw, d) for ln, raw, d in records["decision"].rows if d in effective and d.get("id") not in answered]


SEED_ITEMS = {
    ("role", "founder"), ("role", "member"), ("role", "drill"),
    ("role instance", "founder/founder"), ("role instance", "member/member-1"), ("role instance", "drill/drill-1"),
    ("view", "view/VIEWS.json"),
}
SEED_TOOLS = {"fos_check", "fos_claims", "fos_close", "fos_crate", "fos_drill", "fos_export", "fos_init", "fos_lib", "fos_log",
              "fos_launch", "fos_render", "fos_roles", "fos_rules", "fos_selftest", "fos_sync", "fos_witness", "rename",
              "release_export"}


def governed(adopted_by, ok_ids, kind=None, label=None):
    """True if the item is part of the organization (not merely proposed)."""
    if adopted_by in ("core", "seed"):
        return kind is None or (kind, label) in SEED_ITEMS or (kind == "tool" and label in SEED_TOOLS)
    return adopted_by in ok_ids


def structural_items(cfg, tools=None, views=None):
    """Yield (kind, label, adopted_by) for every structural item."""
    for m in cfg.get("modules", []):
        if m.get("state") == "on":
            yield ("module", m.get("id"), m.get("adopted_by"))
    for r in cfg.get("roles", []):
        yield ("role", r.get("id"), r.get("adopted_by"))
        for inst in r.get("instances", []):
            yield ("role instance", "%s/%s" % (r.get("id"), inst.get("id")), inst.get("adopted_by"))
    for c in cfg.get("checks", []):
        yield ("check", c.get("id"), c.get("adopted_by"))
    for g in cfg.get("decision_rights", {}).get("delegated", []):
        yield ("delegated right", "%s -> %s" % (g.get("right"), g.get("to")), g.get("adopted_by"))
    for r in cfg.get("retired_roles", []):
        yield ("retired role", r.get("id"), r.get("retired_by"))
    for t in (tools if tools is not None else tools_registry()).get("tools", []):
        if t.get("status") not in ("proposed", "retired"):
            yield ("tool", t.get("id"), t.get("adopted_by"))
    if views is None:
        try:
            views = load_json("view/VIEWS.json")
        except (OSError, ValueError):
            views = None
    if views:
        yield ("view", "view/VIEWS.json", views.get("adopted_by"))


def modules_in_force(cfg, ok_ids):
    return [m.get("id") for m in cfg.get("modules", [])
            if m.get("state") == "on" and governed(m.get("adopted_by"), ok_ids, "module", m.get("id"))]


# ---------------------------------------------------------------- stage

def stage(cfg, events):
    """'seed', 'born' or 'founded', decided from the history and the witness (stage_info)."""
    return stage_info(cfg, events)["stage"]


# ---------------------------------------------------------------- decision words (CORE-3)

GENERIC_TOKENS = set("""ok okay k kk yes yeah yep yup ya sure fine great good cool nice perfect thanks thank you
sounds sound looks look go ahead agreed agree absolutely awesome excellent love it right correct lgtm do for
why not of course alright all wonderful brilliant amazing fantastic indeed totally definitely sweet super
please that this works work me to oh wow yay sgtm""".split())


def normalize_words(words):
    return " ".join(re.sub(r"[^0-9a-z]+", " ", (words or "").lower()).split())


def is_generic_reply(words):
    toks = normalize_words(words).split()
    return bool(toks) and all(t in GENERIC_TOKENS for t in toks)


# ---------------------------------------------------------------- citations (CORE-13)

CITATION_PATTERNS = [
    ("URL", re.compile(r"https?://[^\s<>\"')\]]+")),
    ("DOI", re.compile(r"\b10\.\d{4,9}/[^\s<>\"')\]]+")),
    ("arXiv", re.compile(r"\barXiv:\s?\d{4}\.\d{4,5}(?:v\d+)?", re.I)),
    ("ISBN", re.compile(r"\bISBN(?:-1[03])?:?\s?[0-9][0-9 -]{8,16}[0-9Xx]")),
]


def citations_in(text):
    found = []
    for kind, rx in CITATION_PATTERNS:
        for m in rx.finditer(text):
            found.append((kind, m.group(0).rstrip(".,;:")))
    return found


# ---------------------------------------------------------------- CK-1: quotations against their sources (the checker's mechanical core)

_TYPO = {"‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'", "“": '"', "”": '"',
         "„": '"', "″": '"', "–": "-", "—": "-", "−": "-", " ": " ", " ": " ",
         " ": " ", "…": "...", "­": ""}
TEXT_SOURCES = (".md", ".txt", ".rst", ".html", ".htm", ".json", ".jsonl", ".csv", ".tsv", ".xml", ".tex", ".yaml",
                ".yml", ".bib")


def normalize_quote_text(s, join_broken_words=False):
    """Typographic quotes, dashes and spaces made plain; spaces collapsed. A word hyphenated across a line break
    keeps its hyphen, or (join_broken_words) loses it: "infor-\\nmation" -> "information"."""
    s = "".join(_TYPO.get(c, c) for c in (s or ""))
    s = re.sub(r"(\w)-[ \t]*\r?\n\s*(\w)", r"\1\2" if join_broken_words else r"\1-\2", s)
    return " ".join(s.split())


def source_text(rel):
    """(text, None) for a saved source the check can read, or (None, why not). A PDF or other binary file is
    read through a text copy saved beside it with the same name and .txt."""
    data = read_bytes(rel)
    if data is None:
        return None, "missing"
    low = rel.lower()
    if not low.endswith(TEXT_SOURCES) or b"\0" in data[:4096]:
        stem = rel.rsplit(".", 1)[0]
        alt = read_bytes(stem + ".txt")
        if alt is None:
            return None, "binary"
        data, low = alt, stem + ".txt"
    text = data.decode("utf-8", errors="replace")
    if low.endswith((".html", ".htm", ".xml")):
        import html as _html
        text = _html.unescape(re.sub(r"<[^>]+>", " ", text))
    return text, None


def quote_found(quote, text):
    """'exact' | 'ignoring_case' | 'missing'. A quotation with an ellipsis must match each part, in order."""
    parts = [p.strip() for p in re.split(r"\[\s*\.\.\.\s*\]|\.\.\.", normalize_quote_text(quote)) if p.strip(" .,;:")]
    hays = [normalize_quote_text(text), normalize_quote_text(text, join_broken_words=True)]

    def in_order(h, ps):
        at = 0
        for p in ps:
            i = h.find(p, at)
            if i < 0:
                return False
            at = i + len(p)
        return True
    if parts and any(in_order(h, parts) for h in hays):
        return "exact"
    if parts and any(in_order(h.casefold(), [p.casefold() for p in parts]) for h in hays):
        return "ignoring_case"
    return "missing"


def file_sha256(rel):
    data = read_bytes(rel)
    return hashlib.sha256(data).hexdigest() if data is not None else None


def claim_checks(records):
    """CK-1 on every claim: [(level, claim id, message)] with level FAIL or WARN. A verified claim needs its
    saved source, and its quotation must occur in that source. A claim that a record_correction points to stays
    on record; its problems are then warnings (a corrected defect), not failures."""
    corrected = set()
    for e in records["event"].objs:
        cor = e.get("corrects")
        if e.get("type") == "record_correction" and isinstance(cor, dict) and isinstance(cor.get("seq"), int) \
                and str(cor.get("file", "")).replace("\\", "/").endswith("claims.jsonl"):
            corrected.add(cor["seq"])
    out = []
    for c in records["claim"].objs:
        cid, status, sf, q = c.get("id"), c.get("status"), c.get("source_file") or "", c.get("quote") or ""
        if status != "verified":
            continue
        if c.get("seq") in corrected:
            before = len(out)
            out.extend(_claim_problems(c, cid, sf, q))
            out[before:] = [("WARN", i, "corrected defect: " + m) for _, i, m in out[before:]]
            continue
        out.extend(_claim_problems(c, cid, sf, q))
    return out


def _claim_problems(c, cid, sf, q):
    """The CK-1 findings for one verified claim."""
    if not sf or read_bytes(sf) is None:
        return [("FAIL", cid, "claim %s is marked verified, but its source file %r is not in the folder" % (cid, sf))]
    out = []
    if c.get("source_sha256") and c["source_sha256"] != file_sha256(sf):
        out.append(("WARN", cid, "claim %s: %s changed since the claim was recorded (its SHA-256 differs); check the "
                                 "claim against the source again" % (cid, sf)))
    if not q:
        return out + [("WARN", cid, "claim %s is marked verified but gives no quotation, so CK-1 cannot check it "
                                    "against %s" % (cid, sf))]
    text, why = source_text(sf)
    if text is None:
        return out + [("WARN", cid, "claim %s: %s cannot be read as text, so its quotation is unchecked; save a text "
                                    "copy beside it (same name, .txt)" % (cid, sf))]
    found = quote_found(q, text)
    if found == "missing":
        out.append(("FAIL", cid, "QUOTE NOT IN SOURCE: claim %s quotes \"%s\", which does not occur in %s (CK-1)"
                                 % (cid, q[:120], sf)))
    elif found == "ignoring_case":
        out.append(("WARN", cid, "claim %s: its quotation occurs in %s only if letter case is ignored" % (cid, sf)))
    return out


_QUOTED = re.compile(r"“([^”]+)”|\"([^\"\n]+)\"")


def quoted_passages(text, min_words=4):
    """(line number, passage) for each passage of at least min_words words in quotation marks, outside code."""
    out, fenced, comment = [], False, False
    for n, line in enumerate((text or "").splitlines(), 1):
        if comment:
            comment = "-->" not in line
            continue
        if line.strip().startswith("<!--"):
            comment = "-->" not in line
            continue
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        for m in _QUOTED.finditer(re.sub(r"`[^`]*`", "", line)):
            q = (m.group(1) or m.group(2) or "").strip()
            if len(q.split()) >= min_words:
                out.append((n, q))
    return out


def founder_words(cfg, records, ad=None):
    """Text the founder said or adopted: GOAL.md, the founder's recorded replies and notes, records written by the
    founder, and the change text of proposals adopted by a signed decision."""
    ad = ad or adoption(cfg, records)
    founders = founder_instances(cfg)
    parts = [read_text("org/GOAL.md", "") or ""]
    signed = ad["signed"]
    adopted = set()
    for d in ad["decisions"]:
        if d.get("decided_by") in founders:
            parts += [d.get("words") or "", d.get("amendment") or ""]
        if d.get("id") in signed:
            adopted.update(d.get("proposal_ids") or [])
            parts.append(d.get("amendment") or "")
    for p in records["proposal"].objs:
        if p.get("id") in adopted:
            parts.append(p.get("change") or "")
    for s in records["signature"].objs:
        parts.append(s.get("note") or "")
    for kind, p in records.items():
        for o in p.objs:
            if o.get("captured_by") == "founder":
                parts += [v for v in o.values() if isinstance(v, str)]
    return "\n".join(parts)


ORG_TEXTS = ("org/CHARTER.md", "org/STATE.md", "org/LETTER_TO_NEXT_SESSION.md", "org/OUR_RULES.md", "org/NORMS.md",
             "org/DESIGN_AHEAD.md", "org/RECORDS_POLICY.md")


SEED_TEXT_AREAS = ("AGENTS.md", "README.md", "onboarding", "modules", "docs")


def seed_texts():
    """The seed's own text for people and members (AGENTS.md, README.md, onboarding/, modules/, docs/), as the
    organization was born with it (its first commit), or as it is on disk where git cannot be used.
    Returns [(path, text)]. CK-1 uses it to tell a quotation of the seed from a misquotation of the founder."""
    root = root_commit() if git_ok() and has_head() else None
    if root:
        code, listing = git("ls-tree", "-r", "-z", root, "--", *SEED_TEXT_AREAS)
        entries = []
        for item in (listing.split("\0") if code == 0 else []):
            meta, _, rel = item.partition("\t")
            parts = meta.split()
            if len(parts) == 3 and parts[1] == "blob" and rel.lower().endswith(".md"):
                entries.append((rel, parts[2]))
        try:
            blobs = W.read_blobs(["-C", ROOT], [sha for _, sha in entries])
            return [(rel, blobs[sha].decode("utf-8", "replace")) for rel, sha in entries if sha in blobs]
        except W.GitError:
            pass
    out = []
    for area in SEED_TEXT_AREAS:
        p = path(area)
        if os.path.isfile(p):
            out.append((area, read_text(area, "")))
            continue
        for d, _, fs in os.walk(p):
            for fn in sorted(fs):
                if fn.lower().endswith(".md"):
                    rel = os.path.relpath(os.path.join(d, fn), ROOT).replace("\\", "/")
                    out.append((rel, read_text(rel, "")))
    return out


_WORD = re.compile(r"[0-9a-z]+(?:'[0-9a-z]+)*")


def quote_words(s):
    return _WORD.findall(normalize_quote_text(s).casefold())


def _word_lines(texts):
    """[(file, line, words)] for every line of [(file, text)] with at least two words."""
    out = []
    for rel, text in texts:
        for line in (text or "").splitlines():
            w = quote_words(line)
            if len(w) >= 2:
                out.append((rel, line.strip(), w))
    return out


def longest_word_run(words, lines):
    """The longest run of `words` found adjacent and in order within one of `lines` (from _word_lines):
    (length, file, line)."""
    best, where = 0, (None, None)
    for rel, line, h in lines:
        pos = {}
        for j, w in enumerate(h):
            pos.setdefault(w, []).append(j)
        for i, w in enumerate(words):
            for j in pos.get(w, ()):
                k = 0
                while i + k < len(words) and j + k < len(h) and words[i + k] == h[j + k]:
                    k += 1
                if k > best:
                    best, where = k, (rel, line)
    return best, where[0], where[1]


SEED_QUOTE_MIN_WORDS = 4        # a run at least this long ...
SEED_QUOTE_SHARE = 0.75         # ... covering at least this share of the passage's words


def org_quote_checks(cfg, records, ad=None):
    """CK-1, second half: a passage quoted in the organization's own files (org/) must be something the founder
    said or adopted, or occur in a saved source, or be the seed's own text (an interview question, say).
    Returns [(level, file, line, passage, seed file, seed line)]:
      FAIL  it matches nothing the founder said or adopted, no saved source, and not the seed's own text;
      WARN  it is close to the seed's own words, and closer to them than to the founder's: a quotation of the
            seed that is not exact, not a misquotation of the founder.
    A passage that is exactly the founder's, a source's or the seed's own text gives no line."""
    corpus = [founder_words(cfg, records, ad)]
    for c in records["claim"].objs:
        corpus.append(c.get("quote") or "")
    for d, _, fs in os.walk(path("sources")):
        for fn in fs:
            text, _ = source_text(os.path.relpath(os.path.join(d, fn), ROOT).replace("\\", "/"))
            if text:
                corpus.append(text)
    hay = "\n".join(corpus)
    pending = [(rel, n, q) for rel in ORG_TEXTS for n, q in quoted_passages(read_text(rel, ""))
               if quote_found(q, hay) == "missing"]
    if not pending:
        return []
    seeds = seed_texts()
    seed_hay = "\n".join(t for _, t in seeds)
    seed_lines, own_lines = _word_lines(seeds), _word_lines([("", hay)])
    out = []
    for rel, n, q in pending:
        if quote_found(q, seed_hay) != "missing":
            continue                      # the seed's own words, quoted exactly
        words = quote_words(q)
        run, sfile, sline = longest_word_run(words, seed_lines)
        own, _, _ = longest_word_run(words, own_lines)
        if words and run >= SEED_QUOTE_MIN_WORDS and run >= SEED_QUOTE_SHARE * len(words) and run > own:
            out.append(("WARN", rel, n, q, sfile, sline))
        else:
            out.append(("FAIL", rel, n, q, None, None))
    return out


def founder_quote_checks(cfg, records, ad=None):
    """The passages quoted in org/ that CK-1 fails: [(file, line, passage)] (see org_quote_checks)."""
    return [(rel, n, q) for level, rel, n, q, _, _ in org_quote_checks(cfg, records, ad) if level == "FAIL"]


# ---------------------------------------------------------------- rules in Markdown: "### ID Title" then "field: value" lines

_HEAD = re.compile(r"^###\s+(\S+)(?:\s+(.*))?$")
_FIELD = re.compile(r"^([a-z_]+):\s?(.*)$")


def parse_entries(text):
    """Parse '### ID Title' entries and their 'field: value' lines; fenced blocks and comments are skipped."""
    entries, cur, fenced, comment = [], None, False, False
    for line in (text or "").splitlines():
        if comment:
            comment = "-->" not in line
            continue
        if line.strip().startswith("<!--"):
            comment = "-->" not in line
            continue
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = _HEAD.match(line)
        if m:
            cur = {"id": m.group(1), "title": (m.group(2) or "").strip()}
            entries.append(cur)
            continue
        if line.startswith("## ") or line.startswith("# "):
            cur = None
            continue
        if cur is not None:
            f = _FIELD.match(line.strip())
            if f:
                cur[f.group(1)] = f.group(2).strip()
    return entries


def module_rules(module_id):
    return parse_entries(read_text("modules/%s/MODULE.md" % module_id, ""))


def module_title_line(module_id):
    m = re.search(r"\*\*For\.\*\*\s*(.+)", read_text("modules/%s/MODULE.md" % module_id, ""))
    return m.group(1).strip() if m else ""


def core_rule_ids():
    return re.findall(r"\*\*(CORE-\d+)\.", read_text("AGENTS.md", ""))


# ---------------------------------------------------------------- roles: triggers, heartbeat, roll-call

TRIGGER_KINDS = ("session_start", "close_out", "event", "every_n_sessions", "founder_call", "schedule")


def role_heartbeats(cfg, events):
    """Map role id -> session of the last event showing the role ran (its instance wrote it, or a
    role_ran event names the role)."""
    inst_to_role = instance_role(cfg)
    role_ids = {r.get("id") for r in cfg.get("roles", [])}
    last = {}
    for e in events:
        roles = set()
        who = (e.get("identity") or {}).get("instance")
        if who in inst_to_role and e.get("type") != "role_ran":
            roles.add(inst_to_role[who])
        if e.get("type") == "role_ran":
            roles.update(r for r in (e.get("refs") or []) if r in role_ids)
        for r in roles:
            last[r] = e.get("session")
    return last


def role_rollcall(cfg, events):
    """Each role: trigger, expected interval, last session run, sessions since, and a status:
    ok | due | stale | never | exempt | no_trigger. Sessions are counted by their starts and their close-outs,
    so sessions that nobody recorded still count toward a role being due."""
    sessions = counted_sessions(events)
    beats = role_heartbeats(cfg, events)
    default = cfg.get("settings", {}).get("default_expected_every_sessions", 5)
    out = []
    for r in cfg.get("roles", []):
        trig = r.get("trigger") or {}
        exp = r.get("expected_every_sessions", default) if "expected_every_sessions" in r else default
        last = beats.get(r.get("id"))
        since = len(sessions) - 1 - sessions.index(last) if last in sessions else None
        if not trig.get("on"):
            st = "no_trigger"
        elif exp is None:
            st = "exempt"
        elif last is None:
            st = "never" if len(sessions) >= (exp or 1) else "ok"
        elif since is not None and since >= exp:
            st = "stale"
        elif since is not None and since == exp - 1 and exp > 1:
            st = "due"
        else:
            st = "ok"
        out.append({"role": r.get("id"), "title": r.get("title", r.get("id")), "trigger": trig, "expected": exp,
                    "last_session": last, "sessions_since": since, "status": st})
    return out
