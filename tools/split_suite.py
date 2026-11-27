#!/usr/bin/env python3
"""Cuts tests/run_tests.sh at its sections so pieces of the suite can run side by side (tools/test_parallel.sh).
   python3 tools/split_suite.py list                 section number, first line, name
   python3 tools/split_suite.py build OUT 3,5,9-12 [OWN]   a runnable script: the start of the suite + those sections + the end (only OWN are counted)\n   python3 tools/split_suite.py deps                 which earlier sections each section needs (read from the script text)\n   python3 tools/split_suite.py plan 3               the sections of each of 3 shards and which of them each shard owns
Nothing in tests/run_tests.sh is changed. Sections are the lines that start with   sec "== ...   """
import re, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tests", "run_tests.sh")

def parse():
    lines = open(SRC, encoding="utf-8").read().split("\n")
    starts = [i for i, l in enumerate(lines) if l.startswith('sec "')]
    end = max(i for i, l in enumerate(lines) if l == "repo_guard")   # the last repo_guard: the epilogue (real-home check, summary) starts there
    assert starts and end > starts[-1], "run_tests.sh has no sections or no closing repo_guard"
    head = lines[:starts[0]]
    bounds = starts + [end]
    secs = []
    for n in range(len(starts)):
        body = lines[bounds[n]:bounds[n + 1]]
        name = re.match(r'sec "([^"]*)', lines[starts[n]]).group(1)
        secs.append((n + 1, starts[n] + 1, name, body))
    tail = lines[end:]
    return head, secs, tail


CREATE_WORDS = re.compile(r'(mkdir|mkstage|mksv|mkhome|\bcp\b|\btar\b|\btouch\b|\bmv\b|\bln\b|cat >|printf .*>|echo .*>|git init|rm -rf)')

def analyze(head, secs):
    """For every section: the earlier sections it needs. A section needs the latest earlier section that sets a shell variable or function
    it uses, and the latest earlier section that makes a folder or file under $T/name that it uses but does not make itself."""
    assigned = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)=|(?<=; )([A-Z][A-Z0-9_]*)=', re.M)   # at the start of a line, or an UPPERCASE one after '; ' (mkstage x; HR=...)
    funcs = re.compile(r'^([A-Za-z_][A-Za-z0-9_-]*)\(\)\s*\{', re.M)
    head_text = "\n".join(head)
    head_defs = set(x for t in assigned.findall(head_text) for x in t if x) | set(funcs.findall(head_text))
    defs, text = {}, {}
    for n, line, name, body in secs:
        t = "\n".join(body); text[n] = t
        defs[n] = set(x for tt in assigned.findall(t) for x in tt if x) | set(funcs.findall(t))
    tok = re.compile(r'\$T/([A-Za-z0-9_.-]+)')
    creators = {}   # token -> sections that make it
    for n, line, name, body in secs:
        for l in body:
            if CREATE_WORDS.search(l):
                for x in tok.findall(l): creators.setdefault(x, set()).add(n)
    deps = {n: set() for n, _, _, _ in secs}
    for n, line, name, body in secs:
        t = text[n]
        names = set(re.findall(r'\$\{?([A-Za-z_][A-Za-z0-9_]*)', t))
        for d in defs:                       # a function used as a command: its name as a word
            pass
        allfn = set(x for s2 in defs.values() for x in s2)
        for fn in allfn:
            if fn in names: continue
            if re.search(r'(?<![\w./$-])' + re.escape(fn) + r'(?![\w-])', t) and fn not in head_defs and fn not in defs[n]: names.add(fn)
        for v in names:
            if v in head_defs or v in defs[n]: continue
            earlier = [m for m in defs if m < n and v in defs[m]]
            if earlier: deps[n].add(max(earlier))
        for x in set(tok.findall(t)):
            if n in creators.get(x, ()): continue
            earlier = [m for m in creators.get(x, ()) if m < n]
            if earlier: deps[n].add(max(earlier))
    return deps

def components(deps):
    """Sections that must run together (a section and everything it needs, directly or through others)."""
    parent = {n: n for n in deps}
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for n, ds in deps.items():
        for d in ds: parent[find(n)] = find(d)
    comp = {}
    for n in sorted(deps): comp.setdefault(find(n), []).append(n)
    return sorted(comp.values())

def closure(n, deps, seen=None):
    seen = set() if seen is None else seen
    if n in seen: return seen
    seen.add(n)
    for d in deps[n]: closure(d, deps, seen)
    return seen

def own_plan(deps, weights, shards):
    """Every section is OWNED by one shard (its result counts there). A shard also runs the sections its owned ones need, but those
    are not counted again. Greedy: biggest first, to the shard where it adds the least time."""
    cl = {n: closure(n, deps) for n in deps}
    cost = lambda ns: sum(weights.get(x, 20) for x in ns)
    owned = [[] for _ in range(shards)]; allsec = [set() for _ in range(shards)]
    for n in sorted(deps, key=lambda n: -cost(cl[n])):
        best = min(range(shards), key=lambda i: (cost(allsec[i] | cl[n]), cost(allsec[i])))
        owned[best].append(n); allsec[best] |= cl[n]
    return [(round(cost(allsec[i])), sorted(allsec[i]), sorted(owned[i])) for i in range(shards)]

def pack(comps, weights, shards):
    """Longest first into the lightest shard; sections inside a shard keep their original order."""
    bins = [[0.0, []] for _ in range(shards)]
    for c in sorted(comps, key=lambda c: -sum(weights.get(n, 30) for n in c)):
        b = min(bins, key=lambda b: b[0]); b[0] += sum(weights.get(n, 30) for n in c); b[1].extend(c)
    return [(round(w), sorted(ns)) for w, ns in bins]

def spec(ns):
    out, i = [], 0
    ns = sorted(ns)
    while i < len(ns):
        j = i
        while j + 1 < len(ns) and ns[j + 1] == ns[j] + 1: j += 1
        out.append(str(ns[i]) if i == j else "%d-%d" % (ns[i], ns[j])); i = j + 1
    return ",".join(out)

def ranges(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part: continue
        if "-" in part:
            a, b = part.split("-", 1); out.extend(range(int(a), int(b) + 1))
        else: out.append(int(part))
    return sorted(set(out))

def main(argv):
    if len(argv) >= 2 and argv[1] == "list":
        head, secs, tail = parse()
        for n, line, name, body in secs: print("%d\t%d\t%d\t%s" % (n, line, len(body), name))
        return 0

    if len(argv) >= 2 and argv[1] == "deps":
        head, secs, tail = parse(); deps = analyze(head, secs)
        names = {n: name for n, l, name, b in secs}
        for n in sorted(deps): print("%d\t%s\t%s" % (n, ",".join(map(str, sorted(deps[n]))) or "-", names[n]))
        return 0
    if len(argv) == 3 and argv[1] == "closure":   # closure SPEC: the given sections plus every section they need, as a spec
        head, secs, tail = parse(); deps = analyze(head, secs)
        extra = os.path.join(ROOT, "tools", "suite_extra_deps.txt")
        if os.path.exists(extra):
            for l in open(extra):
                if l.strip() and not l.startswith("#"):
                    x, y = l.split("\t")[:2]; deps[int(x)].update(int(z) for z in y.split(",") if z.strip())
        allns = set()
        for n in ranges(argv[2]): allns |= closure(n, deps)
        print(spec(allns)); return 0
    if len(argv) >= 3 and argv[1] == "plan":
        # plan SHARDS [weights.tsv]: weights.tsv has "section<TAB>seconds"; prints one line per shard: seconds<TAB>sections
        head, secs, tail = parse(); deps = analyze(head, secs)
        extra = os.path.join(ROOT, "tools", "suite_extra_deps.txt")   # by hand: "section<TAB>needs,needs" when the text analysis misses one
        if os.path.exists(extra):
            for l in open(extra):
                if l.strip() and not l.startswith("#"):
                    a, b = l.split("\t")[:2]; deps[int(a)].update(int(x) for x in b.split(",") if x.strip())
        w = {}
        if len(argv) >= 4:
            for l in open(argv[3]):
                p2 = l.split("\t")
                if len(p2) >= 2: w[int(p2[0])] = float(p2[1])
        else:
            KNOWN = {47: 399, 31: 327, 34: 237, 27: 227, 59: 176, 32: 127, 43: 124, 68: 93, 35: 81, 30: 69, 37: 59, 41: 59}   # seconds, suite 2.35.0 on the pi400
            for n, line, name, body in secs: w[n] = KNOWN.get(n, max(5, len(body) * 0.4))
        for est, allns, ownns in own_plan(deps, w, int(argv[2])): print("%d\t%s\t%s" % (est, spec(allns), spec(ownns)))
        return 0
    if len(argv) in (4, 5) and argv[1] == "build":
        head, secs, tail = parse()
        want = ranges(argv[3]); have = {s[0]: s for s in secs}
        bad = [w for w in want if w not in have]
        if bad: print("no such section: %s" % bad, file=sys.stderr); return 2
        own = set(ranges(argv[4])) if len(argv) == 5 else set(want)
        text = list(head)
        for w in want:
            body = list(have[w][3])
            if w not in own:   # only run because another section needs what it sets up: its results are not counted here
                body.insert(1, "__P=$PASS; __F=$FAIL"); body.append("PASS=$__P; FAIL=$__F")
            text.extend(body)
        text.extend(tail)
        with open(argv[2], "w", encoding="utf-8") as f: f.write("\n".join(text))
        return 0
    print(__doc__); return 2

sys.exit(main(sys.argv))
