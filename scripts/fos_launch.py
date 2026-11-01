"""Launch a member: the founder says which instance an agent app will be, and on what. Run it yourself.

Usage (the founder, in an ordinary terminal, before starting an agent app on this organization):
  python scripts/fos_launch.py <instance>                 asks for the model and the rest
  python scripts/fos_launch.py <instance> --model-id ID --producer P --agent-app A --host H
                                          [--agent-app-version V] [--model-snapshot S]
  python scripts/fos_launch.py <instance> ... --file      also write .fos_launch.json in this folder
  python scripts/fos_launch.py <instance> ... --app-instructions <file or folder> [...]
                                          also record the SHA-256 of the agent app's own instruction and
                                          configuration files for this launch (their names, never their
                                          content or full paths)
  python scripts/fos_launch.py --list                     the launches recorded so far
  python scripts/fos_launch.py --ask --file               asks which member first (what the double-click
                                                          launcher Start-a-member runs)

Why: a member's own statement of who it is cannot be checked. A launch is the founder's statement,
made before the app starts: this app, in this folder, is instance <instance>, running model ... by
producer ..., in agent app ..., served by host .... It is recorded twice:
  - as an instance_launched event in records/events.jsonl, which members read;
  - in the witness folder (launches/L-nnnn.json), outside the members' reach, with a secret that
    only this launch knows.
The script then prints one line to set in the terminal from which the agent app is started:
FOS_LAUNCH=<launch>:<instance>:<secret>. fos_log reads it and stamps every record that member writes
with a fingerprint (an HMAC-SHA256 of the record, keyed by the secret). The check recomputes each
fingerprint from the witness's copy: a record is then attributed to the launched instance by
something the member did not write. Records without a fingerprint are reported as unverified.

Agent apps that cannot be started from a terminal: --file writes the line into .fos_launch.json
(never committed), which fos_log reads when no FOS_LAUNCH is set. Then only one instance may work at a
time, since every member in the folder can read that file. Remove it (or launch again) when another
instance takes over.

The agent app brings instructions of its own (a system prompt, configuration files, plug-ins), which
the folder cannot see. --app-instructions names those files for this launch: each file's name and
SHA-256, and for a folder its name, its number of files and one SHA-256 over their relative paths and
hashes, are recorded in the launch event and in the witness's copy. Their content never is.

The launch says what the founder knows (the model chosen in the app, its producer, the app, the
host). The check compares it with the instance's model slot in org/config.json; a difference is a
change of model in a slot, which is a proposal and a decision.
Like the close-out, it runs only in a terminal (--test-answers is for the seed's self-test).
Standard library only; no network.
"""
import hashlib
import json
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402

TEST = {"answers": None}
FIELDS = (("model_id", "--model-id", "Model ID, exactly as the app or host shows it"),
          ("producer", "--producer", "Producer (who made the model)"),
          ("agent_app", "--agent-app", "Agent app (the program the member runs in)"),
          ("host", "--host", "Host (who serves the model to the app: the producer, a cloud provider, or this machine)"))
OPTIONAL = (("agent_app_version", "--agent-app-version"), ("model_snapshot", "--model-snapshot"))


def ask(prompt, default):
    if TEST["answers"] is not None:
        a = TEST["answers"].pop(0) if TEST["answers"] else ""
        print("%s [%s] %s   [test answer]" % (prompt, default, a))
        return a.strip() or default
    try:
        a = input("%s [%s]: " % (prompt, default)).strip()
    except EOFError:
        a = ""
    return a or default


def opt(argv, flag):
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None


def app_instruction_paths(argv):
    """The paths given after --app-instructions, up to the next flag."""
    if "--app-instructions" not in argv:
        return []
    out = []
    for a in argv[argv.index("--app-instructions") + 1:]:
        if a.startswith("--"):
            break
        out.append(a)
    return out


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def app_instruction_hashes(paths):
    """[{name, sha256}] for files and [{name/, files, sha256}] for folders, or (None, problem). Only names and
    hashes leave this function: never a file's content or its full path."""
    out = []
    for p in paths:
        name = os.path.basename(os.path.normpath(p))
        if os.path.isfile(p):
            out.append({"name": name, "sha256": _sha256_file(p)})
        elif os.path.isdir(p):
            rows = []
            for d, dirs, files in os.walk(p):
                dirs.sort()
                for fn in sorted(files):
                    full = os.path.join(d, fn)
                    rows.append("%s\t%s\n" % (os.path.relpath(full, p).replace(os.sep, "/"), _sha256_file(full)))
            digest = hashlib.sha256("".join(sorted(rows)).encode("utf-8")).hexdigest()
            out.append({"name": name + "/", "files": len(rows), "sha256": digest})
        else:
            return None, "%s is neither a file nor a folder" % p
    return out, None


def launches_folder(create=False):
    w = L.find_witness()
    if not w or not os.path.isdir(w["folder"]):
        return None
    d = os.path.join(w["folder"], "launches")
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def next_launch_id(folder):
    n = 0
    for e in L.read_records(L.RECORD_FILES["event"]).objs:
        v = e.get("launch_id")
        if e.get("type") == "instance_launched" and isinstance(v, str) and v[2:].isdigit():
            n = max(n, int(v[2:]))
    for fn in os.listdir(folder):
        if fn.startswith("L-") and fn.endswith(".json") and fn[2:-5].isdigit():
            n = max(n, int(fn[2:-5]))
    return "L-%04d" % (n + 1)


def list_launches():
    rows = [e for e in L.read_records(L.RECORD_FILES["event"]).objs if e.get("type") == "instance_launched"]
    if not rows:
        print("No launches recorded yet.")
    for e in rows:
        i = e.get("launched") or {}
        print("  %s  %-12s %s by %s, in %s, served by %s (session %s)" % (
            e.get("launch_id"), e.get("launched_instance"), i.get("model_id"), i.get("producer"),
            i.get("agent_app"), i.get("host"), e.get("session")))
    return 0


def main(argv):
    if "--test-answers" in argv:
        TEST["answers"] = [a for a in argv[argv.index("--test-answers") + 1].split("|")]
    if "--list" in argv:
        return list_launches()
    args = [a for a in argv[1:] if not a.startswith("--")]
    flagged = {opt(argv, f) for f in [x[1] for x in FIELDS] + [x[1] for x in OPTIONAL] + ["--test-answers"]}
    instr_paths = app_instruction_paths(argv)
    args = [a for a in args if a not in flagged and a not in instr_paths]
    if not args and "--ask" not in argv:
        print(__doc__)
        return 2
    if TEST["answers"] is None and not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("A launch is the founder's statement of who a member is, so it runs only in a terminal you are typing "
              "in, never from an agent app.")
        return 3
    cfg = L.config()
    if not args:
        ais = L.ai_instances(cfg)
        print("The organization's AI members: %s" % (", ".join(ais) or "none"))
        args = [ask("Which member are you starting", ais[0] if ais else "member-1")]
    instance = args[0]
    found = L.instances(cfg).get(instance)
    if not found:
        print("There is no role instance '%s' in org/config.json (instances: %s). Adding one is a proposal and a "
              "decision." % (instance, ", ".join(sorted(L.instances(cfg)))))
        return 1
    role, inst = found
    if role.get("kind") != "ai":
        print("'%s' is a %s role instance; launches are for AI members." % (instance, role.get("kind")))
        return 1
    folder = launches_folder(create=True)
    if not folder:
        print("A launch is kept in the witness folder, outside the members' reach, and this organization has none "
              "yet. The witness is created by python scripts/fos_init.py, or by the first close-out.")
        return 1
    instructions, problem = app_instruction_hashes(instr_paths)
    if problem:
        print("--app-instructions: %s. Nothing was recorded." % problem)
        return 1
    slot = inst.get("slot") or {}
    stated = {}
    for key, flag, prompt in FIELDS:
        stated[key] = opt(argv, flag) or ask(prompt, slot.get(key) or "unknown")
    for key, flag in OPTIONAL:
        if opt(argv, flag):
            stated[key] = opt(argv, flag)
    stated["model_id_source"] = "founder"
    lid = next_launch_id(folder)
    token = secrets.token_hex(24)
    kept = {"id": lid, "instance": instance, "identity": stated, "token": token, "ts": L.now_utc()}
    event = {"type": "instance_launched", "captured_by": "launch_script", "launch_id": lid,
             "launched_instance": instance, "launched": stated,
             "summary": "The founder launched %s as %s: model %s by %s, in %s, served by %s"
                        % (lid, instance, stated["model_id"], stated["producer"], stated["agent_app"], stated["host"])}
    if instructions:
        kept["app_instructions"] = event["app_instructions"] = instructions
        event["summary"] += "; the app's own instructions: %d item(s) hashed" % len(instructions)
    with open(os.path.join(folder, lid + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(kept, f, indent=1)
    L.append_record("event", event, writer="fos_launch")
    line = "%s:%s:%s" % (lid, instance, token)
    if "--file" in argv:
        with open(L.path(L.LAUNCH_FILE), "w", encoding="utf-8", newline="\n") as f:
            json.dump({"launch": line, "about": "Written by scripts/fos_launch.py --file. Never committed. While it is "
                                                "here, every member in this folder writes as %s." % instance}, f, indent=1)
    differs = [k for k, _, _ in FIELDS if slot.get(k) and stated.get(k) not in (slot.get(k), "unknown")]
    print("Launch %s recorded: %s, model %s by %s, in %s, served by %s." % (
        lid, instance, stated["model_id"], stated["producer"], stated["agent_app"], stated["host"]))
    for item in instructions:
        print("  the app's own instructions: %s (%s%s)" % (item["name"], item["sha256"][:16],
                                                          (", %d files" % item["files"]) if "files" in item else ""))
    if differs:
        print("Note: this differs from %s's model slot in org/config.json (%s). A change of model in a slot is a "
              "proposal and a decision; the check will say so." % (instance, ", ".join(differs)))
    if "--file" in argv:
        print("Written to %s: start the agent app in this folder. Only one instance at a time while this file is "
              "here." % L.LAUNCH_FILE)
    else:
        print("Start the agent app for %s from a terminal where this is set:" % instance)
        print("  PowerShell:      $env:FOS_LAUNCH=\"%s\"" % line)
        print("  Command Prompt:  set FOS_LAUNCH=%s" % line)
        print("  bash or zsh:     export FOS_LAUNCH=%s" % line)
        print("then start the app in this folder. Keep the line to yourself; do not paste it into a chat.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
