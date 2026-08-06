# Phase 1h — has the distance these elk migrate changed, and can a collar record answer that at all?

**Status:** pre-registered 2026-08-06. Written before any displacement, path length or trend has
been computed. What *was* looked at first is in §1 and it is not nothing: the fix intervals and the
seasonal coverage were measured, because the design depends on a confound that had to be shown to
exist before it could be designed around.

## Why this note exists

Six million track fixes across seven sources have produced **zero findings**. They are the largest
unused asset in the lake, and the ledger has an aerial claim from radar, a marine claim from trawls
and a terrestrial claim from birds — no mammal, anywhere, despite the lake holding seven mammal
studies.

There is a reason for the silence and it is a good one. [Phase 1d](phase1d-tracks.md) found that
changing the collar moves a measured migration date by **46.8 days** on the same caribou, which
closed timing questions for track data. This note asks whether *anything* survives that, and
proposes a measure chosen specifically because the instrument cannot reach it.

## 1. What was looked at before this was written

Structure and sampling only, from `lake.reader.scan` over `TRACK`.

| source | rows | animals | span | years |
| --- | --- | --- | --- | --- |
| `movebank_yahatinda_elk` | 1,784,888 | 206 | 2001-12 – 2024-12 | 23 |
| `movebank_svalbard_reindeer` | 1,317,837 | 116 | 2009-04 – 2022-10 | 14 |
| `movebank_missouri_bison` | 720,077 | 45 | 2012-10 – 2026-02 | 11 |

**The confound, measured.** Median fix interval per year, elk: **0.25 h to 13 h, a 52-fold change**
across the record. Svalbard reindeer 4-fold, bison 6-fold. A path length, a speed, or anything else
accumulated along a track scales with how often the collar reported, so for the elk it is
uninterpretable — Phase 1d's lesson in a second form.

**The escape, checked for coverage.** 341 elk animal-years hold a fix in both a February window and
an August window, spread over 17 distinct years, 14–44 per year from 2014 onward.

What was **not** looked at: any position, any distance, any displacement, any per-year value of
anything, and nothing at all from the reindeer beyond the fix intervals above.

## 2. The estimand

For each animal *i* in year *y*, the **great-circle displacement between its winter position and its
summer position**:

```
D(i,y) = haversine( median position 15 Jan – 1 Mar ,  median position 15 Jul – 29 Aug )
```

and the trend in *D* across years.

**Displacement, not path length, and that is the whole design.** A displacement needs one fix near
each of two dates. It does not care whether the collar reported every fifteen minutes or every
thirteen hours, so the 52-fold sampling change cannot enter it. A path length would be a measurement
of the collar.

**A median position over a window, not a single fix**, so one wandering day near the boundary does
not become the animal's whole season.

**The windows are a definition and not the animals' own.** Mid-January to March and mid-July to
August are fixed calendar blocks chosen to sit inside the settled parts of each season. An animal
that shifted *when* it moved rather than *how far* is invisible here by construction — which is the
right trade, because when-it-moved is exactly what Phase 1d showed a collar record cannot measure.

## 3. Predictions, registered now

1. **The confound is real.** Per animal-year path length correlates with that year's median fix
   interval at |ρ| > 0.5. Registered because it must be demonstrated rather than asserted: this note
   discards a measure and has to show why.
2. **The escape works.** Displacement correlates with the year's median fix interval at |ρ| < 0.2.
   **This is the prediction the note lives or dies by.**
3. **The trend, two-sided.** No direction is registered. This herd is well studied and I do not have
   reliable enough recall of that literature to claim a prior without inventing one; a direction
   guessed now and confirmed later would be worth nothing. The test is two-sided and the result is a
   measurement, not a discovery.
4. **Svalbard reindeer replicate the method, not the number.** The same measure on a second
   population, a different species, a different continent. Prediction 2 must hold there too. Nothing
   is predicted about its trend, and a disagreement between the two herds is a result rather than a
   failure.

## 4. Stop conditions

- **Prediction 2 fails.** Displacement tracks the fix rate, so it is measuring the collar too and
  nothing is published but the fact that both measures are confounded. This would be the strongest
  version of Phase 1d's result and it would end track findings for good.
- **The trend aligns with a collar change.** If the year the trend turns is the year the hardware
  turned, it is Phase 1d again. Collar model is checked against the trend before any claim.
- **Fewer than ten animal-years in more than half the covered years.** A trend across years whose
  medians rest on three animals is a trend across three animals.
- **The trend is carried by animal turnover.** Fitted within animals as well as across them; if only
  the across-animal version shows it, the finding is about which elk were collared and it is
  reported that way or not at all.

## 5. What this cannot establish

- **One herd, one valley.** Ya Ha Tinda is a single population on the edge of Banff. This is not
  "elk" and it is certainly not "mammals".
- **Not a cause.** No covariate for forage, snow, wolves, hunting or road traffic enters this.
- **Not whether they migrate**, only how far the ones that were collared ended up from where they
  wintered. A herd shifting from migratory to resident would show as shrinking displacement, and so
  would a herd migrating a shorter way; this cannot separate those.
- **Collared animals are not a random sample** of the herd, and who gets a collar changes with the
  study's questions over 23 years.
- **Nothing about timing**, by construction. See §2.

## 6. Where the result goes

- A seventh `Finding` if it survives, realm `terrestrial`, taxon *Cervus elaphus* — which would also
  be the first non-bird, non-fish claim on the site and would unblock the multi-class ledger test.
- The confounded path-length measure published *beside* the robust one, as the exhibit. This project
  shows the wrong answer next to the right one when it has both, and here it will have both from the
  same animals in the same years.
- Results appended here with every prediction graded, whichever way it goes.

---

# Results — appended 2026-08-06

## The predictions, graded

| | registered | elk | Svalbard reindeer |
| --- | --- | --- | --- |
| 1 | path length tracks the fix interval, \|ρ\| > 0.5 | **−0.879** ✔ | −0.066 (see below) |
| 2 | displacement does not, \|ρ\| < 0.2 | **−0.047** ✔ | **+0.092** ✔ |
| 3 | trend, two-sided | −1.84 ± 3.89 km/decade | +1.16 ± 2.13 km/decade |
| 4 | reindeer replicate prediction 2 | — | ✔ |

341 elk animal-years over 130 animals and 17 years; 219 reindeer animal-years over 80 animals and
13 years. No stop condition fired: 6 of 17 elk years fall under ten animals, which is not the
"more than half" that would have ended it, and there is no trend for a collar change to align with.

## Prediction 1 is the result

**Path length correlates with the fix interval at ρ −0.879.** Not a caveat, not a suspicion — the
measure this project would have reached for first is, on this record, largely a measurement of the
collar. Across animal-years the elk fix interval runs 0.25 h to 26 h, a **104-fold** spread. (§1
quoted 52-fold; that was the spread of *per-year medians*, and the per-animal-year spread is twice
it. Both are true and the larger one is the relevant one.)

**Displacement correlates with it at −0.047**, on the same animals in the same years. The escape
works, and it works by construction rather than by luck.

That is Phase 1d's finding generalised: the collar does not merely move a measured *date* by 46.8
days, it dominates a measured *distance*. And it is the first result this project has that says what
to do about it rather than what to avoid.

**Prediction 1 not firing for the reindeer is not a failure.** §3 registered prediction 1 for the elk
record and required only prediction 2 of the reindeer. Their fix interval varies 8-fold against the
elk's 104-fold, so there is little sampling variation for a path length to track, and ρ −0.066 says
the Svalbard record is simply well behaved. A confound that is absent cannot be demonstrated.

## The trend is flat, and the null is weak enough that this must be said loudly

Neither herd's seasonal displacement clears its own interval, across animals or within them — elk
−1.84 ± 3.89, and −1.90 fitted inside animals; reindeer +1.16 ± 2.13, and +1.81 within.

**But the interval is as wide as the quantity.** The elk median displacement is 3.91 km and the
interval on its trend spans 199% of that per decade. **A change smaller than roughly a doubling or a
halving per decade could not have been distinguished from none.** For the reindeer the figure is 56%.

So "no change detected" here is a statement about this study's resolution at least as much as about
the animals, and it must not be read as "these herds are stable". It is not a bounded null of the
kind Phase 1b produced; it is a wide one.

## What the distribution shows, and the question this note did not ask

Elk displacement quartiles are 1.64 / 3.91 / 15.54 km. 46.3% of animal-years move more than 5 km,
37.2% more than 10, 18.2% more than 20. That is not a spread around a typical distance — it is a
mixture of animals that stayed and animals that left.

**A trend in the median of a bimodal mixture mostly tracks the mixing proportion**, and the mixing
proportion is the quantity a reader would actually want: what share of the herd migrates, and has it
changed. §2 registered a distance and not a share, so that question is **not answered here and is
not going to be answered here after the fact.** It is written down as the obvious next
pre-registration, with its own note, before any of it is computed.

## Where this goes

The methodological result is what gets published: a movement statistic that survives a collar record
whose sampling varied 104-fold, demonstrated against the statistic it replaces on the same animals.
The flat trend is reported inside it, with the power stated, and is not the headline — a null this
wide should not be a claim about elk.
