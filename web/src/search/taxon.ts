/**
 * Species search against a prebuilt static index.
 *
 * No backend and no request per keystroke: the index is generated at build time from what was
 * actually published and searched in memory. Keys are GBIF usage keys, so the frontend and the
 * pipeline agree on what a species is.
 *
 * Every entry has *something* behind it, and that is a weaker promise than the one this file used
 * to make. It said every entry has a surface, which was true and left 689 of the 755 species that
 * carry a measured distribution shift unreachable -- FISHGLOB is a survey, not a published layer,
 * so the animals this project has the most to say about could not be found. A hit with a study and
 * no map is a better answer than no hit.
 *
 * What has not changed is that a hit is never a dead end. The previous index was a hand-written
 * list of thirty animals and most hits led nowhere: a search box that answers and then shrugs
 * teaches the viewer not to trust it.
 */

export interface TaxonEntry {
  key: number;
  scientific: string;
  vernacular: string;
  /** Which published layer holds this taxon's surface. Empty where there is no surface. */
  layer: string;
  /** Human name of that layer. 95 taxa appear in both marine sources, so the rows must differ. */
  layer_title: string;
  /** Occupied cells, which is both a relevance signal and worth showing. */
  cells: number;
  /** Which shard file carries the surface. */
  shard: number;
  /** Whether a study page exists. Absent on older index files, so read it as optional. */
  studied?: boolean;
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

  /**
   * Load the drawn index, and the studied-but-undrawn one beside it.
   *
   * Two files with one writer each rather than one file two commands take turns clobbering --
   * `build-layers` owns the surfaces and `build-species` owns the studies, and the last time this
   * project had two commands writing one index the second silently replaced 3,072 taxa with
   * thirty. The second file is optional: a build that has not run `build-species` yet still
   * searches, with fewer answers.
   */
  static async load(url: string): Promise<TaxonIndex> {
    const index = new TaxonIndex();
    const response = await fetch(url);
    if (!response.ok) throw new Error(`taxon index ${response.status}`);
    const file = (await response.json()) as TaxonIndexFile;

    const studied = await fetch(url.replace("taxon-index.json", "species-index.json"))
      .then((extra) => (extra.ok ? (extra.json() as Promise<TaxonIndexFile>) : null))
      .catch(() => null);

    index.#entries = [...file.taxa, ...(studied?.taxa ?? [])];
    index.shards = file.shards;
    index.#haystack = index.#entries.map((e) => `${e.scientific} ${e.vernacular}`.toLowerCase());
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
