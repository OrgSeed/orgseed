"""Release the seed for publication: the files of its last commit, in a new repository with one commit.

Usage:
  python scripts/release_export.py <target-folder> --date <YYYY-MM-DDTHH:MM:SSZ> [options]
  python scripts/release_export.py --scan <folder> [--terms <file>] [--also <word>]... [--allow <text>]...

Options:
  --date <time>      the date of the release commit, in UTC (required), e.g. 2026-11-01T00:00:00Z.
                     Author and committer dates are both set to it, with the offset +0000.
  --terms <file>     a private list of words and patterns that must not appear in the release. JSON
                     with "block" (a list, or groups of lists), "review" and "allow"; or a text file with
                     one pattern per line, all treated as block. Patterns are regular expressions,
                     matched without regard to case. Keep the list outside the seed: it is read, never
                     copied, and nothing of it is written anywhere.
  --also <text>      one more word that must not appear (a name, a handle, a machine); may be repeated.
  --allow <text>     an exact string to ignore wherever it appears; may be repeated.
  --author "<name> <<e-mail>>"
                     the release identity. Default: "<seed name> authors <anonymous@example.invalid>".
  --message <text>   the commit message. Default: "<seed name> <version>", from seed.json.
  --replace          replace an earlier release in the target folder (only a folder this script made).
  --manifest <file>  also write the manifest to a file, outside the target folder.

What it does, in order:
  1. Refuses unless this folder is the seed itself (an organization born from the seed is exported
     with fos_export.py, because its history is its record), has no uncommitted changes, and has no
     tracked file that the ignore list would keep out.
  2. Writes every file of the last commit, byte for byte from git, into the target folder. Nothing
     else comes along: no .git, no ignored files, no history, no local settings.
  3. Makes the target a new git repository that reads no global or system git settings, adds the
     files, and checks that its tree is the seed's last tree (the same tree id means the same names
     and the same bytes).
  4. Scans every file, every file name and the commit it is about to make for: e-mail addresses,
     user paths, the user's and the machine's names, time zones, IP and hardware addresses, key-like
     strings, links to accounts and ORCID iDs, copyright and author lines, and the words given with
     --terms and --also.
  5. Stops without committing if the scan finds anything marked BLOCK. Otherwise it makes ONE commit
     with the release identity and the fixed date: no parent, no signature, no remote, no reflog.
     Then it checks that the repository holds that commit and nothing else.
  6. Prints a manifest: the commit and tree ids, then the SHA-256 of every file.
The same seed commit, date, identity and message give the same commit id on any machine.
It sends nothing anywhere and adds no remote; publishing is a separate step (docs/RELEASE.md).
--scan runs step 4 on any folder (a release, or a fresh clone of one), plus its git history and
settings when it has them.
Exit code: 0 released (or scanned) with nothing to read; 1 the same, with REVIEW items a person
should read; 2 refused, or BLOCK found, and nothing committed.
Standard library only; no network.
"""
import calendar
import collections
import hashlib
import ipaddress
import json
import math
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fos_lib as L  # noqa: E402

DEFAULT_MAIL = "anonymous@example.invalid"
MARKER = "release_export"                  # a file inside the release's .git: a folder this script made
RESERVED_MAIL = re.compile(r"(?:^|\.)(?:example\.(?:com|net|org)|example|invalid|test|localhost)$", re.I)
DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32")]
PLACEHOLDER_USERS = {"user", "username", "you", "your-name", "yourname", "me", "name", "runner", "vscode", "node",
                     "root", "...", "x", "someone", "public", "default", "all users", "shared"}
GENERIC_LOCAL = {"workgroup", "localhost", "root", "user", "admin", "administrator", "runner", "vscode", "node",
                 "utc", "gmt", "coordinated universal time", "local"}
# Time-zone abbreviations, kept in lower case here and matched in upper case only, so that this file
# never matches itself.
TZ_ABBR = ("est edt cst cdt mst mdt pst pdt akst akdt hst bst ist cet cest eet eest wet west msk "
           "jst kst hkt sgt awst acst aest aedt nzst nzdt").split()

Rule = collections.namedtuple("Rule", "category level rx judge note")
Finding = collections.namedtuple("Finding", "level category where text note")


# ---------------------------------------------------------------- the rules

def _offset_judge(m):
    sign, hh, mm = m.group("s"), m.group("h"), m.group("m") or "00"
    return None if int(hh) == 0 and int(mm) == 0 else "BLOCK"


def _offset_review(m):
    return None if _offset_judge(m) is None else "REVIEW"


def _ip_judge(m):
    try:
        ip = ipaddress.ip_address(m.group(0))
    except ValueError:
        return None
    if ip.is_loopback or ip.is_unspecified or any(ip in n for n in DOC_NETS) or str(ip) == "255.255.255.255":
        return None
    if ip.version == 6 and sum(1 for g in m.group(0).split(":") if g) < 3:
        return None
    return "REVIEW" if ip.is_global else "BLOCK"


def _mail_judge(m):
    domain = m.group(0).rsplit("@", 1)[1].rstrip(".")
    return None if RESERVED_MAIL.search(domain) else "BLOCK"


def _home_judge(m):
    who = m.group("u").strip().lower()
    if who in PLACEHOLDER_USERS or who[:1] in "<$%{[(" or who.endswith(">"):
        return None
    return "BLOCK"


def _entropy(s):
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in collections.Counter(s).values())


def _token_judge(m):
    t = m.group(0)
    if not (re.search(r"[a-z]", t) and re.search(r"[A-Z]", t) and re.search(r"\d", t)):
        return None
    return "REVIEW" if _entropy(t) >= 4.0 else None


def base_rules():
    r = []

    def add(category, level, pattern, judge=None, note="", flags=0):
        r.append(Rule(category, level, re.compile(pattern, flags), judge, note))

    add("e-mail", "BLOCK", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}", _mail_judge,
        "an e-mail address outside the reserved example domains")
    add("user path", "BLOCK", r"\b[A-Za-z]:[\\/]+(?:Users|Documents and Settings)[\\/]+(?P<u>[^\\/\s\"'`<>|*?]+)",
        _home_judge, "a path inside a user's home folder", re.I)
    add("user path", "BLOCK", r"(?<![\w.])(?:/[A-Za-z])?/(?:Users|home)/(?P<u>[A-Za-z0-9._-]+)", _home_judge,
        "a path inside a user's home folder")
    add("path", "REVIEW", r"(?<![\w%$])[A-Z]:\\{1,2}[A-Za-z0-9_$. -]{2,}", None, "an absolute Windows path")
    add("path", "REVIEW", r"\bfile:///\S+", None, "a link to a local file")
    add("path", "REVIEW", r"(?<![\w\\])\\\\[A-Za-z0-9_.-]+\\[A-Za-z0-9_$.-]+", None, "a network share")
    add("machine name", "BLOCK", r"\b(?:DESKTOP|LAPTOP)-[A-Z0-9]{6,8}\b", None, "a default Windows machine name")
    add("time zone", "BLOCK", r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?\s?(?P<s>[+-])(?P<h>\d{2}):?(?P<m>\d{2})\b",
        _offset_judge, "a timestamp with a local UTC offset")
    add("time zone", "BLOCK", r"\b\d{2}:\d{2}:\d{2}(?: \d{4})? (?P<s>[+-])(?P<h>\d{2})(?P<m>\d{2})\b", _offset_judge,
        "a git-style timestamp with a local UTC offset")
    add("time zone", "REVIEW", r"\b\d{1,2}:\d{2}(?::\d{2})?\s?(?P<s>[+-])(?P<h>\d{2}):(?P<m>\d{2})\b", _offset_review,
        "a time followed by an offset (or a time range)")
    add("time zone", "REVIEW", r"\b(?:UTC|GMT)\s?(?P<s>[+-])\s?(?P<h>\d{1,2})(?::?(?P<m>\d{2}))?\b", _offset_review,
        "a UTC offset")
    add("time zone", "BLOCK", r"\b(?:America|Europe|Asia|Africa|Australia|Pacific|Atlantic|Indian|Antarctica|US|"
        r"Canada|Brazil|Mexico|Chile)/[A-Z][A-Za-z_+-]+", None, "a named time zone")
    add("time zone", "BLOCK", r"\b(?:Eastern|Central|Mountain|Pacific|Atlantic|Alaska|Alaskan|Hawaii|Hawaiian|India|"
        r"China|Japan|Tokyo|Korea|Singapore|AUS Eastern|Central European|W\. Europe|GMT|British) "
        r"(?:Standard |Daylight |Summer )?Time\b", None, "a named time zone")
    add("time zone", "REVIEW", r"\b(?:%s)\b" % "|".join(a.upper() for a in TZ_ABBR), None,
        "a time-zone abbreviation")
    add("IP address", "BLOCK", r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w]|\.\d)", _ip_judge,
        "a private network address (BLOCK) or a public one, or a version number (REVIEW)")
    add("IP address", "BLOCK", r"(?<![\w:.])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{1,4}(?![\w:])", _ip_judge,
        "an IPv6 address")
    add("hardware address", "BLOCK", r"(?<![\w:-])(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}(?![\w:-])", None,
        "a network card's hardware address")
    begin = re.escape("-" * 5 + "BEGIN")
    add("key-like", "BLOCK", begin + r" [A-Z ]*PRIVATE KEY", None, "a private key")
    add("key-like", "BLOCK", r"\bsk-[A-Za-z0-9_-]{20,}", None, "an API key")
    add("key-like", "BLOCK", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}", None,
        "a code-hosting token")
    add("key-like", "BLOCK", r"\bAKIA[0-9A-Z]{16}\b", None, "a cloud access key")
    add("key-like", "BLOCK", r"\bAIza[0-9A-Za-z_-]{35}\b", None, "a cloud API key")
    add("key-like", "BLOCK", r"\bxox[abprs]-[A-Za-z0-9-]{10,}", None, "a chat-service token")
    add("key-like", "BLOCK", r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", None, "a signed web token")
    add("key-like", "BLOCK", r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}=*", None, "a bearer token")
    add("key-like", "BLOCK", r"(?i)\b(?:api[_-]?key|secret|token|passw(?:or)?d)\b[\"']?\s*[:=]\s*[\"'](?=[^\"']*\d)"
        r"[A-Za-z0-9/+_.-]{16,}[\"']", None, "a quoted value assigned to a key, secret, token or password")
    add("key-like", "BLOCK", r"^\s*(?:export\s+)?[A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_]*\s*=\s*(?=\S*\d)\S{16,}",
        None, "a setting that holds a key, secret, token or password")
    add("key-like", "REVIEW", r"(?<![A-Za-z0-9+/_=-])[A-Za-z0-9+/_=-]{32,}(?![A-Za-z0-9+/_=-])", _token_judge,
        "a long mixed string (a key, or encoded data)")
    add("key-like", "REVIEW", r"(?<![0-9a-fA-F])[0-9a-fA-F]{32,}(?![0-9a-fA-F])", None, "a long hex string (a hash, or a key)")
    add("ORCID iD", "BLOCK", r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b", None, "a researcher identifier")
    add("account link", "REVIEW", r"\b(?:github\.com|gitlab\.com|bitbucket\.org|codeberg\.org|huggingface\.co|hf\.co|"
        r"twitter\.com|x\.com|linkedin\.com|orcid\.org|osf\.io|zenodo\.org|researchgate\.net|scholar\.google\.[a-z.]+|"
        r"ssrn\.com|academia\.edu|youtube\.com|medium\.com|substack\.com)/[^\s)\"'<>\]]*", None,
        "a link to an account or a record that may be the authors'", re.I)
    add("copyright line", "REVIEW", r"(?i)(?:\bcopyright\b|©)\s*(?:\(c\)\s*)?(?:\d{4}|\[yyyy\]).*", None,
        "a copyright line: check the holder")
    add("author line", "REVIEW", r"(?i)(?:\b__author__\s*=|^\s*[-*]?\s*\**(?:author|authors|maintainer|contact)\**\s*:)\s*\S.*",
        None, "an author or contact line")
    return r


def local_rules():
    """Words that would identify this machine and its user, read at run time (never stored in a file)."""
    words, paths = set(), set()
    for k in ("USERNAME", "USER", "LOGNAME", "COMPUTERNAME", "USERDOMAIN", "HOSTNAME", "USERDNSDOMAIN"):
        if os.environ.get(k):
            words.add(os.environ[k])
    home = os.path.expanduser("~")
    words.add(os.path.basename(home.rstrip("\\/")))
    try:
        words.add(socket.gethostname())
        words.add(socket.gethostname().split(".")[0])
    except OSError:
        pass
    for key in ("user.name", "user.email"):
        try:
            r = subprocess.run(["git", "config", "--global", "--get", key], capture_output=True)
            if r.returncode == 0:
                words.add(r.stdout.decode("utf-8", "replace").strip())
        except OSError:
            pass
    words.update(n for n in time.tzname if n)
    for p in (home, L.ROOT, os.path.dirname(L.ROOT)):
        if p and len(p) > 3:
            paths.update({p, p.replace("\\", "/")})
    rules = []
    for w in sorted({w.strip() for w in words if w and w.strip()}):
        if len(w) >= 3 and w.lower() not in GENERIC_LOCAL:
            rules.append(Rule("this machine or user", "BLOCK", re.compile(r"(?<!\w)%s(?!\w)" % re.escape(w), re.I),
                              None, "a name of this machine, its user, its time zone or its git identity"))
    for p in sorted(paths):
        rules.append(Rule("this machine or user", "BLOCK", re.compile(re.escape(p), re.I), None, "a path on this machine"))
    return rules


def term_rules(path, also):
    rules, allow = [], []
    if path:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if path.lower().endswith(".json"):
            t = json.loads(text)
            block = t.get("block", [])
            groups = block.items() if isinstance(block, dict) else [("block", block)]
            for g, pats in groups:
                for p in pats:
                    rules.append(Rule("term list (%s)" % g, "BLOCK", re.compile(p, re.I), None, "a word on the private list"))
            for p in t.get("review", []):
                rules.append(Rule("term list (review)", "REVIEW", re.compile(p, re.I), None, "a word on the private list"))
            allow = list(t.get("allow", []))
        else:
            for ln in text.splitlines():
                if ln.strip() and not ln.lstrip().startswith("#"):
                    rules.append(Rule("term list", "BLOCK", re.compile(ln.strip(), re.I), None, "a word on the private list"))
    for w in also:
        rules.append(Rule("--also", "BLOCK", re.compile(r"(?<!\w)%s(?!\w)" % re.escape(w), re.I), None, "a word given with --also"))
    return rules, allow


# ---------------------------------------------------------------- scanning

def mask(line, allow):
    for a in allow:
        line = re.sub(re.escape(a), " " * len(a), line, flags=re.I)
    return line


def scan_text(text, where, rules, allow, out, levels=("BLOCK", "REVIEW")):
    for i, raw in enumerate(text.splitlines(), 1):
        line = mask(raw, allow)
        for r in rules:
            for m in r.rx.finditer(line):
                level = r.judge(m) if r.judge else r.level
                if level in levels:
                    out.append(Finding(level, r.category, "%s:%d" % (where, i), m.group(0).strip()[:100], r.note))


def walk_files(folder):
    for d, dirs, files in os.walk(folder):
        dirs[:] = sorted(x for x in dirs if x != ".git")
        for fn in sorted(files):
            p = os.path.join(d, fn)
            yield os.path.relpath(p, folder).replace("\\", "/"), p


def scan_folder(folder, rules, allow, out):
    n = 0
    for rel, p in walk_files(folder):
        with open(p, "rb") as f:
            data = f.read()
        scan_text(rel, "name:" + rel, rules, allow, out)
        if b"\0" in data[:8192]:
            out.append(Finding("REVIEW", "binary file", rel, rel, "scanned as bytes for BLOCK items only; check its metadata by hand"))
            scan_text(data.decode("latin-1"), rel, rules, allow, out, levels=("BLOCK",))
        else:
            scan_text(data.decode("utf-8", "replace"), rel, rules, allow, out)
        n += 1
    return n


def scan_git(folder, rules, allow, out, expect=None):
    """The history and settings a published repository carries or a copy of it may carry."""
    env = clean_env()
    code, refs, _ = tgit(folder, "for-each-ref", "--format=%(objectname) %(objecttype) %(refname)", env=env)
    if code != 0:
        out.append(Finding("BLOCK", "git", ".git", "unreadable", "the repository could not be read"))
        return 0
    commits = tgit(folder, "rev-list", "--all", env=env)[1].split()
    for c in commits:
        raw = tgit(folder, "cat-file", "commit", c, env=env)[1]
        head, _, msg = raw.partition("\n\n")
        for ln in head.splitlines():
            key = ln.split(" ", 1)[0]
            if key in ("author", "committer"):
                m = re.match(r"\w+ (.*) <(.*)> (\d+) ([+-]\d{4})$", ln)
                if not m:
                    out.append(Finding("BLOCK", "git", "commit " + c[:12], ln[:100], "an unreadable identity line"))
                    continue
                if m.group(4) != "+0000":
                    out.append(Finding("BLOCK", "time zone", "commit " + c[:12], "%s %s" % (key, m.group(4)),
                                       "a commit date with a local UTC offset"))
                scan_text("%s <%s>" % (m.group(1), m.group(2)), "commit %s %s" % (c[:12], key), rules, allow, out)
            elif key in ("gpgsig", "gpgsig-sha256", "mergetag"):
                out.append(Finding("BLOCK", "git", "commit " + c[:12], key, "a signature, which names its signer's key"))
            elif key not in ("tree", "parent", "encoding", ""):
                out.append(Finding("REVIEW", "git", "commit " + c[:12], key, "an unusual commit header"))
        scan_text(msg, "commit %s message" % c[:12], rules, allow, out)
    for ln in refs.splitlines():
        oid, kind, name = ln.split(" ", 2)
        if kind == "tag":
            raw = tgit(folder, "cat-file", "tag", oid, env=env)[1]
            out.append(Finding("REVIEW", "git", name, "annotated tag", "a tag object carries a tagger's name and time"))
            scan_text(raw, "tag " + name, rules, allow, out)
    cfg = tgit(folder, "config", "--local", "--list", env=env)[1]
    for ln in cfg.splitlines():
        k = ln.split("=", 1)[0].lower()
        if k.startswith(("remote.", "url.", "credential", "branch.")):
            out.append(Finding("REVIEW", "git settings", ".git/config", ln[:100],
                               "local settings travel with a copied folder, not with a push or a clone"))
    scan_text(cfg, ".git/config", rules, allow, out)
    if expect is not None and len(commits) != expect:
        out.append(Finding("BLOCK", "git", ".git", "%d commits" % len(commits), "a release holds exactly %d" % expect))
    return len(commits)


def report(out, header):
    lines = list(header)
    block = [f for f in out if f.level == "BLOCK"]
    review = [f for f in out if f.level == "REVIEW"]
    lines.append("BLOCK: %d" % len(block))
    for f in block[:300]:
        lines.append("  [%s] %s -> %r  (%s)" % (f.category, f.where, f.text, f.note))
    if len(block) > 300:
        lines.append("  ... %d more" % (len(block) - 300))
    groups = collections.OrderedDict()
    for f in review:
        g = groups.setdefault((f.category, f.text.lower()), [0, [], f.note])
        g[0] += 1
        if len(g[1]) < 3:
            g[1].append(f.where)
    lines.append("REVIEW: %d hit(s), %d distinct" % (len(review), len(groups)))
    for (cat, text), (n, wh, note) in sorted(groups.items(), key=lambda x: (x[0][0], -x[1][0], x[0][1])):
        lines.append("  [%s] %r x%d in %s%s" % (cat, text[:60], n, ", ".join(wh), " ..." if n > len(wh) else ""))
    return lines, len(block), len(review)


# ---------------------------------------------------------------- git in the release folder

def clean_env(extra=None):
    """Run git as if this machine had no global or system settings (no identity, hooks, templates or signing)."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=EMPTY["config"], GIT_TERMINAL_PROMPT="0",
               GIT_TEMPLATE_DIR=EMPTY["templates"])
    env.update(extra or {})
    return env


EMPTY = {}


def make_empty():
    d = tempfile.mkdtemp(prefix="release-git-")
    open(os.path.join(d, "config"), "w").close()
    os.makedirs(os.path.join(d, "templates"))
    EMPTY.update(dir=d, config=os.path.join(d, "config"), templates=os.path.join(d, "templates"))


def tgit(folder, *args, env=None, data=None):
    r = subprocess.run(["git", "-C", folder] + list(args), capture_output=True, input=data, env=env or clean_env())
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace").strip()


def rmtree(p):
    def onerror(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    shutil.rmtree(p, onerror=onerror)


def made_by_us(target):
    return os.path.isfile(os.path.join(target, ".git", MARKER))


# ---------------------------------------------------------------- the release

def parse_date(text):
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(Z|[+-]00:?00)", (text or "").strip())
    if not m:
        return None
    y, mo, d, h, mi, s = (int(x or 0) for x in m.groups()[:6])
    try:
        return calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0)) if 1 <= mo <= 12 and 1 <= d <= 31 else None
    except (ValueError, OverflowError):
        return None


def option(argv, name, many=False):
    vals = [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == name]
    return vals if many else (vals[-1] if vals else None)


def seed_blobs():
    code, out = L.git("ls-tree", "-r", "-z", "--full-tree", "HEAD")
    entries = []
    for item in out.split("\0"):
        if item:
            meta, rel = item.split("\t", 1)
            mode, kind, oid = meta.split()
            entries.append((mode, kind, oid, rel))
    return entries


def read_blobs(oids):
    r = subprocess.run(["git", "-C", L.ROOT, "cat-file", "--batch"], input=("\n".join(oids) + "\n").encode(),
                       capture_output=True)
    data, pos, blobs = r.stdout, 0, {}
    for oid in oids:
        nl = data.index(b"\n", pos)
        head = data[pos:nl].decode().split()
        size = int(head[2])
        blobs[oid] = data[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1
    return blobs


def inside(path, base):
    """True if path is base or lies inside it (case-blind where the file system is)."""
    try:
        a, b = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(base))
        return os.path.commonpath([a, b]) == b
    except ValueError:
        return False


def refuse(msg):
    print(msg)
    return 2


def main(argv):
    terms = option(argv, "--terms")
    also = option(argv, "--also", many=True)
    allow_extra = option(argv, "--allow", many=True)
    if terms and not os.path.isfile(terms):
        return refuse("--terms: no such file: %s" % terms)
    if terms and inside(terms, L.ROOT):
        return refuse("Keep the term list outside the seed (it was given from inside it).")
    try:
        t_rules, t_allow = term_rules(terms, also)
    except (ValueError, re.error) as e:
        return refuse("--terms: the list could not be read: %s" % e)
    rules = base_rules() + local_rules() + t_rules
    allow = t_allow + allow_extra
    make_empty()
    try:
        if "--scan" in argv:
            folder = option(argv, "--scan")
            if not folder or not os.path.isdir(folder):
                return refuse("--scan needs a folder.")
            out = []
            n = scan_folder(folder, rules, allow, out)
            c = scan_git(folder, rules, allow, out) if os.path.isdir(os.path.join(folder, ".git")) else None
            lines, nb, nr = report(out, ["Scan of %s: %d file(s)%s" % (os.path.abspath(folder), n,
                                                                       "" if c is None else ", %d commit(s)" % c)])
            print("\n".join(lines))
            return 2 if nb else (1 if nr else 0)
        return release(argv, rules, allow)
    finally:
        rmtree(EMPTY["dir"])


def release(argv, rules, allow):
    flags_with_values = {"--date", "--terms", "--also", "--allow", "--author", "--message", "--manifest"}
    args, skip = [], False
    for a in argv[1:]:
        if skip:
            skip = False
        elif a in flags_with_values:
            skip = True
        elif not a.startswith("--"):
            args.append(a)
    if len(args) != 1:
        print(__doc__)
        return 2
    target = os.path.abspath(args[0])
    epoch = parse_date(option(argv, "--date"))
    if epoch is None:
        return refuse("Give the release date in UTC with --date, e.g. --date 2026-11-01T00:00:00Z (the offset must be Z or +00:00).")
    seed = L.seed_info()
    author = option(argv, "--author") or "%s authors <%s>" % (seed.get("name", "seed"), DEFAULT_MAIL)
    m = re.fullmatch(r"\s*([^<>\n]+?)\s*<([^<>\s]*)>\s*", author)
    if not m:
        return refuse('--author must look like "Name <e-mail>".')
    name, mail = m.group(1), m.group(2)
    message = option(argv, "--message") or "%s %s" % (seed.get("name", "seed"), seed.get("version", ""))
    message = message.strip() + "\n"
    manifest_file = option(argv, "--manifest")

    # 1. what may be released
    if not (L.git_ok() and L.has_head()):
        return refuse("The release is made from the seed's last commit: it needs git and at least one commit.")
    if L.stage_info()["stage"] != "seed":
        return refuse("This folder is an organization born from the seed. Its history is its record: export it "
                      "with python scripts/fos_export.py. A release with a fresh history is made only from the seed.")
    code, status = L.git("status", "--porcelain")
    if [ln for ln in status.splitlines() if ln.strip()]:
        return refuse("The seed has uncommitted changes. The release is made from the last commit only: commit "
                      "them (or set them aside) and run again.\n" + status)
    code, ignored = L.git("ls-files", "-ci", "--exclude-standard")
    if ignored.strip():
        return refuse("These tracked files match the ignore list, so they may hold what the list keeps out. "
                      "Untrack them in the seed (git rm --cached) and commit:\n" + ignored)
    if inside(target, L.ROOT) or inside(L.ROOT, target):
        return refuse("Write the release outside the seed's folder, and not around it: %s" % target)
    if manifest_file and (inside(manifest_file, target) or inside(manifest_file, L.ROOT)):
        return refuse("Write the manifest outside the release and outside the seed.")
    if os.path.exists(target) and (not os.path.isdir(target) or os.listdir(target)):
        if "--replace" not in argv:
            return refuse("%s exists and is not empty. Give --replace to replace an earlier release." % target)
        if not made_by_us(target):
            return refuse("%s was not made by this script, so --replace will not delete it." % target)
        rmtree(target)

    # 2. the files of the last commit, byte for byte
    entries = seed_blobs()
    odd = [e for e in entries if e[1] != "blob" or e[0] not in ("100644", "100755")]
    if odd:
        return refuse("The seed holds entries a release cannot carry as plain files (links or submodules): %s"
                      % ", ".join(e[3] for e in odd))
    seed_tree = L.git("rev-parse", "HEAD^{tree}")[1].strip()
    seed_commit = L.git("rev-parse", "HEAD")[1].strip()
    blobs = read_blobs([e[2] for e in entries])
    os.makedirs(target, exist_ok=True)
    files = []
    for mode, _, oid, rel in entries:
        p = os.path.join(target, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(blobs[oid])
        files.append((rel, hashlib.sha256(blobs[oid]).hexdigest(), len(blobs[oid]), mode))

    # 3. a new repository, with no settings from this machine
    env = clean_env()
    steps = [("init", "-q", target), ("symbolic-ref", "HEAD", "refs/heads/main"),
             ("config", "core.autocrlf", "false"), ("config", "core.logAllRefUpdates", "false"),
             ("config", "user.name", name), ("config", "user.email", mail)]
    for s in steps:
        code, _, err = tgit(target, *s, env=env)
        if code != 0:
            return refuse("git %s failed: %s" % (s[0], err))
    with open(os.path.join(target, ".git", MARKER), "w", encoding="utf-8", newline="\n") as f:
        f.write("This repository was made by scripts/release_export.py; --replace may delete it.\n")
    code, _, err = tgit(target, "add", "-A", env=env)
    for rel, _, _, mode in files:
        if mode == "100755":
            tgit(target, "update-index", "--chmod=+x", "--", rel, env=env)
    code, tree, err = tgit(target, "write-tree", env=env)
    tree = tree.strip()
    out = []
    if tree != seed_tree:
        out.append(Finding("BLOCK", "tree", "release", tree[:12],
                           "the release's tree differs from the seed's last tree %s (line endings or modes changed)" % seed_tree[:12]))

    # 4. the scan
    n = scan_folder(target, rules, allow, out)
    scan_text("%s <%s>" % (name, mail), "commit identity", rules, allow, out)
    scan_text(message, "commit message", rules, allow, out)
    header = ["Release of %s %s into %s" % (seed.get("name", "seed"), seed.get("version", "?"), target),
              "Scan: %d file(s) and their names, the commit identity and message" % n]
    lines, nb, nr = report(out, header)
    print("\n".join(lines))
    if nb:
        print("\nNothing was committed. The files are left in %s to look at. Fix the seed, commit, and run again "
              "with --replace." % target)
        return 2

    # 5. one commit, and nothing else
    stamp = "%d +0000" % epoch
    cenv = clean_env(dict(GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=mail, GIT_AUTHOR_DATE=stamp,
                          GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=mail, GIT_COMMITTER_DATE=stamp))
    code, commit, err = tgit(target, "commit-tree", tree, env=cenv, data=message.encode("utf-8"))
    commit = commit.strip()
    if code != 0 or not commit:
        return refuse("git commit-tree failed: %s" % err)
    code, _, err = tgit(target, "update-ref", "refs/heads/main", commit, env=cenv)
    if code != 0:
        return refuse("git update-ref failed: %s" % err)
    problems = []
    raw = tgit(target, "cat-file", "commit", commit, env=env)[1]
    want = "tree %s\nauthor %s <%s> %s\ncommitter %s <%s> %s\n\n%s" % (tree, name, mail, stamp, name, mail, stamp, message)
    if raw != want:
        problems.append("the commit object is not exactly tree, author, committer and message")
    if tgit(target, "for-each-ref", "--format=%(refname)", env=env)[1].split() != ["refs/heads/main"]:
        problems.append("the repository holds refs other than main")
    if tgit(target, "rev-list", "--all", "--count", env=env)[1].strip() != "1":
        problems.append("the repository holds more than one commit")
    if tgit(target, "remote", env=env)[1].strip():
        problems.append("the repository has a remote")
    if tgit(target, "status", "--porcelain", env=env)[1].strip():
        problems.append("the working files differ from the commit")
    if tgit(target, "fsck", "--unreachable", "--no-reflogs", "--no-progress", env=env)[1].strip():
        problems.append("the repository holds objects the commit does not reach")
    if os.path.exists(os.path.join(target, ".git", "logs")):
        problems.append("a reflog was written")
    git_out = []
    scan_git(target, rules, allow, git_out, expect=1)
    problems += ["%s: %s" % (f.where, f.note) for f in git_out if f.level == "BLOCK"]
    if problems:
        print("\nThe release repository failed its own check; do not publish it:\n  " + "\n  ".join(problems))
        return 2

    # 6. the manifest
    body = ["%s  %s" % (h, rel) for rel, h, _, _ in files]
    digest = hashlib.sha256(("\n".join(body) + "\n").encode("utf-8")).hexdigest()
    man = ["# Release manifest",
           "# commit    %s" % commit,
           "# tree      %s (the seed's last tree)" % tree,
           "# identity  %s <%s>, author and committer" % (name, mail),
           "# date      %s (%d +0000)" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch)), epoch),
           "# message   %s" % message.strip().replace("\n", " / "),
           "# files     %d, %d bytes" % (len(files), sum(f[2] for f in files)),
           "# sha256 of the lines below: %s" % digest] + body
    print("\nReleased: one commit %s on main in %s (no remote; nothing was sent anywhere)." % (commit, target))
    print("\n".join(man))
    print("\n(For you, not part of the release: made from the seed's commit %s.)" % seed_commit)
    if manifest_file:
        with open(manifest_file, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(man) + "\n")
        print("manifest written to %s" % manifest_file)
    return 1 if nr else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
