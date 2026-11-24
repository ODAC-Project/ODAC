# The data model

What is in this database, where each thing lives, and how we know nothing has
been forgotten. **Written from a measurement of the files, not from memory** — a
list written from memory knows only the fields its author remembers, and this
catalogue has already lost five that way.

## The five things the database talks about

| | lives in | what it is |
|---|---|---|
| **device** | `database/devices/<brand>/<device>/` | a converter or a network player |
| **device input** | a claim's `inputs.<interface>` | that device **through** one input |
| **brand** | `database/brands/<brand>.json` | the maker |
| **chip family** | `database/chip-families/<family>.json` | the silicon, and what it fixes |
| **interface** | `database/interfaces/<interface>.json` | a transport, and what it can carry |

A converter's ceilings are not properties of the converter but of the converter
**through an input**: a part that takes 768 kHz over USB commonly stops at
96 kHz over optical. That is why a device input is its own subject.

## A device is a directory

```
database/devices/holo-audio/holo-may/
  identity.json              what NAMES it — never a fact
  claims/001-….json          a batch of facts, with ONE piece of evidence
  claims/002-….json          another batch, another piece of evidence
  open-doubt.json            a doubt worth writing down
```

**`identity.json` carries no facts.** It holds `id`, `kind` (`dac` or
`network_player`), `brand`, `model`, optional `aliases`, and the exact USB
identities. Anything that could be contested belongs in a claim. The verifier
refuses a fact found in an identity, because two places to assert one thing is
two places to get it wrong.

**A claim is one batch of facts sharing one piece of evidence.**

```json
{
  "source": { "kind": "measurement", "quote": "…the words carrying the fact…",
              "read_on": "2026-11-24" },
  "source_names_subject": true,
  "submitted_by": "handle",
  "submitted_on": "2026-11-24",
  "facts":  { "pcm_dsd_level_offset_db": -6.0 },
  "inputs": { "usb": { "pcm_max_hz": 1536000 } }
}
```

Three things follow from a fact being a **file** rather than a line in a record,
and they are the whole reason for this shape: a contribution is a new file, so
two contributors never conflict; a claim reviews on its own instead of as a diff
inside a forty-line record; and **two claims that contradict each other coexist**
instead of overwriting. Resolution happens when the artefact is built, not when
the file is written.

## Three states, and `null` is forbidden

- **No entry** — nobody filled it in.
- **`"unknown"`** — the question was asked and nobody knows. A consumer takes the
  conservative branch.
- **A value** — known.

These are different facts about where to spend effort. `null` carried the first
two at once, and in one record it silently erased a chip family's bit depth.

One type deserves its own name: **`boolean_or_reason`**. `dsd_direct` is `true`,
`false`, or the *name* of the reason nobody knows yet — `to_be_measured`,
`firmware_dependent`. That is not `"unknown"`: it says the question is live and
why. It is also the state that makes a consumer refuse to send DSD, so flattening
it to a boolean would erase the refusal.

## The field registry is what keeps nothing forgotten

**`schemas/fields.json` registers every field a claim may assert**, with its
type, its completeness level, and whether a probe can establish it.
`tools/verifier.py` refuses a claim asserting anything else, and a mutant proves
that check fires. A typo like `pcm_max_hertz` is caught at the pull request
rather than becoming a value nobody ever reads.

The registry also carries what is **not** used:

- `used_on_records: 0` with `planned: true` — the field is part of the model and
  no record carries it yet;
- `deprecated: true` — the field exists in the data and should go.

That is the difference between *not yet filled in* and *nobody remembers it
exists*. **23 fields registered today: 17 in use, 5 planned, 0 deprecated.**

## What a record must carry: four levels

| level | what it establishes | who can |
|---|---|---|
| **1** identified | brand, model, evidence, USB identity | the driver, free |
| **2** what it accepts | the ceilings, per input | **a probe, free** |
| **3** what it does inside | family, DSD behaviour, level offset, real depth, bypass | **a person** |
| **4** measured | a correction profile | an instrument |

**A probe gives the whole of level 2 and nothing of level 3.** Asking a device
what it accepts never reveals what it does with it. That rule is data —
`probe_can_establish` in the registry — not something the code remembers.

## What CI refuses

- a claim with no quoted evidence — a source that does not quote is an address;
- `null`, anywhere;
- a fact smuggled into an identity;
- a field not in the registry;
- a brand, interface or chip family that does not exist;
- a device with no `kind`, or a kind outside `dac` / `network_player`;
- text that must not be published (see `docs/CONTRIBUTING.md`).

Each of those has a mutant that breaks the data on purpose and checks the
verifier dies. A guard nobody has seen fire is a guard nobody knows is wired up.

## What is knowingly missing

Measured, so that it is a list and not a feeling.

**`provenance` is documented and does not exist.** Which of the four inlets a
fact came through — the device probed, the maker in writing, a listener, an agent
— is described in `database/vocabulary/governance.json` as central to the model,
and no record carries it. Today a claim says *who submitted* and *what the source
is*, which is close but not the same question.

**Only one field is ever asserted per input.** `inputs.pcm_max_hz`, on 68
records. The word width, the depth steps above a rate, and whether the input
carries native DSD or DoP are registered as planned and never filled.

**Level 3 is empty: no record is complete on what the device does inside.**
Seven know the real ladder depth, one an internal bypass rate, sixteen the
PCM/DSD level offset. That is the gap this database exists to close, and no
amount of scraping closes it.

**No record is at level 4.** That needs an instrument.

**`device_settings` is typed two ways** — a list of objects on one record, prose
on four others. The registry says list; the four others are wrong and should be
converted.

**All 48 claims have source kind `import`.** The evidence rule is formally
satisfied — every claim quotes something — but no claim yet carries a real kind
(`measurement`, `manual`, `maker_reply`…). Splitting the imported batches into
per-field claims with their real source is the first real curation work.
