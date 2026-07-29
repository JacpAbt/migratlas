import logging

from migratlas.ingest import ebird_st

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
result = ebird_st.ingest()
print(f"{result.rows:,} rows -> {result.path}")
