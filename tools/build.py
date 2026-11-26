# -*- coding: utf-8 -*-
"""Build the published artefact from the tree.

    python3 tools/build.py

Writes dist/odac-<version>.jsonl and dist/latest.json. Nobody consumes the tree;
they consume this. One file parses faster than a thousand, and it keeps traffic
off GitHub — see docs/CONSUMING.md.

Resolution is deliberate and visible: for each (device, field) the claim with the
highest-weighted source wins, ties broken by the later submission. Every resolved
value travels with the source that carries it, and a field claimed with two
different values is listed in `contested` rather than silently flattened.
"""
import re, datetime, gzip, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DB = os.path.join(ROOT, "database")
DIST = os.path.join(ROOT, "dist")

# A measurement outranks a datasheet outranks a forum post. Not a law of nature:
# a starting point, to calibrate once real disagreements exist. Today there are none.
WEIGHT = {"measurement": 90, "datasheet": 70, "maker_reply": 70, "manual": 65,
          "kernel": 60, "probe": 55, "retailer": 35, "listener": 30,
          "forum": 25, "third_party_doc": 20, "curator": 40, "import": 15}

read = lambda p: json.load(open(p, encoding="utf-8"))
lines, contested_total = [], 0


def emit(kind, ident, data):
    lines.append(json.dumps({"type": kind, "id": ident, "data": data},
                            ensure_ascii=False, sort_keys=True))


for folder, kind in (("brands", "brand"), ("chip-families", "chip_family"),
                     ("interfaces", "interface")):
    d = os.path.join(DB, folder)
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            e = read(os.path.join(d, f))
            emit(kind, e.get("id") or f[:-5], e)

# The vocabulary ships too, and it is not optional. These files carry the ORDERED
# rules that derive dac_class, the completeness levels and the shape of a match -
# things a consumer has to implement and cannot infer. Leaving them out while
# README says "do not clone this repository" meant the published channel did not
# carry what it told people to read: on 2026-11-24 two rule corrections in a row,
# one of them changing a device's class, left the artefact byte-identical. Worse
# than missing - the fingerprint is how a consumer decides whether to download
# again, so an unchanged fingerprint actively said "nothing changed".
#
# FOUR of these files are a bare JSON string, not an object, so `e.get("id")`
# would die on them. The filename stem is the id for all of them: a vocabulary
# file is addressed by its name, and nothing inside it is a better key.
vocab = os.path.join(DB, "vocabulary")
for f in sorted(os.listdir(vocab)):
    if f.endswith(".json"):
        emit("vocabulary", f[:-5], read(os.path.join(vocab, f)))

devices = os.path.join(DB, "devices")
for brand in sorted(os.listdir(devices)):
    bpath = os.path.join(devices, brand)
    if not os.path.isdir(bpath):
        continue
    for dev in sorted(os.listdir(bpath)):
        base = os.path.join(bpath, dev)
        if not os.path.isdir(base):
            continue
        ident = read(os.path.join(base, "identity.json"))
        record = dict(ident)
        evidence, claimed = {}, {}
        cdir = os.path.join(base, "claims")
        for cf in sorted(os.listdir(cdir)) if os.path.isdir(cdir) else []:
            if not cf.endswith(".json"):
                continue
            c = read(os.path.join(cdir, cf))
            w = WEIGHT.get((c.get("source") or {}).get("kind", ""), 10)
            for k, v in (c.get("facts") or {}).items():
                claimed.setdefault(k, []).append((w, v, c, cf))
            if c.get("inputs"):
                for iface, blk in c["inputs"].items():
                    for k, v in blk.items():
                        key = "inputs.%s.%s" % (iface, k)
                        claimed.setdefault(key, []).append((w, v, c, cf))
        contested = {}
        for key, entries in claimed.items():
            distinctes = {json.dumps(e[1], sort_keys=True) for e in entries}
            if len(distinctes) > 1:
                # THE RIVAL VALUES TRAVEL WITH THE ARTEFACT, each with its own
                # evidence. Until 2026-11-25 this field carried only the PATH of the
                # contested field, which told a consumer that a disagreement existed
                # and nothing about what it was - so the only way to see the losing
                # value was to clone the repository and read the claims by hand.
                # Disagreement is the centre of this model, not an error state: two
                # sources may say different things and both be honestly reported, and
                # a reader deciding whether to trust the winner needs to see what it
                # beat and on what. The cost is a few kilobytes.
                #
                # One entry per DISTINCT VALUE, not per claim: several claims may
                # support the same value and that is agreement, not rivalry. Each
                # entry carries the strongest claim backing that value, and
                # `claims` says how many back it in all. Sorted by weight, so the
                # value the build chose is first and `chosen` marks it.
                par_valeur = {}
                for e in entries:
                    cle = json.dumps(e[1], sort_keys=True)
                    if cle not in par_valeur or (e[0], e[3]) > (par_valeur[cle][0], par_valeur[cle][3]):
                        par_valeur[cle] = e
                compte = {}
                for e in entries:
                    cle = json.dumps(e[1], sort_keys=True)
                    compte[cle] = compte.get(cle, 0) + 1
                rivales = []
                for cle, (w2, v2, c2, cf2) in par_valeur.items():
                    rivales.append({"value": v2, "weight": w2, "claims": compte[cle],
                                    "claim": cf2, "source": c2.get("source"),
                                    "submitted_by": c2.get("submitted_by"),
                                    "names_subject": c2.get("source_names_subject", None)})
                rivales.sort(key=lambda r: (-r["weight"], r["claim"]))
                rivales[0]["chosen"] = True
                for r in rivales[1:]:
                    r["chosen"] = False
                contested[key] = rivales
            w, v, c, cf = max(entries, key=lambda e: (e[0], e[3]))
            if key.startswith("inputs."):
                _, iface, field = key.split(".", 2)
                record.setdefault("inputs", {}).setdefault(iface, {})[field] = v
            else:
                record[key] = v
            evidence[key] = {"source": c.get("source"), "claim": cf,
                             "submitted_by": c.get("submitted_by"),
                             "names_subject": c.get("source_names_subject", None)}
        doubt = os.path.join(base, "open-doubt.json")
        if os.path.exists(doubt):
            record["open_doubt"] = read(doubt)
        record["evidence"] = evidence
        if contested:
            record["contested"] = {k: contested[k] for k in sorted(contested)}
            contested_total += len(contested)
        emit("device", ident["id"], record)

os.makedirs(DIST, exist_ok=True)
body = "\n".join(lines) + "\n"
fingerprint = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
version = datetime.date.today().strftime("%Y.%m.%d")
# THE NAME CARRIES THE FINGERPRINT, so the URL is addressed by its content and is
# genuinely immutable. The comment that stood here claimed the URL was "versioned
# and never overwritten" while the version was only the DATE - and on 2026-11-24
# that one URL carried TEN different builds, from 349 entries to 347 to 359. A
# consumer who cached it in the morning held content the afternoon no longer
# matched, at an address the documentation called permanent. One build, one URL,
# cacheable for ever.
name = "odac-%s-%s.jsonl" % (version, fingerprint)
open(os.path.join(DIST, name), "w", encoding="utf-8").write(body)

# The repository keeps ONE artefact: the current one. Superseded builds are the
# mirror's business, where an old URL must stay reachable; git serves the tier
# that wants the newest minute, so intermediate builds here would be weight with
# no reader.
for stale in sorted(os.listdir(DIST)):
    if stale.startswith("odac-") and stale.endswith(".jsonl") and stale != name:
        os.remove(os.path.join(DIST, stale))

# latest.json is the only mutable thing, 118 bytes of it: fetch this, compare the
# fingerprint, and download the artefact only when it changed.
json.dump({"version": version, "fingerprint": fingerprint, "url": name,
           "entries": len(lines)},
          open(os.path.join(DIST, "latest.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)

raw = body.encode("utf-8")
packed = gzip.compress(raw, 9)
# Print the compressed size as well: the whole point of a single artefact is
# bandwidth, and the number that travels is the compressed one.
print("dist/%s\n  %d entries, %d bytes, %d gzipped (%.0f%% off)"
      % (name, len(lines), len(raw), len(packed),
         100 - 100.0 * len(packed) / len(raw)))
print("fingerprint %s" % fingerprint)
print("contested fields: %d" % contested_total)

# THE SIZE GUARD LIVES HERE because this is the only tool that knows the size.
# docs/CONSUMING.md prints the raw and compressed figures so a consumer can size a
# download, and on 2026-11-25 it still said "261 228 bytes raw -> 43 762 bytes
# gzipped" while the artefact had reached 2 591 154 - a factor of ten, and the
# figure a decision about the mirror had been taken on. The verifier cannot catch
# it: it reads the database and never builds, so it has no size to compare. The
# lesson of the completeness count applied immediately: PUT THE CHECK WHERE THE
# FIGURE LIVES.
_doc = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "docs", "CONSUMING.md")
if os.path.exists(_doc):
    _t = open(_doc, encoding="utf-8").read()
    _m = re.search(r"([\d\s  ,]+?) bytes raw\s*(?:→|->)\s*([\d\s  ,]+?) bytes gzipped", _t)
    if _m:
        _dit = [int(re.sub(r"[^\d]", "", g)) for g in _m.groups()]
        if _dit != [len(raw), len(packed)]:
            # A GUARD THAT SUGGESTS A LINE IT CANNOT THEN READ. The replacement
            # line was printed with THIN SPACES (U+2009) while the regex above
            # accepted only ordinary ones, so pasting this guard's own
            # suggestion verbatim turned the next run into "no size line to
            # check against" - the guard disabling itself with its own output.
            # Found 2026-11-25 by doing exactly that. Two fixes, because either
            # alone would leave the trap half-set: the suggestion now uses an
            # ordinary space, and the regex accepts thin and non-breaking ones
            # in case a line was already written that way.
            def _esp(n):
                return "{:,}".format(n).replace(",", " ")
            print("ERROR docs/CONSUMING.md: says %d raw and %d gzipped, "
                  "this build is %d and %d" % (_dit[0], _dit[1], len(raw), len(packed)))
            # Print the corrected line ready to paste. A guard that only says "wrong"
            # makes the author compose the replacement, which is where the next wrong
            # figure comes from.
            print("       replace that line with:")
            print("       %s bytes raw   \u2192   %s bytes gzipped   (%.0f%% off)"
                  % (_esp(len(raw)), _esp(len(packed)),
                     100 - 100.0 * len(packed) / len(raw)))
            sys.exit(1)
    else:
        print("ERROR docs/CONSUMING.md: no size line to check against")
        sys.exit(1)
    # AND THE COMPRESSION FACTOR, WHICH DRIFTED BECAUSE IT WAS A WORD.
    # The byte line above has been guarded since the day it was found stale. The
    # sentence four lines below it said "it compresses by a factor of fifteen"
    # and nothing checked it, because a guard that compares digits cannot read
    # an English numeral - the same reason the verifier refuses spelled-out
    # figures before its guarded nouns. Measured 2026-11-25: fifteen against a
    # real 16.5, and a teammate reading a third document found "six" there,
    # true when the artefact was 261 kB. One fact, three values, two documents.
    # The factor also IMPROVES as the artefact grows, so it will drift again on
    # its own - which makes it exactly the kind of figure that must be computed
    # rather than written.
    _fac = len(raw) / float(len(packed))
    _mf = re.search(r"compresses by a factor of\s+(\d+(?:[.,]\d+)?)", _t)
    if not _mf:
        print("ERROR docs/CONSUMING.md: the compression factor is not written in "
              "digits, so nothing can check it. Write it as a figure:")
        print("       it compresses by a factor of %.1f" % _fac)
        sys.exit(1)
    _ditf = float(_mf.group(1).replace(",", "."))
    if abs(_ditf - _fac) > 0.1:
        print("ERROR docs/CONSUMING.md: says it compresses by a factor of %s, "
              "this build compresses by %.1f" % (_mf.group(1), _fac))
        print("       replace that figure with: %.1f" % _fac)
        sys.exit(1)
