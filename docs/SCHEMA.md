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
`network_player`), `brand`, `model`, optional `aliases`, the exact USB
identities, and `superseded_by` when a record has been replaced.

**The `id` IS the path**: `holo-audio/may`, never a flat `holo_may` beside a
directory that says something else. One identity, one spelling, and a guard that
refuses the two drifting apart — because the slug is **frozen**: it is never
renamed. If the structure turns out wrong, a new record is created and the old
one marked `superseded_by`.

**An alias says HOW a name relates to the record**, and this is not decoration.
Untyped, the list merged three different things: a `spelling` is the same object
written differently, an `edition` is a variant no fact yet distinguishes, and a
`neighbour` is a **different product** resolved here only for want of its own
record. Before they were typed, a match on "Spring 2" would have asserted the
Spring 3's facts for another generation, and a headphone amplifier sat beside a
converter as though they were one device — they share a USB identity, which is
why they were listed together at all.

There is no range level between brand and model, and that is measured rather than
forgotten: of the 138 records, one brand has two or more models on the same
silicon, and its maker does not name them as a range. A level with no occupant is
a mechanism that cannot be wrong because nothing exercises it. The rule for
creating one — same silicon **and** the maker names the grouping — is decided and
waiting for its first real case. Anything that could be contested belongs in a claim. The verifier
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
exists*. **25 fields registered today: 17 in use, 7 planned, 0 deprecated — and one in no
bucket at all.** `device_correction_profile` carries no record and is not marked
planned, so the three counts did not add up to the total, and said 23 for 22. The
registry is meant to expose exactly that; the sentence describing it was hiding it.

## What a record must carry: four levels

| level | what it establishes | who can |
|---|---|---|
| **1** identified | brand, model, evidence, and a USB identity **or a resolved match** | a USB descriptor, else a person |
| **2** what it accepts | the ceilings, per input | **a probe, free** |
| **3** what it does inside | family, DSD behaviour, level offset, real depth, bypass | **a person** |
| **4** measured | a correction profile | an instrument |

**A probe gives the whole of level 2 and nothing of level 3.** Asking a device
what it accepts never reveals what it does with it. That rule is data —
`probe_can_establish` in the registry — not something the code remembers.

## Level 1 does not come from the announcement

A record enters at level 1 with a USB identity **or** a resolved match. The first
gate asked for a USB identity alone, and that excluded every device the field can
actually report: a network player asks the network, and a UPnP announcement carries
no USB descriptor.

It is worse than a missing field. **The announcement names the renderer — the
software serving the stream — and not the converter behind it.** A bridge or daemon
sitting in front of a DAC announces itself, so one announced string covers many
different devices, and the brand announced is frequently not the brand of the
hardware. Anyone can verify this on any UPnP network.

So the correspondence is a claim like any other, with evidence, contestable, and
never inferred from the string: `device_match`, whose shape is in
`database/vocabulary/matching.json`. Three things follow.

- **It is a row, not a column**, because it is many-to-many in both directions: one
  string covers many devices, and one device announces many strings as firmware and
  protocol vary.
- **It says what it resolves TO** — brand, range or device. An identity is often
  generic: `ta-dac200` carries one USB identity across four products, and
  `mola-mola-generique` carries a VID/PID whose model is `unknown`. A match claiming
  a device where the evidence establishes a range would assert a chip, a modulator
  order and a level offset for the wrong product.
- **Withdrawing a wrong match moves no fact.** Delete the row; the device keeps
  every assertion it had. That is the whole reason it is not a field on the device.

A MAC prefix is far more reliable than a name and still not a brand: an OUI gives
the maker of the network card, which for a shelf of streamers built on the same
single-board computer is not the audio brand. Corroboration, never evidence on its
own. And only the first three bytes are ever stored, truncated on receipt — the
other three identify one person's machine and are not ours.

## The figures are checked, not trusted

A count written beside the data it describes drifts. On 24 November 2026 a single
afternoon moved these figures five times, four files each time, and one wrong
number reached a commit message before anyone caught it. The verifier already
computed every one of them, so now it also **compares**: a count stated in
`README.md` or in these docs, and every `used_on_records` in the registry, must
equal what the data holds, or CI fails.

The dated `_state_YYYY_MM_DD` narratives in `completeness.json` are deliberately
**not** checked. They are history — they say what was true on a day, and they
keep the trail of a number that has been wrong twice and had its denominator
move once. A dated statement is allowed to be out of date; that is what the date
is for. An undated count is not.

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

**Four fields are now asserted per input**, and three of them arrived together on
2026-11-24 with the first record of the population pass. `inputs.pcm_max_hz` is on
65 records; `inputs.bits` on 4, `inputs.native_dsd_possible` on 3 and
`inputs.dop_possible` on 2 — all on one device, because one maker's specification
table distinguished its inputs and nothing had ever asked the question before.
The depth steps above a rate and the channel count are still registered as planned
and carried by nobody, and `inputs.dsd_reconverted_to_pcm` joined them on
2026-11-24.

**That last one is a deliberate asymmetry, not an oversight.** Whether DSD is
brought back to PCM can differ by input, because the input receiver is where it
differs: a device may take native DSD over USB and only DoP over S/PDIF, and
unwrapping DoP is the moment a receiver may hand PCM to the converter. The
transport already varies that way here — `native_dsd_possible` is false on
eversolo/dmp-a8's S/PDIF and true on its USB — so the field deciding whether to
send DSD at all can vary with it. A per-input value overrides the device-level
one for that input, which overrides the chip family's: the same three steps as
every other field.

**`dsd_direct` is NOT following it**, and the reason is the whole point. That
field asks whether the converter is reached unfiltered, which is a property of
the conversion stage and the same whichever socket the signal arrived by —
`classes.json` puts it plainly: *a converter with a direct DSD path still has one
when it is reached over AirPlay; the transport is what cannot carry DSD*.
Splitting both would re-merge the two fields that were painfully separated on
2026-11-20.

It starts empty on purpose. A sweep of thirteen manufacturers' own pages found no
device whose maker says it re-converts on one input and not another. The case is
real and this catalogue has not met it; registering it as planned means the first
person who meets it knows they have found something, instead of contradicting the
device-level value in silence.

`inputs.channels` is the newest of them, and it carries a warning rather than a
hole: **what a device accepts is not what a consumer will send.** A player's own
channel setting is the boundary of its cost model, so a consumer may refuse a
six-channel source while this field reads 8. Reading the 8 as permission to
answer for eight channels is the error already paid when `dsd_direct` and
`dsd_reconverted_to_pcm` were one field — two questions that look like one, about
two different objects. It is registered as planned and deliberately left out of
level 2's criterion, which names `inputs` as a whole: no decision served here
needs the count, and the 17 of 25 complete at level 2 did not move because of it.

**Level 3 is empty: no record is complete on what the device does inside.**
Seven know the real ladder depth, one an internal bypass rate, sixteen the
PCM/DSD level offset. That is the gap this database exists to close, and no
amount of scraping closes it.

**No record is at level 4.** That needs an instrument.

**`device_settings` is typed two ways** — a list of objects on one record, prose
on four others. The registry says list; the four others are wrong and should be
converted.

**Almost every claim still has source kind `import`.** The exceptions are the
records of the population pass, whose source is a maker's published specification
and says so: `datasheet`, weight 70 against import's 15. They are also the first
claims ever to set `source_names_subject`, which CONTRIBUTING has asked for from
the beginning. The exact split is in the verifier's output rather than written
here, because a figure in prose beside the data drifts and this one moves with
every batch. The evidence rule is formally
satisfied — every claim quotes something — but no claim yet carries a real kind
(`measurement`, `manual`, `maker_reply`…). Splitting the imported batches into
per-field claims with their real source is the first real curation work.
