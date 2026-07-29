import time

import polars as pl

from migratlas.ingest import fishglob

for survey in ("EBS", "AI", "GOA"):
    pandas = fishglob.read_survey(survey)
    frame = pl.from_pandas(pandas[["num", "wgt", "num_cpue", "wgt_cpue", "num_cpua", "wgt_cpua"]])  # type: ignore[index]
    filled = {c: f"{1 - frame[c].is_null().mean():.0%}" for c in frame.columns}
    print(f"{survey:<5} populated: {filled}")
    for c in ("num_cpue", "num_cpua", "wgt_cpue"):
        vals = frame[c].drop_nulls()
        if vals.len():
            print(f"      {c} e.g. {vals.head(3).to_list()}")

print("\n=== can the slow reader handle GSL-N (2.5 MiB)? ===")
import rdata

from migratlas.ingest.http import RemoteFile, fetch

path = fetch(RemoteFile(url=f"{fishglob.BASE}/GSL-N_clean.RData", name="GSL-N_clean.RData"), "fishglob")
start = time.monotonic()
objects = rdata.read_rda(path, default_encoding="latin1", force_default_encoding=True)
frame = next(iter(objects.values()))
print(f"  read {frame.shape[0]:,} rows in {time.monotonic() - start:.1f}s")
