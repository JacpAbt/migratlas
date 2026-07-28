# ADR 0001 — Static-first architecture

**Status:** accepted · 2026-07-28

## Context

The globe needs to show decades of animal movement across the whole planet. The obvious design is an
API in front of a spatial database, queried as the user pans. That means a server to run, secure,
scale and pay for, and it puts a database on the critical path of every frame.

There is no live-query requirement hiding in the product. The user asks for a species, a place and a
time; all three are known before the request. Nothing needs computing at request time.

## Decision

Every heavy computation is a batch job producing immutable tiles. The browser only ever
range-requests them from object storage behind a CDN. No application server.

- Ingest, metrics and models run locally and write PMTiles and COGs.
- Tiles go to Cloudflare R2. Not GitHub Pages or Cloudflare Pages: both have file-size limits and
  unreliable HTTP range request support, which PMTiles requires.
- The app bundle is static and can live on Pages.

## Consequences

Good: hosting cost is approximately zero and does not grow with traffic. There is no attack surface
worth attacking, no scaling story to get wrong, and the frontend cannot be slow because of a query.
Any published artefact is reproducible from its inputs, because producing it was a job rather than a
request.

Bad: no ad-hoc queries. A new question means a new tileset, which is minutes to hours rather than
milliseconds. Publishing is a deliberate step, which is friction — though for a project where
publication is the dangerous act, friction there is a feature.

Accepted cost: some layers will be coarser than a live query could serve, because they have to be
baked at a fixed resolution.
