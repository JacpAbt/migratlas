# Idea — a response model fed by other people's forecasts

**Status:** idea, not a commitment. Raised by the owner on 2026-08-07; recorded so it is not
re-invented from scratch later. Nothing here is scheduled.

## The idea as raised

Train a model of migration against environmental drivers on the data already in the lake, then
chain it with *someone else's* forecast of those drivers — the owner named NVIDIA's Earth-2 class
of models — so no single model is asked to do too much: a grounded response model on our side, a
specialist forecast model on theirs.

## What is already true

**This is the architecture the project committed to before the idea had this name.** Forecast A
(`TASKS.md` #13, `DATASETS.md`) is exactly this shape: the fitted response function
`S = −0.659 ± 0.165` days per °C, chained with CMIP6 ScenarioMIP temperature — a response model of
ours fed by forecasts of theirs. The attribution used the same trick in the other direction
(`S × W` with `W` from DAMIP). So the instinct is sound, and it is not new work so much as a new
*horizon* for existing work. The question is only which horizon.

## The horizons, and who occupies them

| Horizon | Forecast source | Verdict |
| --- | --- | --- |
| Days (nowcast) | Earth-2 / GraphCast-class weather models | **Still refused.** This is BirdCast's territory — operational, free, better resourced, on the same radar network — and FluxRGNN is the research frontier. A better weather feed does not change why we would be third; the refusal in `literature-2026-07.md` §2 stands regardless of whose weather model is upstream. |
| Weeks to a season | Seasonal forecast systems (ECMWF SEAS5 hindcasts via C3S; AI S2S models as they mature) | **The open middle, and the interesting one.** "Will this autumn's passage be early?" is neither BirdCast's three days nor ScenarioMIP's 2100. `S` is precisely the transfer function it needs: pre-season temperature anomaly in, passage-date anomaly out. A hindcast skill test is cheap, honest and pre-registerable: apply `S` to seasonal hindcasts over held-out years, and either beat climatology or publish the null. Lights-out campaigns are planned weeks ahead, which is exactly the window nothing currently serves. |
| Decades (scenario) | CMIP6 ScenarioMIP | **Already planned as Forecast A**, unchanged. Earth-2-class models are weather models and do not reach this horizon. |

## The ceilings, stated before anyone is excited

- **The weak link is the response model, not the forecast.** `S` carries the *thermal* half of the
  advance; the other half of −0.56 does not track temperature at all (`anthropogenic-share`'s own
  caveat). A pipeline inherits its weakest stage — though this is also the argument *for* the
  pipeline: its uncertainty decomposes into forecast skill and response fit, which one end-to-end
  model cannot offer.
- **`transfer-fails` scopes it.** A response fitted at 37–50°N aerial holds nowhere else until
  tested there; hold-one-out error was 0.68 across realms. Any outlook is a regional product and
  says so.
- **The skill bar must be able to fail.** Seasonal temperature skill over the CONUS autumn is
  modest; `S` times a low-skill forecast is a low-skill outlook, and the pre-registration must
  name climatology as the bar and publish either side of it.

## What must be true first

- A scoop check: nobody found "seasonal migration timing outlook" occupied during the July
  literature pass, but nobody looked for it either. Look before claiming the gap.
- A verified data route for seasonal hindcasts at the radar stations (C3S serves SEAS5; terms and
  volume unmeasured as of this note).
- Forecast A's own skill test (`DATASETS.md` step 1) — if `S` cannot beat climatology on held-out
  *observed* years, feeding it a forecast is decoration, and the answer is a recorded null.
