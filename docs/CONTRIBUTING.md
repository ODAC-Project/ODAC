# Contributing

A contribution is **one new file**. You will not edit anyone else's.

## Adding a fact about a device

Create `database/devices/<brand>/<device>/claims/NNN-short-name.json`:

```json
{
  "source": {
    "kind": "measurement",
    "title": "Bench measurement, Holo May KTE",
    "quote": "PCM output measured 6.0 dB below DSD output at the same volume setting",
    "read_on": "2026-11-24"
  },
  "source_names_subject": true,
  "submitted_by": "a-pseudonym-you-choose",
  "submitted_on": "2026-11-24",
  "facts": { "pcm_dsd_level_offset_db": -6.0 }
}
```

## Signing off

Every commit in a pull request carries a sign-off line:

```
Signed-off-by: Your Name <your@email>
```

`git commit -s` adds it. It is the [Developer Certificate of
Origin](https://developercertificate.org/): you state that you have the right to
submit this work and that it may be published under this repository's licences —
CC BY-SA 4.0 for the data, Apache-2.0 for the code, and the logo under neither. **There is no contributor licence
agreement to sign.** Contributions made through the website's form record the
same agreement with a checkbox, and the pull request it opens repeats it.

## What CI will refuse

- **A claim with no `quote`.** A source that does not quote the words carrying
  the fact is an address, not evidence.
- **A quoted fragment longer than 300 characters.** Evidence is the words
  carrying the fact, not the panel around them. The worked example above is 70
  characters and the median in this database is 39. A `quote` field may be long
  — it is your account of a page, and most of it is your own words — but no
  single run of text inside `« »` may pass 300. Keep the line that states the
  figure and drop the rest. This is a quotation rule, not a licensing one:
  citing is not licensing, however short the quote.
- **A `neighbour` alias naming a device that has its own record.** A neighbour
  resolves a product nothing else in the database holds. Once that product has
  a record, the alias sends its name to the wrong one and asserts the wrong
  figures for it. Put the relation in a note instead. Records whose `model` is
  `generique` or `unknown` are exempt, because saying what an identity does
  *not* resolve to is the whole point of them.
- **`null` anywhere.** Leave the key out if nobody filled it in; write
  `"unknown"` if the question was asked and nobody knows. They are different
  facts about where to spend effort.
- **A file that is not valid JSON**, or a device with no `identity.json`.
- **A brand or interface that does not exist** in `database/`.

## What a human will ask you

**Does your source name *this* device?** A source about a whole range, cited for
one model, is admissible — set `source_names_subject` to `false` and say so. It
is the most common error in this data: one model's figures asserted for every
model in a range.

**Do you own the device?** Say so. A fact from someone holding the hardware
outranks a forum quote, and the fields that matter most — whether the DSD path
is direct, the real ladder depth, the PCM/DSD level offset — cannot be obtained
any other way.

## What we will not accept

**Bulk imports from someone else's compiled list.** In the European Union a
database carries a *sui generis* right covering the investment made in
assembling it. One fact at a time, each with its own source.

**A USB identity you did not read from the device.** An invented identity makes
software assert a technology, a modulator order and a level offset for the wrong
hardware. A wrong record is worse than no record.
