"""Phase 2a, the causal step: how much of the autumn advance is human?

Pre-registered in docs/methods/phase2a-attribution.md, including all four predictions and the
Pinatubo window test, before any model data was read.

The design is deliberately indirect. Models supply a *ratio* -- the human share of modelled
pre-season warming -- while observations supply its magnitude and the radar supplies the translation
into days. Multiplying a model's absolute warming by the fitted sensitivity would inherit that
model's bias in absolute trend; a ratio survives a model running warm or cold, and transfers across
the window mismatch that `historical` ending in 2014 forces on us.
"""

import logging
from typing import Final, NamedTuple

import numpy as np
import polars as pl

from migratlas.drivers import cmip6
from migratlas.drivers.schema import DRIVER_SAMPLES
from migratlas.lake.reader import scan_dataset
from migratlas.reports.phase2a_timing import CLAIM_BAND, sensitivities

log = logging.getLogger(__name__)

# 1995 matches the radar record's start; 1980 is the volcanic control. Both windows are computed
# because a hist-nat trend can be positive from volcanic recovery alone, with no human forcing in
# the run at all, and a fraction built on an inflated W_nat understates the human share. Which
# window carries more of that recovery is decided by the data rather than by argument -- see
# `_pinatubo_test`, where the method note's prediction turned out to be backwards.
WINDOWS: Final[tuple[tuple[int, int], ...]] = ((1995, cmip6.COMMON_END), (1980, cmip6.COMMON_END))

# A per-model ratio divides by that model's own warming, so a model that barely warms produces a
# ratio of arbitrary size and sign. Those are dropped from the per-model spread -- and counted, so
# the drop is visible -- while the headline ratio is taken on the ensemble means, where the
# denominator is the ensemble's warming and cannot vanish.
MIN_RATIO_WARMING: Final = 0.05

MIN_YEARS: Final = 15

# Prediction 3: human dominance of recent warming is among the best-established results in the
# field, so a small fraction here is evidence of a bug in this extraction rather than a discovery.
EXPECTED_FRACTION: Final = 0.8

# Prediction 1: the ensemble should broadly reproduce the observed pre-season warming, or the
# counterfactual built on it is not trustworthy. Half to double, as an order-of-magnitude check.
VALIDATION_BAND: Final[tuple[float, float]] = (0.5, 2.0)

# Windows whose fractions differ by more than this are treated as disagreeing.
MATERIAL_DISAGREEMENT: Final = 0.1

# How large the synthetic null's warming *difference* may be, as a share of the real forced
# difference, before the machinery is suspect.
#
# The first version of this control compared the null's *fraction* against zero, which was wrong and
# came out at +8.67. Under the null the denominator is a near-zero warming by construction, so the
# ratio is meaningless there however sound the method is -- the same pathology `MIN_RATIO_WARMING`
# exists to keep out of the per-model spread. The numerator carries the information: two halves of
# one experiment should differ by nothing, and how close to nothing is what bounds the noise floor.
PLACEBO_CEILING: Final = 0.2


class Trend(NamedTuple):
    """One simulation's June-July warming at the radar stations, over one window."""

    experiment: str
    model: str
    member: str
    per_decade: float
    stations: int


class Fraction(NamedTuple):
    """The human share of modelled pre-season warming over one window."""

    window: tuple[int, int]
    models: int
    historical: float
    historical_ci: float
    natural: float
    natural_ci: float
    ensemble: float
    """(W_hist - W_nat) / W_hist on the ensemble means. The headline: no vanishing denominator."""
    per_model: list[float]
    dropped: int
    """Models excluded from ``per_model`` because their own historical warming was too small."""

    @property
    def spread(self) -> tuple[float, float]:
        """Min and max of the per-model ratios, or NaN if none survived."""
        if not self.per_model:
            return (float("nan"), float("nan"))
        return (min(self.per_model), max(self.per_model))

    @property
    def difference(self) -> float:
        """W_hist - W_nat: the modelled human contribution in degC per decade.

        The fraction's numerator, and the only part of it that stays meaningful when the denominator
        is near zero -- which is the case under the synthetic null and nowhere else.
        """
        return self.historical - self.natural

    @property
    def above_one(self) -> int:
        """Models whose fraction exceeds 1, meaning their counterfactual *cooled*.

        Not an error. Volcanic and aerosol forcing without greenhouse gases can give a negative
        trend, and then human forcing accounts for more than all of the modelled warming.
        """
        return sum(1 for value in self.per_model if value > 1.0)


def shortfall(landed: pl.DataFrame) -> list[str]:
    """Models the catalogue offers that are not in the lake.

    The ingest logs a store it could not read and carries on, which is right -- one unreadable
    member must not cost the other eighty-seven. But the same tolerance means a third of the
    ensemble can go missing and still produce a plausible answer, which is what happened on the
    first run of this: nine of fifteen models were dropped on a calendar `xarray` could not decode
    without `cftime`, and the only visible symptom was a six-model ensemble that looked fine.

    So the shortfall is checked where the claim is made rather than where the data is fetched. The
    catalogue is already cached, so this costs a local CSV read.
    """
    offered = {store.model for store in cmip6.stores(cmip6.catalogue())}
    present = set(landed["model"].unique().to_list())
    return sorted(offered - present)


def simulated() -> pl.DataFrame:
    """Simulated pre-season temperature per station-year, tagged with which simulation."""
    prefix = f"{cmip6.CANONICAL}_junjul_"
    return (
        scan_dataset(DRIVER_SAMPLES.name, source_id=cmip6.SOURCE_ID)
        .filter(pl.col("variable").str.starts_with(prefix))
        .select(
            station_id=pl.col("site_id"),
            latitude=pl.col("latitude"),
            year=pl.col("period_start").dt.year(),
            experiment=pl.col("variable").str.strip_prefix(prefix),
            # "cmip6:{experiment}:{model}:{member}" -- see drivers/cmip6.to_samples.
            model=pl.col("derived_from").str.split(":").list.get(2),
            member=pl.col("derived_from").str.split(":").list.get(3),
            value=pl.col("value"),
        )
        .collect()
    )


def trends(frame: pl.DataFrame, window: tuple[int, int]) -> list[Trend]:
    """Warming per decade per simulation: fitted per station, then averaged across stations.

    Per station first, matching how the observed warming and the sensitivity were both computed in
    `phase2a_timing`. Averaging the temperatures across stations before fitting would give a
    different weighting and make the model number not comparable with the observed one.
    """
    start, end = window
    band = frame.filter(
        pl.col("latitude").is_between(*CLAIM_BAND, closed="left"),
        pl.col("year").is_between(start, end),
    )
    if band.is_empty():
        return []

    # Slope by the covariance identity rather than a per-group least squares loop: there are
    # thousands of (simulation, station) groups and the answer is identical.
    per_station = (
        band.group_by("experiment", "model", "member", "station_id")
        .agg(
            per_decade=(pl.cov("year", "value") / pl.col("year").var()) * 10.0,
            years=pl.len(),
        )
        .filter(pl.col("years") >= MIN_YEARS, pl.col("per_decade").is_not_null())
    )
    per_member = per_station.group_by("experiment", "model", "member").agg(
        pl.col("per_decade").mean(), stations=pl.len()
    )
    return [
        Trend(
            experiment=row["experiment"],
            model=row["model"],
            member=row["member"],
            per_decade=float(row["per_decade"]),
            stations=int(row["stations"]),
        )
        for row in per_member.sort("experiment", "model", "member").iter_rows(named=True)
    ]


def _mean_ci(values: np.ndarray) -> tuple[float, float]:
    if values.size == 0:
        return (float("nan"), float("nan"))
    ci = 1.96 * float(values.std(ddof=1)) / np.sqrt(values.size) if values.size > 1 else 0.0
    return (float(values.mean()), ci)


def by_model(fitted: list[Trend]) -> pl.DataFrame:
    """Members averaged within each model, then the two experiments put side by side.

    Members first because MIROC6 and CanESM5 publish fifty hist-nat runs each while nine models
    publish three or fewer. Pooling members would make the ensemble a statement about two models.
    """
    if not fitted:
        return pl.DataFrame()
    frame = pl.DataFrame([item._asdict() for item in fitted])
    return (
        frame.group_by("experiment", "model")
        .agg(pl.col("per_decade").mean(), members=pl.len())
        .pivot(on="experiment", index="model", values=("per_decade", "members"))
        .rename(
            {
                "per_decade_historical": "historical",
                "per_decade_hist-nat": "natural",
                "members_historical": "members_hist",
                "members_hist-nat": "members_nat",
            }
        )
        .drop_nulls(["historical", "natural"])
        .sort("model")
    )


def fraction(frame: pl.DataFrame, window: tuple[int, int]) -> Fraction | None:
    """The human share of modelled June-July warming, on the ensemble and per model."""
    models = by_model(trends(frame, window))
    if models.is_empty():
        return None

    historical = models["historical"].to_numpy().astype(float)
    natural = models["natural"].to_numpy().astype(float)
    hist_mean, hist_ci = _mean_ci(historical)
    nat_mean, nat_ci = _mean_ci(natural)

    usable = historical > MIN_RATIO_WARMING
    per_model = ((historical[usable] - natural[usable]) / historical[usable]).tolist()
    return Fraction(
        window=window,
        models=models.height,
        historical=hist_mean,
        historical_ci=hist_ci,
        natural=nat_mean,
        natural_ci=nat_ci,
        ensemble=(hist_mean - nat_mean) / hist_mean if hist_mean != 0 else float("nan"),
        per_model=[float(value) for value in per_model],
        dropped=int((~usable).sum()),
    )


def placebo(frame: pl.DataFrame, window: tuple[int, int]) -> Fraction | None:
    """The same fraction computed between two halves of the *same* experiment.

    A synthetic null on the machinery rather than on the science. One `hist-nat` member is
    relabelled `historical` and the rest keep their label, so there is no forced difference between
    the two sides and `f` must come out near zero. If it does not, the ratio, the averaging or the
    trend fitting is manufacturing a fraction out of internal variability, and the real number is
    worth nothing.

    Written after the main result rather than pre-registered, and it is only honest to say so. It
    can fail in one direction: a large null means the method is broken, a small one bounds the noise
    floor. It cannot make a real fraction larger.
    """
    natural = frame.filter(pl.col("experiment") == "hist-nat")
    if natural.is_empty():
        return None
    first = natural.group_by("model").agg(pl.col("member").min().alias("first"))
    relabelled = (
        natural.join(first, on="model", how="inner")
        .with_columns(
            experiment=pl.when(pl.col("member") == pl.col("first"))
            .then(pl.lit("historical"))
            .otherwise(pl.lit("hist-nat"))
        )
        .drop("first")
    )
    return fraction(relabelled, window)


class Observed(NamedTuple):
    """What the radar and the reanalysis contribute: the translation and the magnitude."""

    sensitivity: float
    """S, days of passage-date shift per degC. Negative is earlier."""
    warming: float
    """W_obs, observed degC per decade."""
    explained: float
    """S x W, each station's own sensitivity times its own warming, then averaged.

    Not the product of the two band means. Those differ -- the product gives -0.341 where the
    per-station average gives -0.301 -- and the second is what `phase2a-timing.md` pre-registered
    and published. Multiplying the human fraction into the other one would quietly compare the
    attribution against a number the timing note never reported.
    """
    advance: float
    """A, observed days per decade. Negative is earlier."""
    stations: int


def observed() -> Observed | None:
    """S, W_obs, S x W and A from the claim band, recomputed rather than copied from the note."""
    fitted = [item for item in sensitivities() if CLAIM_BAND[0] <= item.latitude < CLAIM_BAND[1]]
    if not fitted:
        return None
    return Observed(
        sensitivity=float(np.mean([item.per_degree for item in fitted])),
        warming=float(np.mean([item.warming_per_decade for item in fitted])),
        explained=float(np.mean([item.explained_per_decade for item in fitted])),
        advance=float(np.mean([item.observed_per_decade for item in fitted])),
        stations=len(fitted),
    )


def chosen(fractions: list[Fraction]) -> Fraction:
    """The window the pre-registration says to use: the longer one when they disagree.

    Separate from the narration so the findings document and the report cannot pick differently.
    """
    if len(fractions) == 1:
        return fractions[0]
    gap = abs(fractions[0].ensemble - fractions[1].ensemble)
    if gap <= MATERIAL_DISAGREEMENT:
        return fractions[0]
    return max(fractions, key=lambda found: found.window[1] - found.window[0])


def _pinatubo_test(fractions: list[Fraction], out: list[str]) -> Fraction:
    """Apply the pre-registered window rule, and say where its reasoning went wrong.

    The method note predicted that a window starting in 1995 would be the contaminated one, because
    a hist-nat run beginning four years after Pinatubo is still recovering from volcanic cooling.
    That reasoning was backwards. A window starting in 1980 sits *before* both El Chichon (1982) and
    Pinatubo (1991), so both depressions fall in its first half and tilt a fitted line upwards,
    while by 1995 most of Pinatubo's cooling had already decayed. Whether the data agree is
    checkable rather than arguable -- it is whichever window carries the larger W_nat -- so the
    report states which it was instead of repeating the prediction.

    The rule itself is applied as written: on material disagreement, the longer window is used. It
    happens to be the conservative end of the bracket, which is worth knowing but is not why.
    """
    primary = chosen(fractions)
    if len(fractions) == 1:
        return primary

    gap = abs(fractions[0].ensemble - fractions[1].ensemble)
    agree = gap <= MATERIAL_DISAGREEMENT
    volcanic = max(fractions, key=lambda found: found.natural)
    verdict = (
        "the windows agree, so volcanic recovery is not driving the answer"
        if agree
        else "the windows DISAGREE, so the pre-registered rule takes the longer one, "
        f"{primary.window[0]}-{primary.window[1]}"
    )
    out += [
        f"\n  Pinatubo window test: f differs by {gap:.2f} -- {verdict}.",
        f"  The recovery is measurable either way, and it sits in "
        f"{volcanic.window[0]}-{volcanic.window[1]}, whose W_nat is the",
        f"  larger at {volcanic.natural:+.3f} degC/decade. The method note predicted the opposite "
        "and had the mechanism",
        "  backwards: a window starting in 1980 sits before both El Chichon and Pinatubo, so both",
        "  cooling episodes fall in its first half and tilt the fitted line up, whereas by 1995",
        "  most of Pinatubo's cooling had already decayed.",
    ]
    if not agree:
        out.append(
            "  The two f values therefore bracket the answer rather than one of them being right."
        )
    return primary


def _null_section(frame: pl.DataFrame, primary: Fraction) -> list[str]:
    """The synthetic null, read as a difference rather than as a fraction."""
    null = placebo(frame, primary.window)
    if null is None or not primary.difference:
        return []
    leakage = abs(null.difference / primary.difference)
    return [
        "",
        "=" * 78,
        "synthetic null -- the same machinery on two halves of one experiment",
        "=" * 78,
        f"\n  W_hist - W_nat, forced:  {primary.difference:+.3f} degC per decade",
        f"  W_hist - W_nat, null:    {null.difference:+.3f} degC per decade across "
        f"{null.models} models",
        f"  the null is {leakage:.0%} of the forced difference "
        f"({'PASS' if leakage <= PLACEBO_CEILING else 'FAIL'}, ceiling {PLACEBO_CEILING:.0%})",
        "\n  Two halves of one experiment differ only by initial condition, so the difference",
        "  between them bounds how much of the real one could be internal variability rather than",
        "  forcing. Read as a difference, not a fraction: under the null the denominator is a",
        "  near-zero warming, so the ratio is meaningless there whatever the method does -- it",
        f"  comes out at {null.ensemble:+.1f} and means nothing.",
        "  Written after the main result and not pre-registered. It can show the method broken; it",
        "  cannot make the real fraction larger.",
    ]


def _predictions(primary: Fraction, seen: Observed, anthropogenic: float) -> list[str]:
    """The four pre-registered predictions, each judged against what came out."""
    ratio = primary.historical / seen.warming if seen.warming else float("nan")
    reproduces = VALIDATION_BAND[0] <= ratio <= VALIDATION_BAND[1]
    zero = "in" if abs(primary.natural) <= primary.natural_ci else ""
    residual = (
        " Small but not nothing, and the window test says what it\n     is: volcanic recovery, not "
        "human forcing leaking into a run that has none."
        if not zero and primary.natural > 0
        else ""
    )
    return [
        "",
        "=" * 78,
        "the four predictions",
        "=" * 78,
        f"  1. W_hist resembles the observed warming: {'HELD' if reproduces else 'FAILED'} -- "
        f"modelled {primary.historical:+.3f} against\n     observed {seen.warming:+.3f}, a "
        f"ratio of {ratio:.2f}.",
        f"  2. W_nat near zero: {primary.natural:+.3f} +/- {primary.natural_ci:.3f} degC/decade, "
        f"{zero}distinguishable from zero.{residual}",
        f"  3. f above {EXPECTED_FRACTION}: "
        f"{'HELD' if primary.ensemble > EXPECTED_FRACTION else 'FAILED'} -- f = "
        f"{primary.ensemble:.2f}. This is a check on the\n     extraction, not a discovery: human "
        "dominance of recent warming is established, so a small f\n     would mean a bug here.",
        f"  4. f x S x W smaller in magnitude than A: "
        f"{'HELD' if abs(anthropogenic) < abs(seen.advance) else 'FAILED'} -- "
        f"{abs(anthropogenic):.3f} against {abs(seen.advance):.3f}\n     days per decade.",
    ]


def render() -> str:
    out = [
        "Phase 2a, the causal step -- how much of the autumn advance is human?",
        "=" * 78,
        "Pre-registered in docs/methods/phase2a-attribution.md: the ratio design, both windows,",
        "the member-then-model averaging and all four predictions were fixed before any model",
        "data was read. hist-nat is a counterfactual -- a climate that did not happen -- and is",
        "never shown as an observation.",
    ]

    frame = simulated()
    if frame.is_empty():
        out.append("\nNo CMIP6 samples in the lake. Run `make ingest-cmip6` first.")
        return "\n".join(out)

    missing = shortfall(frame)
    if missing:
        out += [
            "",
            "!" * 78,
            f"INCOMPLETE ENSEMBLE: {len(missing)} model(s) the catalogue offers are missing here:",
            "  " + ", ".join(missing),
            "A model missing is a model that failed to read, and the failures are not random: they",
            "follow whichever calendar or encoding the modelling centre chose. Re-run",
            "`make ingest-cmip6` and read its warnings before quoting anything below.",
            "!" * 78,
        ]

    fractions = [found for window in WINDOWS if (found := fraction(frame, window)) is not None]
    if not fractions:
        out.append(
            f"\nNo model had {MIN_YEARS}+ years in both experiments inside "
            f"{CLAIM_BAND[0]}-{CLAIM_BAND[1]}N."
        )
        return "\n".join(out)

    out += [
        "",
        "=" * 78,
        "modelled warming and the human share",
        "=" * 78,
        "The +- is the spread across models, not the uncertainty of one trend: it says how much",
        "the modelling centres disagree, which a single-model answer would hide.",
        "",
    ]
    out.append(
        f"  {'window':<12} {'models':>6}  {'W_hist degC/dec':>17}  {'W_nat degC/dec':>17}  {'f':>6}"
    )
    for found in fractions:
        out.append(
            f"  {found.window[0]}-{found.window[1]}    {found.models:>6}  "
            f"{found.historical:+8.3f}+-{found.historical_ci:.3f}  "
            f"{found.natural:+8.3f}+-{found.natural_ci:.3f}  {found.ensemble:>6.2f}"
        )
    for found in fractions:
        low, high = found.spread
        dropped = (
            f", {found.dropped} dropped for W_hist <= {MIN_RATIO_WARMING}" if found.dropped else ""
        )
        above = (
            f", {found.above_one} of them above 1 -- a counterfactual that cools"
            if found.above_one
            else ""
        )
        out.append(
            f"  {found.window[0]}-{found.window[1]}: per-model f spans {low:.2f} to {high:.2f} "
            f"across {len(found.per_model)} models{dropped}{above}"
        )

    primary = _pinatubo_test(fractions, out)

    seen = observed()
    if seen is None:
        out.append("\nNo station carried a sensitivity. Run the timing report's ingests first.")
        return "\n".join(out)

    anthropogenic = primary.ensemble * seen.explained
    out += [
        "",
        "=" * 78,
        f"the attribution, {CLAIM_BAND[0]}-{CLAIM_BAND[1]}N, f from {primary.window[0]}-"
        f"{primary.window[1]}",
        "=" * 78,
        f"\n  S      {seen.sensitivity:+.3f} days per degC     "
        f"({seen.stations} stations, from the radar)",
        f"  W_obs  {seen.warming:+.3f} degC per decade   (ERA5 at those stations)",
        f"  S x W  {seen.explained:+.3f} days per decade   "
        "(per station, then averaged, as phase2a-timing published it)",
        f"  f      {primary.ensemble:>6.2f}                     "
        f"({primary.models} models, CMIP6 historical against hist-nat)",
        f"\n  f x S x W  {anthropogenic:+.3f} days per decade  <- the human share, in days",
        f"  observed A {seen.advance:+.3f} days per decade",
    ]
    if seen.advance != 0:
        out.append(f"\n  That is {anthropogenic / seen.advance:.0%} of the observed advance.")
    if len(fractions) > 1:
        out.append("\n  The same arithmetic under every window, so the choice is visible:")
        for found in fractions:
            days = found.ensemble * seen.explained
            share = f"{days / seen.advance:.0%}" if seen.advance else "n/a"
            chosen = "  <- pre-registered" if found is primary else ""
            out.append(
                f"    f from {found.window[0]}-{found.window[1]}, f = {found.ensemble:.2f}: "
                f"{days:+.3f} days per decade, {share} of observed{chosen}"
            )

    out += _null_section(frame, primary)
    out += _predictions(primary, seen, anthropogenic)

    models = by_model(trends(frame, primary.window))
    out += ["", "=" * 78, "per model", "=" * 78]
    out.append(f"  {'model':<18} {'W_hist':>8} {'W_nat':>8} {'f':>6}  members hist/nat")
    for row in models.iter_rows(named=True):
        per_model = (
            (row["historical"] - row["natural"]) / row["historical"]
            if row["historical"] > MIN_RATIO_WARMING
            else float("nan")
        )
        out.append(
            f"  {row['model']:<18} {row['historical']:+8.3f} {row['natural']:+8.3f} "
            f"{per_model:>6.2f}  {row['members_hist']:>7}/{row['members_nat']}"
        )

    out += [
        "",
        "=" * 78,
        "What this concludes, and what it does not. The claim is narrow: of the portion of the",
        "autumn advance that tracks pre-season temperature, this share is attributable to human",
        "forcing. Not that the whole advance is: only about half of it tracks temperature at all.",
        "Not that temperature is the mechanism rather than a correlate of one, since the response",
        "function is observational. And nothing about the southern bands, whose 2012 step is still",
        f"unexplained and which are excluded here as everywhere else. `historical` also ends in "
        f"{cmip6.COMMON_END},",
        "so f is measured over an earlier window than W_obs -- stated in the method note, and the",
        "reason f is a ratio rather than a difference.",
    ]
    return "\n".join(out)
