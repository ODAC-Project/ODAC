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
{ "version": "2026.11.24", "fingerprint": "d25a23b98e33b87b",
  "url": "odac-2026.11.24.jsonl" }
```

Poll the pointer — a few hundred bytes, short cache — and download the artefact
**only when the fingerprint differs** from the one you hold. That is zero
staleness and almost zero bandwidth, which is better than a mirror that
republishes on a timer and hopes.

The artefact URL is **versioned**, never overwritten. A cache header only ever
cures the future: a client that already holds the old URL keeps the old file.

## Format

One JSON object per line:

```
{"type":"brand","id":"holo_audio","data":{...}}
{"type":"device","id":"holo_may","data":{...}}
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
field, with the source that carries it. Competing claims are resolved at build
time; the resolution and its reason travel with the record, so you can always
see why a value is the one you got.
