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
import datetime, gzip, hashlib, json, os, sys

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
        contested = []
        for key, entries in claimed.items():
            if len({json.dumps(e[1], sort_keys=True) for e in entries}) > 1:
                contested.append(key)
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
            record["contested"] = sorted(contested)
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
