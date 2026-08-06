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
