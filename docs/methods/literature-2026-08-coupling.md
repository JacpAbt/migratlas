# The coupling graph against the literature, checked 2026-08-18

Done before pre-registering #55, to answer three questions: has causal discovery been applied to
migration or phenology timing, does a cross-realm directed graph of such series exist anywhere,
and can series of 20–45 annual points support conditional-independence discovery at all. The
first two answers say the idea is unoccupied; the third changes its shape substantially.

What was **not** verified is stated at the end. Where a claim rests on a search rather than on
reading the paper, it says so.

## 1. PCMCI has reached ecology, but no animal's timing

The PCMCI family (Runge et al. 2019, *Science Advances* 5:eaau4996; Tigramite) has an
established ecology footprint that is almost entirely vegetation–climate: eddy-covariance and
greenness networks (Krich et al. 2020, *Biogeosciences* 17:1033; Krich et al. 2021, 18:2379),
dryland greening, flood drivers, one estuarine oxygen study. **No published application to
animal migration or animal phenology timing was found** — "phenology" co-occurs with PCMCI only
through land-surface greenness. The nearest animal-adjacent work uses other machinery:
transfer entropy on salmon dam counts (Goodwell & Campbell 2022, *PLoS ONE* 17:e0269193 — the
closest published thing to directed information flow on a migration series, framed as
predictive information, not a causal graph), and echo-state causal networks on lake plankton
and fish abundances (Suzuki et al. 2022, *PNAS* 119:e2204405119). A 2026 *Biological Reviews*
piece (Suzuki et al., doi 10.1002/brv.70180) surveys exactly this transfer of causal discovery
into ecological time series — its existence confirms the field considers the transfer current
and incomplete. It is paywalled and was assessed from the abstract only; **it must be read
before any public novelty sentence is committed**, the same condition #45 set for itself.

## 2. The mismatch canon compares trends; nobody has drawn the graph

The trophic-coupling classics are linear trends and pairwise regressions between series with a
known mechanism: tits and caterpillars (Visser 1998; Both et al. 2006, *Nature* 441:81),
plankton functional groups (Edwards & Richardson 2004, *Nature* 430:881, on the CPR),
oak–caterpillar–flycatcher chains (Burgess et al. 2018, *Nat Ecol Evol* 2:970). The cross-realm
syntheses — Thackeray et al. 2010 (*GCB* 16:3304) and 2016 (*Nature* 535:241), 10,003 UK series
across marine, freshwater and terrestrial — estimate **many independent climate→taxon
regressions and compare the coefficients**. Kharouba et al. 2018 (*PNAS* 115:5211) measures
synchrony as differences of trends between known interacting pairs. Continental green-up
versus bird arrival is still one series regressed on another (PNAS 121:e2308433121, 2024).
**A cross-realm directed lagged graph of timing series, estimated jointly, does not exist in
what this survey could find** — the nearest structural precedent, MAR(1) community models
(Ives et al. 2003, *Ecol Monogr* 73:301), is abundances within one community.

EDM/CCM (Sugihara et al. 2012, *Science* 338:496) is the established route to causal links
between ecological series, with a mature short-series toolkit — multispatial CCM needs as few
as 5–10 points per replicate given many replicates (Clark et al. 2015, *Ecology* 96:1174),
dewdrop regression pools short series (Hsieh et al. 2008, *Am Nat* 171:71) — but its footprint
is recruitment and abundance dynamics; **no application to migration timing was found**, and
the flagship network study (Ushio et al. 2018, *Nature* 554:360) had fortnightly data, ~285
points, exactly what annual series cannot give.

No public interactive product presents a causal or coupling network of migration or phenology:
BirdCast forecasts, Audubon's Migration Explorer maps connectivity, USA-NPN plots onsets — the
genre "interactive per-edge-tested coupling graph" has no ecological occupant.

## 3. The length problem is real and reshapes the idea

The bluntest findings, each from a stress test rather than an opinion:

- Miersch et al. 2025 (*AIES* 4(4)) ran PCMCI+ on ~70 years of observed hydrology — **longer
  than any series we hold** — and a significant share of inferred edges stayed unstable under
  resampling, with some true mechanisms missed even in 1000-year pseudo-observations.
- Yuan & Shou 2022 (*eLife* 11:e72518): permutation-surrogate significance tests on
  autocorrelated series produced 30–92% false positives; "model-free causality tests are not
  assumption-free."
- PCMCI assumes causal sufficiency, and shared climate modes driving every series is precisely
  the violation we would have. The latent-confounder variant (LPCMCI, Gerhardus & Runge 2020)
  costs recall it cannot afford at n≈30. The Earth-science recommendation (Runge et al. 2019,
  *Nat Comms* 10:2553) is to **condition on the known modes explicitly and detrend**, not hope
  the algorithm finds latents. Two series sharing a warming trend will fabricate an edge.

The verdict the pre-registration must inherit: **a full multivariate graph from single annual
series is not identifiable at our lengths.** What is defensible, with literature backing:
pre-registered *specific* edges with small conditioning sets; the project's replication pooled
(a hundred radar stations, seas as units, taxa within seas — the multispatial-CCM/
multiple-dataset mode); the sub-annual series (weekly radar, half-monthly NDVI, monthly ice and
plankton) carrying the real sample size; τ_max and variable count restricted; bootstrap
per-edge stability published; and nulls published beside hits — which is the findings ledger's
existing rule, not a new burden.

## 4. What this changes

The honest reframe, stated before anyone falls in love with the wrong sentence: most cross-realm
taxon↔taxon pairs have no direct mechanism — radar birds over Kansas and North Atlantic fish
interact only through shared climate — so under the null the "coupling graph" is a
climate-teleconnection graph re-estimated through noisy ecological proxies, and the edges that
would look most novel are the least identifiable. The product #55 pre-registers is therefore
**directed climate-mode and phenology drivers of each system, estimated jointly with explicit
conditioning on shared modes, published with per-edge stability and per-edge caveats** — the
coupling edges that survive that discipline are findings; the ones that do not are nulls worth
publishing. Not "we discovered animals coupling across oceans."

What remains genuinely unoccupied, on this survey's evidence: causal discovery applied to
animal migration/phenology timing at all; a cross-realm directed lagged graph of such series;
and a public interactive presentation of one with per-edge tests. Three empty spaces, each with
an honest reason it is empty, and a defensible way in through the sub-annual series and the
replication.

## Not verified

Suzuki et al. 2026 (*Biological Reviews*) — paywalled, abstract only; reading it is a stop
condition before any novelty claim. Visser 1998, Both & Visser 2001 and Youngflesh et al. 2021
are cited from background knowledge, not re-fetched this session. The Nowosad et al. 2024
author list was not verified. Absence-of-prior-art claims rest on searches, not on
exhaustiveness — they are "not found", never "does not exist".

---

**Status update, 2026-08-19.** The owner has no access to Suzuki et al. 2026. The stop condition
is resolved by removal rather than by waiting: `phase3c-coupling.md` claims no novelty anywhere,
so there is no novelty sentence for the unread review to falsify. The unoccupied-spaces
statements above remain scoped to what this survey's own search reached, which is all they ever
claimed.
