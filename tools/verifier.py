# -*- coding: utf-8 -*-
"""Verify the database. CI runs this on every pull request.

    python3 tools/verifier.py [database-dir]

It refuses what a machine can refuse, so that a reviewer only spends attention
on what needs judgement: is this source serious, is this figure plausible for
this device. A rule a human has to remember is a rule that stops being applied
around the thirtieth contribution.
"""
import json, os, re, sys

DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "database")
errors, warnings = [], []
IDENTITY_KEYS = {"id", "kind", "brand", "model", "aliases", "usb", "superseded_by"}
ALIAS_RELATIONS = {"spelling", "edition", "neighbour"}
KINDS = {"dac", "network_player"}


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        errors.append("%s: not valid JSON (%s)" % (rel(path), e))
        return None


def rel(p):
    return os.path.relpath(p, DB)


def find_nulls(obj, path=""):
    """null is not a value here. It carried two opposite meanings at once."""
    if obj is None:
        return [path or "(root)"]
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += find_nulls(v, "%s.%s" % (path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += find_nulls(v, "%s[%d]" % (path, i))
    return out


# --- the field registry ------------------------------------------------------
# Every field a claim asserts must be registered in schemas/fields.json. Without
# this, a typo invents a field, nobody notices, and the value is silently never
# read: it is exactly how five fields came to exist that the catalogue's own list
# did not name.
REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "schemas", "fields.json")
registry = {}
if os.path.exists(REGISTRY):
    registry = (load(REGISTRY) or {}).get("fields", {})
else:
    errors.append("schemas/fields.json is missing. Nothing can check that a claim "
                  "asserts a field that exists")


def check_field(where, name, scope):
    key = name if scope == "device" else "inputs." + name
    entry = registry.get(key)
    if entry is None:
        errors.append("%s: field %r is not in schemas/fields.json. Register it — with "
                      "its type and what it means — or correct the spelling"
                      % (where, key))
        return
    if entry.get("deprecated"):
        warnings.append("%s: field %r is deprecated — %s"
                        % (where, key, entry.get("description", "")[:80]))


brands, families, ifaces = set(), set(), set()
for name, bucket in (("brands", brands), ("chip-families", families),
                     ("interfaces", ifaces)):
    d = os.path.join(DB, name)
    if not os.path.isdir(d):
        errors.append("missing directory: %s" % name)
        continue
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"):
            continue
        entry = load(os.path.join(d, f))
        if entry is None:
            continue
        for where in find_nulls(entry, os.path.join(name, f)):
            errors.append("null at %s. Leave the key out, or write \"unknown\"" % where)
        bucket.add(entry.get("id") or f[:-5])

devices = os.path.join(DB, "devices")
n_dev = n_claim = 0
for brand_dir in sorted(os.listdir(devices)) if os.path.isdir(devices) else []:
    bpath = os.path.join(devices, brand_dir)
    if not os.path.isdir(bpath):
        continue
    for dev_dir in sorted(os.listdir(bpath)):
        base = os.path.join(bpath, dev_dir)
        if not os.path.isdir(base):
            continue
        n_dev += 1
        ident_path = os.path.join(base, "identity.json")
        if not os.path.exists(ident_path):
            errors.append("%s: no identity.json" % rel(base))
            continue
        ident = load(ident_path)
        if ident is None:
            continue
        for where in find_nulls(ident, rel(ident_path)):
            errors.append("null at %s. Leave the key out, or write \"unknown\"" % where)
        # THE ID IS THE PATH. One identity, one spelling: the id used to be a flat
        # `holo_may` beside a directory `holo-audio/holo-may`, which is two homes for
        # one key and the exact drift this catalogue keeps paying for elsewhere. The
        # slug is frozen - it is never renamed, a replacement record is created and
        # the old one marked superseded_by - so it had better be derivable.
        attendu = "%s/%s" % (brand_dir, dev_dir)
        if ident.get("id") != attendu:
            errors.append("%s: id is %r but its path says %r. The id IS the path"
                          % (rel(ident_path), ident.get("id"), attendu))
        # An alias says HOW a name relates to this record. Untyped, it silently
        # merged a spelling, an edition and a different product.
        for al in (ident.get("aliases") or []):
            if not isinstance(al, dict) or "text" not in al or al.get("relation") not in ALIAS_RELATIONS:
                errors.append("%s: alias %r must be {text, relation} with relation in %s"
                              % (rel(ident_path), al, ", ".join(sorted(ALIAS_RELATIONS))))
        for f in ("id", "kind", "brand", "model"):
            if not ident.get(f):
                errors.append("%s: identity has no %s" % (rel(ident_path), f))
        if ident.get("kind") and ident["kind"] not in KINDS:
            errors.append("%s: kind %r is not one of %s. The registry covers "
                          "converters and network players"
                          % (rel(ident_path), ident["kind"], ", ".join(sorted(KINDS))))
        if ident.get("brand") not in brands:
            errors.append("%s: brand %r is not in database/brands"
                          % (rel(ident_path), ident.get("brand")))
        # Identity names the device. It must not carry facts, or there would be
        # two places to get the same thing wrong.
        stray = [k for k in ident
                 if not k.startswith("_") and k not in IDENTITY_KEYS]
        if stray:
            errors.append("%s: identity carries %s, which are facts. Facts belong "
                          "in a claim, with their evidence" % (rel(ident_path),
                                                               ", ".join(sorted(stray))))

        cdir = os.path.join(base, "claims")
        claims = sorted(f for f in os.listdir(cdir)
                        if f.endswith(".json")) if os.path.isdir(cdir) else []
        if not claims:
            warnings.append("%s: no claim. The record names a device and asserts "
                            "nothing about it" % rel(base))
        for cf in claims:
            n_claim += 1
            cpath = os.path.join(cdir, cf)
            c = load(cpath)
            if c is None:
                continue
            for where in find_nulls(c, rel(cpath)):
                errors.append("null at %s. Leave the key out, or write \"unknown\""
                              % where)
            src = c.get("source") or {}
            if not src.get("quote"):
                errors.append("%s: a claim with no quoted evidence. A source that "
                              "does not quote the words carrying the fact is an "
                              "address, not evidence" % rel(cpath))
            if not src.get("kind"):
                errors.append("%s: the source does not say what kind it is" % rel(cpath))
            if not c.get("submitted_by"):
                errors.append("%s: no submitted_by" % rel(cpath))
            if not (c.get("facts") or c.get("inputs")):
                errors.append("%s: a claim that asserts nothing" % rel(cpath))
            for f in (c.get("facts") or {}):
                if not f.startswith("_"):
                    check_field(rel(cpath), f, "device")
            for iface, blk in (c.get("inputs") or {}).items():
                if iface not in ifaces:
                    errors.append("%s: input %r is not in database/interfaces"
                                  % (rel(cpath), iface))
                for f in blk:
                    if not f.startswith("_"):
                        check_field(rel(cpath), f, "device_input")
            fam = (c.get("facts") or {}).get("family")
            if fam and fam != "unknown" and fam not in families:
                errors.append("%s: chip family %r is not in database/chip-families"
                              % (rel(cpath), fam))

# --- what must not be published ----------------------------------------------
# The seed came from a private catalogue, and a private catalogue carries things
# a public registry must not: a sponsor's unreleased product names, internal
# roadmap, reasoning about one vendor's software. The migration filtered those
# out; this check is what keeps them out once contributions arrive directly and
# the migration is no longer in the path.
FORBIDDEN = [
    (r"\bSendspin\b", "an unreleased product name"),
    (r"\bTune bridge\b", "an unreleased product name"),
    (r"after_instrumentation", "a sponsor's internal roadmap"),
    (r"\bnot yet used\b", "a sponsor's internal roadmap"),
    (r"\d{3,} (?:threads|posts)", "a harvested corpus; cite entries one by one"),
]
for root, _, files in os.walk(DB):
    for f in sorted(files):
        p = os.path.join(root, f)
        try:
            text = open(p, encoding="utf-8").read()
        except Exception:
            continue
        # EVERY occurrence, with its line. re.search reported the first match
        # per pattern per file, so a file holding three leaks showed one: you
        # fixed it, ran again, and found the next. Measured on a file with three
        # occurrences, it named two. Fixing a leak should not be a guessing game
        # played one round at a time.
        for pattern, why in FORBIDDEN:
            for m in re.finditer(pattern, text):
                errors.append("%s:%d: %r must not be published — %s"
                              % (rel(p), text.count("\n", 0, m.start()) + 1,
                                 m.group(0), why))

# --- the figures must match the data --------------------------------------
# Hand-written counts beside the data they describe WILL drift. On 2026-11-24 a
# single afternoon moved them five times, in four files each time, and one wrong
# figure reached a commit message before being caught. The verifier already
# computes every one of them, so from here it also CHECKS them: a count stated
# in the documentation, or a used_on_records in the registry, that disagrees with
# the data is an error and not a stale comment.
#
# What is NOT checked, deliberately: the dated `_state_YYYY_MM_DD` narratives in
# completeness.json. Those are history - they say what was true on a day and keep
# the trail of a number that has been wrong twice. A dated statement is allowed
# to be out of date; that is what the date is for. An UNDATED count is not.
n_doubt_open = n_doubt_resolved = 0
for brand_dir in sorted(os.listdir(devices)) if os.path.isdir(devices) else []:
    bpath = os.path.join(devices, brand_dir)
    if not os.path.isdir(bpath):
        continue
    for dev_dir in sorted(os.listdir(bpath)):
        dpath = os.path.join(bpath, dev_dir, "open-doubt.json")
        if os.path.exists(dpath):
            d = load(dpath) or {}
            if isinstance(d, dict) and d.get("resolved_on"):
                n_doubt_resolved += 1
            else:
                n_doubt_open += 1

# used_on_records is a figure living INSIDE the data, and the one I corrected by
# hand three times in a day.
compte_reel = {}
for brand_dir in sorted(os.listdir(devices)) if os.path.isdir(devices) else []:
    bpath = os.path.join(devices, brand_dir)
    if not os.path.isdir(bpath):
        continue
    for dev_dir in sorted(os.listdir(bpath)):
        cdir = os.path.join(bpath, dev_dir, "claims")
        if not os.path.isdir(cdir):
            continue
        for cf in sorted(os.listdir(cdir)):
            c = load(os.path.join(cdir, cf)) or {}
            for k in (c.get("facts") or {}):
                if not k.startswith("_"):
                    compte_reel[k] = compte_reel.get(k, 0) + 1
            for blk in (c.get("inputs") or {}).values():
                for k in blk:
                    if not k.startswith("_"):
                        kk = "inputs." + k
                        compte_reel[kk] = compte_reel.get(kk, 0) + 1
for champ, e in sorted(registry.items()):
    declare = e.get("used_on_records")
    if declare is not None and declare != compte_reel.get(champ, 0):
        errors.append("schemas/fields.json: %s says used_on_records %d, the data says %d"
                      % (champ, declare, compte_reel.get(champ, 0)))

# --- completeness, counted from vocabulary/completeness.json's OWN field list ---
# The figures that went stale were the completeness ones, and they went stale for
# two reasons that have to be fixed together. First, nothing computed them: the
# guard below covered devices, claims, brands, families, interfaces and doubts,
# and not these - the classic blind spot, a guard that does not look where the
# figure lives. Second, and worse, THE README WROTE THEM AS ENGLISH WORDS -
# "Seventeen records are complete", "the other twenty-five" - and every pattern in
# ATTENDU matches (\d+). A spelled-out number was invisible to this guard by
# construction, so even adding the count would not have caught it. Both are closed
# here: the counts are computed from the vocabulary's own list, so the criterion
# lives in one place, and MOTS_NOMBRES below refuses a spelled-out number in front
# of any noun this guard checks.
#
# PROVEN BY HAND, the way the registry guard next door was, because the mutants run
# against a COPY and this check is skipped there (see count_drifts). Run against the
# real repository on 2026-11-25, before the README was corrected, it printed:
#
#   ERROR : README.md:124: says 25 converters, the data says 136
#   ERROR : README.md:127: "Seventeen records" is a figure spelled out; this guard
#           compares digits, so write it in digits
#   ERROR : README.md:106: "twenty-seven devices" is a figure spelled out; this
#           guard compares digits, so write it in digits
#
# Three figures, and only the first was of a kind the old guard could ever have
# caught. The other two had survived three days and several rewrites of the
# paragraphs around them.
#
# And the completeness count itself was proven live on a COPY of the repository
# with "63 records are complete" changed to 41:
#
#   ERROR : README.md:130: says 41 records complete at level 2, the data says 63
def _complet(niveau, faits, entrees, niveaux):
    for champ in niveaux.get(niveau, []):
        if champ == "inputs":
            if not entrees:
                return False
        elif "." in champ:
            k = champ.split(".", 1)[1]
            if not entrees or not all(k in v for v in entrees.values()):
                return False
        elif champ not in faits:
            return False
    return True


_niveaux = {}
_voc = os.path.join(DB, "vocabulary", "completeness.json")
if os.path.exists(_voc):
    _c = load(_voc) or {}
    for _l in _c.get("levels", []):
        _niveaux[_l.get("level")] = _l.get("fields", [])
n_niv2 = n_niv3 = 0
n_kind = {}
for _marque in sorted(os.listdir(os.path.join(DB, "devices"))):
    _dm = os.path.join(DB, "devices", _marque)
    if not os.path.isdir(_dm):
        continue
    for _mod in sorted(os.listdir(_dm)):
        _dossier = os.path.join(_dm, _mod)
        if not os.path.isdir(_dossier):
            continue
        _faits, _entrees = {}, {}
        _cl = os.path.join(_dossier, "claims")
        if os.path.isdir(_cl):
            for _f in sorted(os.listdir(_cl)):
                if not _f.endswith(".json"):
                    continue
                _o = load(os.path.join(_cl, _f)) or {}
                _faits.update(_o.get("facts") or {})
                _entrees.update(_o.get("inputs") or {})
        if _complet(2, _faits, _entrees, _niveaux):
            n_niv2 += 1
        if _complet(3, _faits, _entrees, _niveaux):
            n_niv3 += 1
        _id = load(os.path.join(_dossier, "identity.json")) or {}
        _k = _id.get("kind")
        if _k:
            n_kind[_k] = n_kind.get(_k, 0) + 1

ATTENDU = [
    (r"(\d+) devices", n_dev, "devices"),
    (r"(\d+) claims", n_claim, "claims"),
    (r"(\d+) brands", len(brands), "brands"),
    (r"(\d+) chip families", len(families), "chip families"),
    (r"(\d+) interfaces", len(ifaces), "interfaces"),
    (r"(\d+) open doubts", n_doubt_open, "open doubts"),
    (r"(\d+) resolved", n_doubt_resolved, "resolved doubts"),
    # case-insensitive since 2026-11-25: « Of the 26 records » sat at the head of a
    # sentence for three days and the pattern was anchored on a lower-case « of ».
    (r"of the (\d+) records", n_dev, "records"),
    (r"(\d+) records are complete on what the device accepts", n_niv2,
     "records complete at level 2"),
    (r"(\d+) records are complete on what it does inside", n_niv3,
     "records complete at level 3"),
    (r"(\d+) converters", n_kind.get("dac", 0), "converters"),
    (r"(\d+) network players", n_kind.get("network_player", 0), "network players"),
]

# A spelled-out number in front of a checked noun is refused outright. It cannot be
# compared - that is the point - so the only safe rule is that these figures are
# written in digits. "Seventeen records are complete" survived three days and five
# rewrites of the surrounding paragraph because no pattern could see it.
# "one" and "two" are deliberately NOT in this list. Written out, they are almost
# always quantifiers in a general statement rather than measurements - "two claims
# that contradict each other can coexist" says what CAN happen, not how many there
# are - and a guard that errors on correct prose is a guard someone switches off.
# The cost is named: a real count that happens to be exactly one or two can still
# go stale unseen. Every figure that actually went stale here was three or more.
MOTS_NOMBRES = ("three four five six seven eight nine ten eleven twelve "
                "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty "
                "thirty forty fifty sixty seventy eighty ninety hundred thousand").split()
NOMS_SURVEILLES = ("devices", "claims", "brands", "chip families", "interfaces",
                   "open doubts", "records", "converters", "network players")
# ONLY against this repository's own database. The mutants run the verifier over a
# COPY with one thing broken, and the documentation describes the real data - so
# checking the docs there would make a mutant fail on this guard instead of the one
# it was written for, and every mutant would then pass for the wrong reason.
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SA_PROPRE_BASE = os.path.abspath(DB) == os.path.abspath(os.path.join(RACINE, "database"))
for doc in (("README.md", os.path.join("docs", "SCHEMA.md"),
             os.path.join("docs", "CONTRIBUTING.md"), os.path.join("docs", "CONSUMING.md"))
            if SA_PROPRE_BASE else ()):
    chemin = os.path.join(RACINE, doc)
    if not os.path.exists(chemin):
        continue
    texte = open(chemin, encoding="utf-8").read()
    # A figure inside `inline code` is a QUOTATION, not an assertion. The
    # documentation has to be able to quote a wrong number in order to explain it -
    # this very guard's own paragraph in docs/SCHEMA.md quotes the stale
    # "Seventeen records are complete" it was written to catch, and was failed by
    # itself for doing so. Same principle as the `_state_YYYY_MM_DD` narratives in
    # completeness.json, which are history and are deliberately not checked.
    # Backticks are blanked rather than removed, so line numbers stay true.
    # The span may wrap across lines, so newlines inside it are kept and everything
    # else blanked: line numbers in the errors stay true.
    texte = re.sub(r"`[^`]*`",
                   lambda m: "".join("\n" if c == "\n" else " " for c in m.group(0)),
                   texte)
    for pattern, vrai, quoi in ATTENDU:
        for m in re.finditer(pattern, texte, re.I):
            if int(m.group(1)) != vrai:
                errors.append("%s:%d: says %s %s, the data says %d"
                              % (doc, texte.count("\n", 0, m.start()) + 1,
                                 m.group(1), quoi, vrai))
    for mot in MOTS_NOMBRES:
        for nom in NOMS_SURVEILLES:
            for m in re.finditer(r"(?<![\w-])%s(?:-\w+)?\s+%s\b" % (mot, nom), texte, re.I):
                errors.append("%s:%d: \"%s\" is a figure spelled out; this guard "
                              "compares digits, so write it in digits"
                              % (doc, texte.count("\n", 0, m.start()) + 1,
                                 m.group(0)))

print("devices    : %d (%s)" % (n_dev, ", ".join("%s %d" % (k, v)
                                                 for k, v in sorted(n_kind.items()))))
print("complete   : %d at level 2, %d at level 3" % (n_niv2, n_niv3))
print("claims     : %d" % n_claim)
print("brands     : %d, chip families: %d, interfaces: %d"
      % (len(brands), len(families), len(ifaces)))
used = sum(1 for e in registry.values() if e.get("used_on_records"))
planned = sum(1 for e in registry.values() if e.get("planned"))
deprecated = sum(1 for e in registry.values() if e.get("deprecated"))
# The three buckets must ACCOUNT FOR the total, or the line is a figure nobody
# re-checks: it read "23 registered, 17 in use, 5 planned, 0 deprecated" while
# 17 + 5 + 0 is 22, and the field it dropped was the one the registry exists to
# surface - carried by no record and not marked planned either.
unaccounted = len(registry) - used - planned - deprecated
print("fields     : %d registered, %d in use, %d planned, %d deprecated%s"
      % (len(registry), used, planned, deprecated,
         (", %d IN NO BUCKET" % unaccounted) if unaccounted else ""))
for w in warnings:
    print("warning    :", w)
for e in errors:
    print("ERROR      :", e)
print("result     : %s" % ("FAIL (%d)" % len(errors) if errors else "ok"))
sys.exit(1 if errors else 0)
