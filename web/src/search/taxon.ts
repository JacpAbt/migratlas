/**
 * Species search against a prebuilt static index.
 *
 * No backend and no request per keystroke: the index is generated at build time from what was
 * actually published and searched in memory. Keys are GBIF usage keys, so the frontend and the
 * pipeline agree on what a species is.
 *
 * Every entry has a surface behind it. The previous index was a hand-written list of thirty
 * animals and most hits led nowhere, which is a worse failure than a short list — a search box
 * that answers and then shrugs teaches the viewer not to trust it.
 */

export interface TaxonEntry {
  key: number;
  scientific: string;
  vernacular: string;
  /** Which published layer holds this taxon's surface. */
  layer: string;
  /** Occupied cells, which is both a relevance signal and worth showing. */
  cells: number;
  /** Which shard file carries the surface. */
  shard: number;
}

export interface TaxonHit extends TaxonEntry {
  score: number;
}

export interface TaxonIndexFile {
  shards: number;
  taxa: TaxonEntry[];
}

export class TaxonIndex {
  #entries: TaxonEntry[] = [];
  #haystack: string[] = [];
  shards = 0;

  static async load(url: string): Promise<TaxonIndex> {
    const index = new TaxonIndex();
    const response = await fetch(url);
    if (!response.ok) throw new Error(`taxon index ${response.status}`);
    const file = (await response.json()) as TaxonIndexFile;
    index.#entries = file.taxa;
    index.shards = file.shards;
    index.#haystack = file.taxa.map((e) => `${e.scientific} ${e.vernacular}`.toLowerCase());
    return index;
  }

  get size(): number {
    return this.#entries.length;
  }

  search(query: string, limit = 8): TaxonHit[] {
    const needle = query.trim().toLowerCase();
    if (needle.length < 2) return [];

    const hits: TaxonHit[] = [];
    for (const [i, hay] of this.#haystack.entries()) {
      const entry = this.#entries[i];
      if (!entry) continue;
      const score = rank(hay, needle);
      if (score > 0) hits.push({ ...entry, score });
    }
    // Ties broken by range size, then by name. With ~3,600 taxa the order of equally-good
    // matches is what the viewer actually sees, and the widest-ranging is the better first answer.
    hits.sort(
      (a, b) =>
        b.score - a.score ||
        b.cells - a.cells ||
        (a.vernacular || a.scientific).localeCompare(b.vernacular || b.scientific),
    );
    return hits.slice(0, limit);
  }
}

function rank(haystack: string, needle: string): number {
  const at = haystack.indexOf(needle);
  if (at < 0) return 0;
  if (at === 0) return 3;
  // A match at a word boundary is what someone typing "grey whale" means; a match
  // mid-word usually is not.
  return haystack[at - 1] === " " ? 2 : 1;
}

/**
 * One taxon's published surface, as index arrays.
 *
 * Shards are fetched lazily and cached: 3,523 marine taxa at one degree total 9.1 MiB, which is
 * far too much to load for a search box, and one shard is ~145 KiB.
 */
export interface SpeciesGrid {
  cell_size_deg: number;
  layer: string;
  x: number[];
  y: number[];
  v: number[];
}

export class SpeciesSurfaces {
  #shards = new Map<number, Promise<Record<string, SpeciesGrid>>>();

  constructor(private readonly baseUrl: string) {}

  async get(entry: TaxonEntry): Promise<SpeciesGrid | undefined> {
    const name = String(entry.shard).padStart(2, "0");
    let shard = this.#shards.get(entry.shard);
    if (!shard) {
      shard = fetch(`${this.baseUrl}layers/species-${name}.json`).then((response) => {
        if (!response.ok) throw new Error(`species shard ${name}: ${response.status}`);
        return response.json() as Promise<Record<string, SpeciesGrid>>;
      });
      this.#shards.set(entry.shard, shard);
    }
    return (await shard)[String(entry.key)];
  }
}
