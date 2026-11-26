# -*- coding: utf-8 -*-
"""Break the data on purpose, and check the verifier dies.

    python3 tools/mutants.py

A guard nobody has seen fire is a guard nobody knows is wired up. Twice in this
project's history a check was written, looked right, and refused nothing.
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "database")
ANY_DEVICE = None
for b in sorted(os.listdir(os.path.join(DB, "devices"))):
    for d in sorted(os.listdir(os.path.join(DB, "devices", b))):
        ANY_DEVICE = os.path.join("devices", b, d)
        break
    if ANY_DEVICE:
        break


def claim_path(root):
    cdir = os.path.join(root, ANY_DEVICE, "claims")
    return os.path.join(cdir, sorted(os.listdir(cdir))[0])


def drop_quote(root):
    p = claim_path(root)
    c = json.load(open(p, encoding="utf-8"))
    c["source"].pop("quote", None)
    json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def put_null(root):
    p = claim_path(root)
    c = json.load(open(p, encoding="utf-8"))
    c.setdefault("facts", {})["bits"] = None
    json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def fact_in_identity(root):
    p = os.path.join(root, ANY_DEVICE, "identity.json")
    i = json.load(open(p, encoding="utf-8"))
    i["pcm_max_hz"] = 768000
    json.dump(i, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def unknown_brand(root):
    p = os.path.join(root, ANY_DEVICE, "identity.json")
    i = json.load(open(p, encoding="utf-8"))
    i["brand"] = "nobody"
    json.dump(i, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def duplicate_brand_file(root):
    # A SECOND FILE FOR ONE MAKER. This passed every check until 2026-11-25,
    # when a script that could not find cambridge.json invented
    # cambridge-audio.json beside it. The guard cannot be "a brand file nobody
    # cites": most brand files here are census entries with no records at all.
    # It is the repeated display name. Three real duplicates were sitting in the
    # tree when the guard was added - cyrus, geshelli and jds - so this mutant
    # protects a repair, not a hypothetical.
    d = os.path.join(root, "brands")
    src = os.path.join(d, sorted(f for f in os.listdir(d) if f.endswith(".json"))[0])
    o = json.load(open(src, encoding="utf-8"))
    o["id"] = (o.get("id") or "x") + "_bis"
    json.dump(o, open(os.path.join(d, "zz-duplicate.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)


PASSES = object()  # sentinel: this mutant must leave the verifier PASSING


def near_duplicate_brand_name(root):
    # THE SAME MAKER UNDER TWO NAMES. The exact-name guard caught three pairs
    # on 2026-11-25 and left three behind: "Apogee Digital" against "Apogee
    # Electronics", "MOTU" against "MOTU (Mark of the Unicorn)", "Pioneer"
    # against "Pioneer Electronics". A normalised comparison catches those.
    # The escape hatch is tested too, below.
    d = os.path.join(root, "brands")
    src = os.path.join(d, sorted(f for f in os.listdir(d) if f.endswith(".json"))[0])
    o = json.load(open(src, encoding="utf-8"))
    o["id"] = (o.get("id") or "x") + "_ter"
    o["name"] = (o.get("name") or "X") + " Electronics"
    json.dump(o, open(os.path.join(d, "zz-near-duplicate.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)


def escape_hatch_that_does_not_work(root):
    # The SAME mutant, but declaring itself a different maker. The guard must
    # stand down, so the verifier must PASS - which means this mutant is
    # expected to survive, and the suite asserts the opposite of usual. An
    # escape hatch nobody tests is a hole, not a hatch.
    near_duplicate_brand_name(root)
    p = os.path.join(root, "brands", "zz-near-duplicate.json")
    o = json.load(open(p, encoding="utf-8"))
    o["_not_the_same_maker_as"] = "a deliberate test of the escape hatch"
    json.dump(o, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def unknown_interface(root):
    p = claim_path(root)
    c = json.load(open(p, encoding="utf-8"))
    c["inputs"] = {"smoke_signal": {"pcm_max_hz": 44100}}
    json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def empty_claim(root):
    p = claim_path(root)
    c = json.load(open(p, encoding="utf-8"))
    c.pop("facts", None)
    c.pop("inputs", None)
    json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def broken_json(root):
    open(claim_path(root), "w", encoding="utf-8").write("{ not json")


def forbidden_text(root):
    p = claim_path(root)
    c = json.load(open(p, encoding="utf-8"))
    c["source"]["quote"] = c["source"]["quote"] + " Works with Sendspin."
    json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def two_leaks_in_one_file(root):
    """Two occurrences of the SAME pattern, on two different lines."""
    p = claim_path(root)
    c = json.load(open(p, encoding="utf-8"))
    c["source"]["quote"] = c["source"]["quote"] + " Works with Sendspin."
    c.setdefault("notes", {})["_also"] = "And Sendspin again, on another line."
    json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def id_not_the_path(root):
    """The id and the directory say different things - two homes for one key."""
    p = os.path.join(root, ANY_DEVICE, "identity.json")
    i = json.load(open(p, encoding="utf-8"))
    i["id"] = "something/else"
    json.dump(i, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def untyped_alias(root):
    """A bare string where an alias must say HOW the name relates."""
    p = os.path.join(root, ANY_DEVICE, "identity.json")
    i = json.load(open(p, encoding="utf-8"))
    i["aliases"] = ["Some Other Name"]
    json.dump(i, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def count_drifts(root):
    """Remove one asserted fact, so the registry's used_on_records no longer matches.

    This one CAN be a mutant because schemas/fields.json is not copied: the
    verifier reads the registry from its own path and the data from `root`.
    The documentation check next to it cannot be mutant-tested for the same
    reason in reverse - the mutants run against a COPY, and the docs describe the
    real database, so that guard is deliberately skipped there. It was proven by
    hand instead: a README saying 26 devices against 25 in the data fails with
    "README.md:124: says 26 devices, the data says 25".
    """
    p = claim_path(root)
    c = json.load(open(p, encoding="utf-8"))
    for k in list(c.get("facts") or {}):
        if not k.startswith("_"):
            c["facts"].pop(k)
            break
    json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def unregistered_field(root):
    p = claim_path(root)
    c = json.load(open(p, encoding="utf-8"))
    c.setdefault("facts", {})["pcm_max_hertz"] = 768000      # faute de frappe
    json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def submitted_by_is_an_address(root):
    """Put an email address in submitted_by.

    A contributor is a chosen pseudonym or "anonymous", never an address. This
    field is published in the artefact, mirrored, and kept in every old artefact
    the mirror holds - it is the one field where a mistake cannot be withdrawn.
    """
    p = claim_path(root)
    c = json.load(open(p, encoding="utf-8"))
    c["submitted_by"] = "someone@example.com"
    json.dump(c, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def quote_fragment_too_long(root):
    """Stretch one quoted fragment past the ceiling.

    THE FIRST VERSION OF THIS GUARD MEASURED THE WHOLE `quote` FIELD, which is
    39% our own connective prose. It would have refused 231 records that were
    never at fault, and it would still have passed a 2 000-character panel
    hidden inside a longer account. This mutant is written on the fragment for
    that reason: it puts a single 399-character take inside guillemets in a
    field that is otherwise short, which is precisely the shape the field-length
    version could not see.
    """
    p = claim_path(root)
    c = json.load(open(p, encoding="utf-8"))
    c["source"]["quote"] = "The maker's page says \u00ab %s \u00bb" % ("word " * 80).strip()
    json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def _deux_fiches_dune_meme_marque(root):
    """Find two devices of one brand: (identity path of A, model name of B)."""
    dev = os.path.join(root, "devices")
    for b in sorted(os.listdir(dev)):
        bp = os.path.join(dev, b)
        if not os.path.isdir(bp):
            continue
        noms = []
        for d in sorted(os.listdir(bp)):
            ip = os.path.join(bp, d, "identity.json")
            if os.path.exists(ip):
                noms.append((ip, json.load(open(ip, encoding="utf-8"))))
        reels = [(ip, i) for ip, i in noms
                 if str(i.get("model", "")).strip().lower() not in ("generique", "unknown")]
        if len(reels) >= 2:
            return reels[0][0], reels[1][1]["model"]
    raise AssertionError("no brand with two non-generic records")


def neighbour_with_its_own_record(root):
    """Alias a device to another device that HAS a record, typed neighbour.

    Done twice by hand in one batch on 2026-11-25 (bryston/bda-3 and
    bryston/bda-3-14 aliased each other) and nothing saw it: aliases live in
    identity, where the evidence rule does not reach, and the duplicate-brand
    guard reads brand files. Either name then resolved to whichever file was
    read first, asserting one product's figures for the other.
    """
    ip, autre_modele = _deux_fiches_dune_meme_marque(root)
    i = json.load(open(ip, encoding="utf-8"))
    i.setdefault("aliases", []).append({"text": autre_modele, "relation": "neighbour"})
    json.dump(i, open(ip, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def a_generic_record_may_name_its_neighbours(root):
    """The SAME alias on a generic record, which must still be accepted.

    This is the main case, not a loophole: chord/generique carries one USB
    identity across several products and names Qutest and Dave as neighbours ON
    PURPOSE - the record exists to say that the identity does not resolve to a
    product. If the exemption silently stopped working, every such record would
    start failing the build; if a typo made it inert, nobody would know which
    way it had broken. So it gets its own mutant, asserting a PASS.
    """
    ip, autre_modele = _deux_fiches_dune_meme_marque(root)
    i = json.load(open(ip, encoding="utf-8"))
    i["model"] = "unknown"
    i.setdefault("aliases", []).append({"text": autre_modele, "relation": "neighbour"})
    json.dump(i, open(ip, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def record_under_a_refused_brand(root):
    """Write a device under a brand whose file carries _refused.

    Done for real on 2026-11-25: two Okto Research records written against a
    refusal commited two hours earlier, verdict DISCARDED, the register entry
    naming the very input row that had been thrown away. It was possible because
    the check made beforehand looked for _refused in database/brands/*.json and
    found seventeen, while the register in the vocabulary held twenty-six - nine
    of them with a silent brand file, Okto among them. The remote is public and
    empty, so the first push would have published them.
    """
    bdir = os.path.join(root, "brands")
    cible = None
    for f in sorted(os.listdir(bdir)):
        if not f.endswith(".json"):
            continue
        e = json.load(open(os.path.join(bdir, f), encoding="utf-8"))
        if any(k.startswith("_refused") for k in e):
            cible = e.get("id") or f[:-5]
            break
    assert cible, "no refused brand in the data"
    d = os.path.join(root, "devices", cible.replace("_", "-"), "essai", "claims")
    os.makedirs(d)
    json.dump({"id": "%s/essai" % cible.replace("_", "-"), "kind": "dac",
               "brand": cible, "model": "Essai"},
              open(os.path.join(d, "..", "identity.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    json.dump({"source": {"kind": "datasheet", "url": "https://exemple.test",
                          "quote": "\u00ab 192 kHz \u00bb", "read_on": "2026-11-25"},
               "source_names_subject": True, "submitted_by": "curator",
               "submitted_on": "2026-11-25", "facts": {"bits": 24}},
              open(os.path.join(d, "001-essai.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)


MUTANTS = [
    ("a field nobody registered", unregistered_field, "not in schemas/fields.json"),
    ("a registry count that drifted", count_drifts, "used_on_records"),
    ("a contributor named by their address", submitted_by_is_an_address,
     "looks like an email address"),
    ("an id that is not its path", id_not_the_path, "The id IS the path"),
    ("an alias that does not say how it relates", untyped_alias, "must be {text, relation}"),
    ("a neighbour that has its own record", neighbour_with_its_own_record,
     "has its own record"),
    ("a generic record naming its neighbours", a_generic_record_may_name_its_neighbours,
     PASSES),
    ("an unreleased product name", forbidden_text, "must not be published"),
    ("two leaks in one file, both named", two_leaks_in_one_file,
     lambda out: out.count("must not be published") >= 2),
    ("a claim with no quoted evidence", drop_quote, "not evidence"),
    ("a verbatim fragment past the ceiling", quote_fragment_too_long,
     "ceiling for one quoted fragment"),
    ("a null value", put_null, "null at"),
    ("a fact smuggled into identity", fact_in_identity, "which are facts"),
    ("a brand that does not exist", unknown_brand, "is not in database/brands"),
    ("a record under a refused brand", record_under_a_refused_brand,
     "a brand that is REFUSED"),
    ("two brand files for one maker", duplicate_brand_file, "all claim the name"),
    ("one maker under two names", near_duplicate_brand_name,
     "probably one maker under two names"),
    ("the escape hatch for two real makers", escape_hatch_that_does_not_work, PASSES),
    ("an interface that does not exist", unknown_interface, "is not in database/interfaces"),
    ("a claim that asserts nothing", empty_claim, "asserts nothing"),
    ("a file that is not JSON", broken_json, "not valid JSON"),
]

bad = 0
for label, mutate, expect in MUTANTS:
    tmp = tempfile.mkdtemp()
    root = os.path.join(tmp, "database")
    shutil.copytree(DB, root)
    mutate(root)
    r = subprocess.run([sys.executable, os.path.join(HERE, "verifier.py"), root],
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    # `expect` is a substring, or a callable when the point is HOW MANY times
    # the guard spoke - a guard that reports one leak out of three is wired up
    # and still unusable.
    if expect is PASSES:
        # AN ESCAPE HATCH NOBODY TESTS IS A HOLE. Most mutants assert that the
        # verifier REFUSES; this kind asserts that it accepts - that a declared
        # exemption really does stand the guard down. Without it, the hatch
        # could silently stop working and every exempted pair would start
        # failing the build, or worse, a typo in the key name would make the
        # exemption inert and nobody would know which way it had broken.
        caught = r.returncode == 0
    else:
        caught = r.returncode != 0 and (expect(out) if callable(expect) else expect in out)
    print("  %-4s %s" % ("ok" if caught else "LIVE", label))
    if not caught:
        bad += 1
        print(out[-500:])
    shutil.rmtree(tmp)

print("\n%d mutant(s) survived" % bad)
sys.exit(1 if bad else 0)
