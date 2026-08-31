# ADR 0016 — A cross-unit slope must survive losing any one unit

**Status:** accepted · 2026-08-31

## Context

Phase 3g graded every registered prediction true and then published nothing, because of a check
nobody had registered.

Its fit was `latitude_trend ~ 1 + oxygen_trend + warming_trend` over sixteen shelf surveys, and the
oxygen coefficient came out `−0.054 ± 0.041` — clear of zero, where warming's was not. Then one unit
of the sixteen turned out to carry it: dropping the Gulf of St Lawrence takes the slope to
`−0.021 ± 0.030`, which no longer clears zero. The note's own words: *"one of sixteen units carries
the association … the conclusion is narrower than the grades."*

The call was right and the way it was reached was not repeatable. §3 of that registration *"asked
for no leverage check, so what follows is a diagnostic and can never be a graded prediction — run
after the result was seen, it could only ever confirm a hope."* It happened because one driver value
was fourteen times the median and somebody looked. Nothing in this project makes it happen again.

**Three live estimates carry the same exposure and none has been asked:**

| where | units | what rests on it |
| --- | --- | --- |
| Phase 3e | 18 | Cochran's Q of 235.7, and the warming null `+0.039 ± 0.179`. Owed to the ledger. |
| Phase 3g | 16 | asked by hand, and the reason nothing was published |
| Phase 1m | 10 | group means and their intraclass correlations |

Phase 3e is the pressing one, because its heterogeneity result is established, unpublished and owed
— and Q is a sum over units, so one extreme unit can inflate it exactly the way one extreme unit
inflated Phase 3g's slope.

A related point, learnt the same way: Phase 3g's extreme was **real**. The Gulf of St Lawrence deep
channel is among the best-documented cases of shelf deoxygenation anywhere and the ingested values
agreed with that literature unprompted. A true extreme with high leverage is *worse* than a bad
point, not better, because there is nothing to clean and the fit still rests on it. So this is not
an outlier rule and must not be written as one.

## Decision

**On a panel of fewer than 30 units, a cross-unit coefficient may be published as clearing zero only
if it still clears zero, in the same direction, with any single unit removed.**

- The bound is a **verdict** bound, not a magnitude bound. It asks whether the conclusion survives,
  not whether the number moves — a coefficient that halves and still clears zero is a coefficient
  whose verdict holds, and saying so is more honest than a threshold on drift that nobody can
  justify.
- **A null is unaffected.** An estimate that does not clear zero has no verdict to overturn, so the
  rule is silent on it. `marine-null` and Phase 3e's warming slope are not made more or less
  publishable by anything here.
- **Above 30 units the rule does not apply.** One row cannot plausibly carry a slope over thirty,
  and the refits become noise. Thirty is the order of magnitude the three exposed panels sit below
  (16, 18, 10) rather than a figure tuned against any of them, and it is stated here so it cannot be
  chosen later against a result.
- **It is computed by refitting, not by a hat matrix.** Weights, standardisation and the
  pseudoinverse all change when a row leaves, and an analytic influence measure would assume they do
  not.
- **It is a diagnostic, never a graded prediction.** A registration may of course predict that its
  estimate survives; what this ADR fixes is that the check runs whether or not anybody thought to
  predict it.

`models/influence.py` implements it, and `phase3b.regression` — the fit Phase 3b and Phase 3e both
call — now returns it on every fit, so the two marine phases inherit the check rather than
remembering to run it. `tests/test_influence.py` builds a panel whose slope one unit manufactures
and requires the rule to refuse it, one where every unit agrees and requires it to pass, a null it
must stay silent about, and a large panel it must not fire on.

## Consequences

**Phase 3e's publication is gated on this rather than on a decision.** Its entry in the ledger is
owed and it now has a condition to meet first. If Q or the slope turns out to rest on one sea, the
finding says so or is not published — and either way the check is in the run rather than in
somebody's memory.

**Phase 3g is deliberately not retrofitted.** Its own `leverage()` is the record of the unregistered
check that actually produced its published grading, and swapping it for the shared helper would
change the provenance of that record without re-running the phase against a lake this ADR is not
touching. A successor that re-runs Phase 3g should switch it over; until then two implementations
exist and this paragraph is why.

**Phase 1m is not retrofitted either**, for a different reason: its units are group means, its
estimand is an intraclass correlation rather than a slope, and what "dropping a unit" means there
needs its own thought. Recorded as exposed rather than as handled.

**The cost is n refits per fit.** On sixteen to eighteen units that is nothing. If a phase ever
brings a panel of hundreds under the floor by some other route, the floor is the thing to read
first.

## What this does not do

- It does not make a small-panel result *right*. Surviving the loss of any one unit is a much
  weaker property than being well estimated, and a panel of sixteen is a panel of sixteen.
- It does not address leverage in the *response* — a unit whose own trend is poorly determined gets
  a small weight and that is the only protection here.
- It says nothing about influence on a **heterogeneity** statistic. Q is a sum over units and the
  same exposure exists, but the rule as written is about a coefficient's verdict, and extending it
  to Q is a separate decision that Phase 3e's publication will have to make explicitly.
