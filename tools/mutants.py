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


def unregistered_field(root):
    p = claim_path(root)
    c = json.load(open(p, encoding="utf-8"))
    c.setdefault("facts", {})["pcm_max_hertz"] = 768000      # faute de frappe
    json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


MUTANTS = [
    ("a field nobody registered", unregistered_field, "not in schemas/fields.json"),
    ("an unreleased product name", forbidden_text, "must not be published"),
    ("a claim with no quoted evidence", drop_quote, "not evidence"),
    ("a null value", put_null, "null at"),
    ("a fact smuggled into identity", fact_in_identity, "which are facts"),
    ("a brand that does not exist", unknown_brand, "is not in database/brands"),
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
    caught = r.returncode != 0 and expect in out
    print("  %-4s %s" % ("ok" if caught else "LIVE", label))
    if not caught:
        bad += 1
        print(out[-500:])
    shutil.rmtree(tmp)

print("\n%d mutant(s) survived" % bad)
sys.exit(1 if bad else 0)
