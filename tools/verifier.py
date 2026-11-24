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
IDENTITY_KEYS = {"id", "kind", "brand", "model", "aliases", "usb"}
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

print("devices    : %d" % n_dev)
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
