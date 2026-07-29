# 0006 — Sample point drivers over OPeNDAP, not from cloud-optimised Zarr

**Status:** accepted, 2026-07-29. Supersedes the plan's "ARCO-ERA5 Zarr on GCS — never download
GRIB" for *point* extraction. That instruction stays correct for anything map-shaped.

## Context

The driver panel's first job is a wind vector at 143 radar stations for every night of
1995–2025, so radar ground speed can be turned into airspeed (`phase1c-homogeneity.md`, Test C).
That is a point time series: ~11,000 dates × 143 fixed locations × 2 components.

The plan named ARCO-ERA5 on Google Cloud Storage, which is public and needs no credentials. It is
the right recommendation for the access pattern it was chosen for and the wrong one for this.

## What the measurement showed

Chunk shapes read from the store's own consolidated metadata:

| Store | Array shape | Chunk shape | Bytes per chunk |
| --- | --- | --- | --- |
| `ar/full_37-1h-0p25deg` `u_component_of_wind` | 1323648 × 37 × 721 × 1440 | **1 × 37 × 721 × 1440** | ~154 MB |
| `ar/full_37-1h-0p25deg` `2m_temperature` | 1323648 × 721 × 1440 | 1 × 721 × 1440 | ~4 MB |
| `co/model-level-wind` `t`, `w`, `vo`, `d` | 374016 × 137 × 410240 | 1 × 137 × 410240 | ~225 MB |

Every array in the bucket is chunked as **one timestep, all levels, the whole globe**. A chunk is
the smallest unit that can be fetched, so a single station-hour of 850 hPa wind costs a 154 MB
read. Scaled to what Test C needs, that is petabytes to extract a few hundred thousand numbers.
`co/` is worse and does not even carry `u`/`v` — it holds vorticity and divergence on a reduced
Gaussian grid, so using it would mean a spectral transform first. The `raw/` prefix is one 50 MB
NetCDF per date × variable × level, which is 756 GB for the migration windows alone.

Three other routes were checked and rejected:

- **Open-Meteo's ERA5 archive** serves point time series, needs no key, and covers 1940–present —
  but returns `"undefined"` units for `wind_speed_850hPa` while returning `km/h` for
  `wind_speed_100m`. Surface and 10/100 m only, no pressure levels. 100 m sits below the
  nocturnal low-level jet and is not the layer the migrants are in.
- **The Copernicus CDS API** does exactly the right server-side area subsetting, and is the
  standard answer. It needs an account and an API key, so it is a dependency on someone
  registering rather than on code.
- **Picking 850 hPa at all** was itself wrong. The Dark Ecology profiles integrate 0–3000 m above
  the radar with most mass low, so the reflectivity-weighted velocity sits nearer 750 m — about
  925 hPa, not 1500 m.

## Decision

Sample point drivers over **OPeNDAP with server-side hyperslab constraints**, and take the wind
from **NCEP NARR** via NOAA PSL's THREDDS server.

Measured, not assumed: one grid point for a whole month at one level is a **3.2 kB** response,
and the full 277 × 349 latitude grid is 389 kB in 1.3 s. No key, no account, no bulk download.

NARR earns it on the merits rather than only on access:

- **1979–present, 3-hourly, 32 km, 29 pressure levels** — spacing is 25 hPa through the lower
  troposphere, so 1000/975/950/925/900/875/850 are all available and the vertical weighting can be
  made to match the radar profile instead of collapsing to one arbitrary level.
- Its domain **is** the radar domain. The Dark Ecology network is CONUS; a North American regional
  reanalysis at 32 km assimilating US observations is a better wind field here than a global
  product at 0.25°, not a compromise.
- 3-hourly is ample: the target is a nightly mean, not an instantaneous wind.

## Verification

One month, one station, real numbers rather than a smoke test. KBGM, September 2015, wind averaged
over 1000–850 hPa and over the four night timesteps, differenced against the lake's
reflectivity-weighted ground velocity:

- Ten busiest nights: median airspeed **11.5 m/s**, inside the 8–15 m/s band for nocturnal migrant
  songbirds and well clear of the 0–5 m/s insect band.
- Every one of those ten nights has a heading between **181° and 233°** — uniformly
  south-westward, which is the autumn heading for the north-eastern US.

The direction agreement is the part worth trusting, because it is independent of the airspeed
arithmetic: it says the scatterers are migrating birds regardless of whether the level weighting is
exactly right.

Per-night noise is real and visible — 19.9 m/s on 2015-09-20, 6.7 m/s on 2015-09-11 — as expected
from differencing two vectors whose levels and time windows only approximately coincide. Test C
asks for a trend in a mean over thousands of nights, which tolerates that; any per-night claim
would not, and none will be made.

## Consequences

- New dependency: **`pydap`**, pure Python and wheel-only, so the no-`sudo` constraint holds. No
  system HDF5 or netCDF library is needed.
- `features/annotate.py` takes an OPeNDAP backend, keyed by driver and realm as planned. The
  interface stays "sample a gridded field onto a point set" so CMEMS and CMIP6 DAMIP can arrive
  behind it later.
- Driver rows land in `DRIVER_SAMPLES` with `kind=GRIDDED`, which is what keeps them
  distinguishable from FISHGLOB's per-haul measured temperatures.
- **NARR is North America only.** When ENRAM adds European radar the wind field has to come from
  somewhere else, and that is the point at which the CDS key becomes worth asking for. Recording
  it here so the second network does not silently inherit a North American reanalysis.
- The station-to-grid match is nearest-cell on a Lambert Conformal grid. KBGM's centre lands 25 km
  away on a 32 km grid, which is inherent to the resolution rather than an error, but it means a
  station near a sharp gradient — a coast, a mountain front — carries more error than one inland.
