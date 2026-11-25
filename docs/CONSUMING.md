# How to consume the database

The database is built into `dist/` by CI after every merge. **Consume the built
artefact, not the tree**: one file parses faster than a thousand, and it keeps
traffic off GitHub.

## Where to fetch it

- **Commercial products**: mirror or cache the artefact on your own
  infrastructure. Do not point your installed base at GitHub.
- **Open source, non-commercial, personal use**: fetch it from the MozAIk Labs
  mirror, served behind a CDN. *(URL to be announced — the mirror is part of the
  transactional side and is not live yet.)*
- **GitHub directly**: only when you genuinely need the last commit — iterative
  development, debugging, reviewing data that has just landed.

## Fetch it only when it has changed

Alongside the artefact, CI publishes a small pointer:

```json
{ "version": "2026.11.24", "fingerprint": "353823dc6d5dde50",
  "url": "odac-2026.11.24-353823dc6d5dde50.jsonl", "entries": 359 }
```

Poll the pointer — a few hundred bytes, short cache — and download the artefact
**only when the fingerprint differs** from the one you hold. That is zero
staleness and almost zero bandwidth, which is better than a mirror that
republishes on a timer and hopes.

**The artefact URL carries the fingerprint, so it is addressed by its content**
and never changes meaning. Cache it for as long as you like; a different build is
a different URL. This paragraph used to promise that and the filename could not
keep it — the version was the date alone, and on 24 November 2026 one URL carried
ten different builds, from 349 entries to 347 to 359. A cache header only ever
cures the future: a client that already holds a URL keeps the file behind it, so
the URL has to mean one thing for ever.

The repository keeps only the current artefact. Old URLs stay reachable on the
mirror, which is what the mirror is for; GitHub serves the tier that wants the
newest minute.

## Ask for it compressed

```
261 228 bytes raw   →   43 762 bytes gzipped   (83% off)
```

It is JSON Lines: highly repetitive, and it compresses by a factor of six. Send
`Accept-Encoding: gzip` and make sure your mirror is configured to honour it —
a server that omits JSON from its compressible types serves this in the clear
and nothing breaks, so nobody notices paying six times the bandwidth. This is
the single largest lever on the cost of consuming the database, larger than
anything in the schema.

## Format

One JSON object per line:

```
{"type":"brand","id":"holo_audio","data":{...}}
{"type":"device","id":"holo-audio/may","data":{...}}
{"type":"interface","id":"usb","data":{...}}
{"type":"chip_family","id":"r2r_ladder","data":{...}}
{"type":"vocabulary","id":"classes","data":{...}}
```

The `vocabulary` entries are the part you have to read rather than index.
`classes` carries the ORDERED rules that derive a device's class and the
predicates they test - the order is the whole content of the classification, so
it is data and not our code. `completeness` defines the four levels, `matching`
the shape of a correspondence between what your own system reports and a record
here, `fields` what a claim may assert. A vocabulary entry's `data` is usually an
object and is **sometimes a bare string**: four of them are a single paragraph,
and a consumer that assumes an object will break on those.

Each device's `data` is the **resolved** record: the winning claim for each
field, with the source that carries it in `evidence`. Competing claims are
resolved at build time by source weight.

## When two sources disagree

A device whose claims disagree on a field carries a `contested` object. That
paragraph above used to end "the resolution and its reason travel with the
record, so you can always see why a value is the one you got", and until
25 November 2026 that was **not true**: `contested` was a list of field PATHS.
You could see that a disagreement existed and nothing about what it was, so the
only way to read the losing value was to clone the repository.

It now carries the rival values:

```json
"contested": {
  "bits": [
    {"value": 24, "weight": 70, "claims": 1, "chosen": true,
     "claim": "003-specification-du-fabricant.json",
     "submitted_by": "curator", "names_subject": true,
     "source": {"kind": "datasheet", "url": "...", "quote": "...", "read_on": "..."}},
    {"value": 16, "weight": 15, "claims": 1, "chosen": false,
     "claim": "001-catalogue-initial.json", "submitted_by": "import",
     "names_subject": null, "source": {"kind": "import", "quote": "...", "read_on": "..."}}
  ]
}
```

One entry per **distinct value**, not per claim: several claims supporting the
same value is agreement, not rivalry, and `claims` says how many back each one.
Entries are sorted by weight, so the value the build chose is first and `chosen`
marks it. The key is the field path, `inputs.<interface>.<field>` for a per-input
field.

**Disagreement is the centre of this model, not an error state.** Two sources may
say different things and both be honestly reported - one of the three live cases
is a maker's product page saying an optical input takes 96 kHz against the same
maker's own manual saying 192. A reader deciding whether to trust the winner needs
to see what it beat and on what. The cost of carrying all of it was measured when
it was added: 4,820 bytes across the whole artefact.
